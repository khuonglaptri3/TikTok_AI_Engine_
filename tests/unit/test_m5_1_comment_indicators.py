from __future__ import annotations

import asyncio

import httpx
import pandas as pd
import pytest

from apps.api.app.main import create_app
from apps.demo.presentation import format_trust_audit_markdown
from packages.common.settings import AppSettings
from packages.data_contracts.multimodal import RawCommentInput
from packages.seeding import detect_seeding_comments
from packages.seeding.evaluation import (
    build_annotation_pool,
    compute_inter_annotator_agreement,
    evaluate_comment_indicator_metrics,
    split_comments_by_video,
)


def test_observable_labels_preserve_originals_and_exempt_short_organic_duplicates() -> None:
    raw = [
        RawCommentInput(comment_id="c1", author_handle="u1", text="  Ngon quá  "),
        RawCommentInput(comment_id="c2", author_handle="u2", text="Ngon quá"),
        RawCommentInput(
            comment_id="c3",
            author_handle="u3",
            text="Tuyển CTV việc nhẹ lương cao inbox zalo 0909123456",
        ),
        RawCommentInput(comment_id="c4", author_handle="u4", text="😋🔥💯"),
        RawCommentInput(
            comment_id="c5",
            author_handle="u5",
            text="Quán ăn này nước dùng đậm đà ngon xuất sắc luôn mọi người",
        ),
        RawCommentInput(
            comment_id="c6",
            author_handle="u6",
            text="Quán ăn này nước dùng đậm đà ngon xuất sắc luôn mọi người nha",
        ),
    ]
    out = {c.comment_id: c for c in detect_seeding_comments("vid_1", raw)}

    assert out["c1"].original_text == "  Ngon quá  "
    assert out["c1"].text == "Ngon quá"
    # Repeated short organic compliments MUST NOT be flagged as duplicate spam
    assert out["c1"].observable_label == "no_indicator_observed"
    assert out["c2"].observable_label == "no_indicator_observed"
    assert out["c1"].is_seeding is False
    assert out["c2"].is_seeding is False
    assert "short_organic_phrase_exempt" in out["c1"].observable_reason_codes

    assert out["c3"].observable_label == "contact_or_link"
    assert out["c3"].seeding_reason == "contact_or_link_spam"
    assert out["c4"].observable_label == "noise_or_empty"
    assert out["c5"].observable_label == "observable_duplicate"
    assert out["c6"].observable_label == "observable_duplicate"

    for rec in out.values():
        assert rec.diagnostic_only is True
        joined = f"{rec.observable_label} {' '.join(rec.observable_reason_codes)}".lower()
        assert "bot" not in joined
        assert "payment" not in joined


def test_video_disjoint_split_agreement_and_gate_check() -> None:
    rows: list[dict[str, object]] = []
    classes = [
        "observable_duplicate",
        "contact_or_link",
        "noise_or_empty",
        "no_indicator_observed",
        "unknown_ambiguous",
    ]
    for vid_idx in range(9):
        for j, cls in enumerate(classes):
            pred = cls if cls != "unknown_ambiguous" else "no_indicator_observed"
            rows.append(
                {
                    "comment_id": f"c_{vid_idx}_{j}",
                    "video_id": f"v_{vid_idx:02d}",
                    "adjudicated_label": cls,
                    "pred_label": pred,
                    "N_label": cls,
                    "K_label": cls if j != 4 else "observable_duplicate",
                }
            )

    splits = split_comments_by_video(rows, video_id_col="video_id", seed=42)
    assert set(splits.keys()) == {"dev", "calibration", "held_out_third"}
    vids_dev = {r["video_id"] for r in splits["dev"]}
    vids_cal = {r["video_id"] for r in splits["calibration"]}
    vids_test = {r["video_id"] for r in splits["held_out_third"]}
    assert vids_dev and vids_cal and vids_test
    assert vids_dev.isdisjoint(vids_cal)
    assert vids_dev.isdisjoint(vids_test)
    assert vids_cal.isdisjoint(vids_test)

    agr = compute_inter_annotator_agreement(
        [str(r["N_label"]) for r in rows],
        [str(r["K_label"]) for r in rows],
    )
    assert 0.5 < agr["raw_agreement"] < 1.0
    assert agr["unknown_ambiguous_count"] > 0

    report = evaluate_comment_indicator_metrics(
        list(splits["held_out_third"]),
        pred_col="pred_label",
        truth_col="adjudicated_label",
        human_signoff_complete=False,
        n_boot=100,
        seed=42,
    )
    assert report["macro_precision"] >= 0.99
    assert report["auto_filter_eligible"] is False
    assert report["recommended_mode"] == "diagnostic_only_without_filtering"

    pool_df = pd.DataFrame(rows)
    with pytest.raises(ValueError):
        build_annotation_pool(pool_df, max_items=301)
    sampled = build_annotation_pool(pool_df, max_items=30, double_overlap=10, seed=42)
    assert len(sampled) == 30
    assert sum(1 for r in sampled if r["review_assignment"] == "double_review_N_K") == 10


def test_trust_api_and_demo_diagnostic_mode_and_filter_sensitivity() -> None:
    app = create_app(
        settings=AppSettings.from_env().model_copy(update={"gemini_api_key": ""}),
        mount_demo=False,
    )

    async def _run() -> dict[str, object]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            resp = await client.post(
                "/api/v1/trust/audit-video",
                json={
                    "video_id": "v_m5_1",
                    "caption": "Quán bún bò ngon ở quận 1",
                    "transcript": "Nước lèo đậm đà giá hợp lý phục vụ nhanh",
                    "comments": [
                        {"comment_id": "1", "author_handle": "a", "text": "Ngon quá"},
                        {"comment_id": "2", "author_handle": "b", "text": "Ngon quá"},
                        {
                            "comment_id": "3",
                            "author_handle": "c",
                            "text": "Inbox zalo 0909123456 nhận voucher",
                        },
                        {
                            "comment_id": "4",
                            "author_handle": "d",
                            "text": "Đồ ăn nguội ngắt và dơ, phục vụ quá chậm",
                        },
                    ],
                },
            )
            assert resp.status_code == 200
            return dict(resp.json())

    body = asyncio.run(_run())
    assert body["comment_filter_policy"] == "diagnostic_only_unvalidated"
    sens = body["filter_sensitivity"]
    assert isinstance(sens, dict)
    assert sens["total_comments"] == 4
    assert sens["flagged_indicator_count"] == 1
    assert "before_filter_viewer_mean" in sens
    assert "after_filter_viewer_mean" in sens

    md = format_trust_audit_markdown(body)
    assert "0909123456" in md
    assert "contact_or_link" in md.lower()
    assert "độ nhạy trước/sau" in md.lower() or "filter sensitivity" in md.lower()


def test_k_review_five_to_seven_syllable_vietnamese_organic_inquiries_exempt() -> None:
    raw = [
        RawCommentInput(comment_id="q1", author_handle="u1", text="Cho mình xin địa chỉ"),
        RawCommentInput(comment_id="q2", author_handle="u2", text="Cho mình xin địa chỉ"),
        RawCommentInput(comment_id="q3", author_handle="u3", text="Quán này ở đâu vậy"),
        RawCommentInput(comment_id="q4", author_handle="u4", text="Quán này ở đâu vậy"),
        RawCommentInput(comment_id="q5", author_handle="u5", text="Cho mình xin địa chỉ quán với"),
        RawCommentInput(comment_id="q6", author_handle="u6", text="Cho mình xin địa chỉ quán ạ"),
    ]
    out = {c.comment_id: c for c in detect_seeding_comments("vid_org", raw)}
    for cid, rec in out.items():
        assert rec.observable_label == "no_indicator_observed", f"{cid} falsely flagged: {rec}"
        assert rec.is_seeding is False


def test_k_review_spam_isolation_template_visibility_transitive_clusters_and_19digit_id() -> None:
    raw = [
        RawCommentInput(
            comment_id="spam1",
            author_handle="sp1",
            text="Cho mình hỏi địa chỉ quán ở đâu vậy zalo",
        ),
        RawCommentInput(
            comment_id="diner1",
            author_handle="dn1",
            text="Cho mình hỏi địa chỉ quán ở đâu vậy ạ",
        ),
        RawCommentInput(
            comment_id="tpl1",
            author_handle="tp1",
            text="Quán ruột của mình mỗi tuần đều ghé ăn bún bò",
        ),
        RawCommentInput(
            comment_id="tpl2",
            author_handle="tp2",
            text="Quán ruột của mình mỗi tuần đều ghé ăn bún bò nha",
        ),
        RawCommentInput(
            comment_id="vid_ref",
            author_handle="v1",
            text="Xem thêm clip 7401234567890123456 món bún bò ngon lắm",
        ),
        RawCommentInput(
            comment_id="tg1",
            author_handle="s_tg",
            text="Nhận ưu đãi qua https://t.me/quananngon nha",
        ),
        RawCommentInput(
            comment_id="rep_noise",
            author_handle="n1",
            text="aaaaaaaaaaaa",
        ),
        # 4-node near-duplicate chain across distinct authors
        RawCommentInput(comment_id="ch1", author_handle="a1", text="Nước lẩu đậm đà thịt bò mềm tươi phục vụ chu đáo lắm"),
        RawCommentInput(comment_id="ch2", author_handle="a2", text="Nước lẩu đậm đà thịt bò mềm tươi phục vụ chu đáo nha"),
        RawCommentInput(comment_id="ch3", author_handle="a3", text="Nước lẩu đậm đà thịt bò mềm tươi phục vụ chu đáo quá"),
        RawCommentInput(comment_id="ch4", author_handle="a4", text="Nước lẩu đậm đà thịt bò mềm tươi phục vụ chu đáo thiệt"),
    ]
    out = {c.comment_id: c for c in detect_seeding_comments("vid_edge", raw)}
    assert out["spam1"].observable_label == "contact_or_link"
    assert out["diner1"].observable_label == "no_indicator_observed"
    assert out["diner1"].cluster_id is None
    assert out["tpl1"].observable_label == "template_phrase_match"
    assert out["tpl2"].observable_label == "template_phrase_match"
    assert out["vid_ref"].observable_label == "no_indicator_observed"
    assert out["tg1"].observable_label == "contact_or_link"
    assert out["rep_noise"].observable_label == "noise_or_empty"
    cids = {out[k].cluster_id for k in ("ch1", "ch2", "ch3", "ch4")}
    assert len(cids) == 1 and None not in cids


def test_k_review_held_out_third_gate_reachable_strict_labels_and_recall_support() -> None:
    rows: list[dict[str, object]] = []
    classes = [
        "observable_duplicate",
        "contact_or_link",
        "noise_or_empty",
        "template_phrase_match",
        "no_indicator_observed",
    ]
    for vid_idx in range(36):
        for j, cls in enumerate(classes):
            rows.append(
                {
                    "comment_id": f"c_{vid_idx}_{j}",
                    "video_id": f"v_{vid_idx:02d}",
                    "adjudicated_label": cls,
                    "pred_label": cls,
                }
            )
    assert len(rows) == 180
    splits = split_comments_by_video(rows, video_id_col="video_id", seed=42)
    held_out = list(splits["held_out_third"])
    assert len(held_out) == 60

    gate_report = evaluate_comment_indicator_metrics(
        held_out,
        pred_col="pred_label",
        truth_col="adjudicated_label",
        human_signoff_complete=True,
        total_annotated_pool_count=len(rows),
        n_boot=50,
        seed=42,
    )
    assert gate_report["auto_filter_eligible"] is True
    assert gate_report["recommended_mode"] == "auto_filter_validated"

    # Null or typo labels must fail closed instead of silently coercing to string
    with pytest.raises(ValueError):
        evaluate_comment_indicator_metrics(
            [{"comment_id": "bad", "video_id": "v1", "adjudicated_label": None, "pred_label": "no_indicator_observed"}]
        )

    # support=0 with fp>0 penalizes macro_precision but must NOT drag down macro_recall
    fp_only_rows = [
        {"comment_id": "1", "video_id": "v1", "adjudicated_label": "contact_or_link", "pred_label": "contact_or_link"},
        {"comment_id": "2", "video_id": "v2", "adjudicated_label": "no_indicator_observed", "pred_label": "noise_or_empty"},
    ]
    fp_rep = evaluate_comment_indicator_metrics(fp_only_rows, n_boot=20, seed=42)
    assert fp_rep["macro_precision"] == pytest.approx(0.5, abs=1e-4)
    assert fp_rep["macro_recall"] == pytest.approx(1.0, abs=1e-4)


def test_k_review_blinded_video_grouped_pool_and_gold_parquet_reconstruction() -> None:
    from packages.seeding.evaluation import reconstruct_observable_predictions

    clean_variants = {
        1: "Nước lèo thanh ngọt vừa miệng thịt bò tái mềm",
        2: "Không gian thoáng mát bàn ghế sạch sẽ gửi xe miễn phí",
        3: "Nhân viên nhiệt tình lên món khá nhanh dù buổi trưa đông",
    }
    # Simulate 10-column Gold fact_comments.parquet (no observable_label column)
    gold_df = pd.DataFrame(
        [
            {
                "comment_id": f"c_{v}_{j}",
                "video_id": f"vid_{v:02d}",
                "author_handle": f"u_{v}_{j}",
                "text": "Inbox zalo 0909123456" if j == 0 else clean_variants[j],
                "like_count": 1,
                "reply_count": 0,
                "is_seeding": j == 0,
                "seeding_reason": "contact_or_link_spam" if j == 0 else None,
                "similarity_score": 0.0,
                "cluster_id": None,
            }
            for v in range(6)
            for j in range(4)
        ]
    )
    blinded_pool = build_annotation_pool(gold_df, max_items=16, double_overlap=8, seed=42)
    assert len(blinded_pool) == 16
    for item in blinded_pool:
        assert "predicted_observable_label" not in item
        assert "predicted_reason_codes" not in item

    # Comments from the same video must stay contiguous in thread order
    seen_completed_videos: set[str] = set()
    prev_vid: str | None = None
    for item in blinded_pool:
        vid = str(item["video_id"])
        if prev_vid is not None and vid != prev_vid:
            seen_completed_videos.add(prev_vid)
            assert vid not in seen_completed_videos, f"Video thread {vid} was fragmented across pool"
        prev_vid = vid

    preds = reconstruct_observable_predictions(gold_df, blinded_pool)
    by_cid = {r["comment_id"]: r["predicted_observable_label"] for r in preds}
    for cid, lbl in by_cid.items():
        if cid.endswith("_0"):
            assert lbl == "contact_or_link"
        else:
            assert lbl == "no_indicator_observed"


def test_k_review_empty_after_filter_abstention_and_demo_bare_url_parsing() -> None:
    from apps.demo.presentation import parse_demo_comment_lines
    from packages.seeding.evaluation import compute_comment_filter_sensitivity

    parsed = parse_demo_comment_lines(
        "Xem menu tại https://example.com/quan-an\n"
        "@viewer_01: 19:30 quán đã hết bàn rồi\n"
        "Giá: 45k một tô đầy ắp"
    )
    assert parsed[0] == {
        "comment_id": "c1",
        "author_handle": "viewer_1",
        "text": "Xem menu tại https://example.com/quan-an",
    }
    assert parsed[1] == {
        "comment_id": "c2",
        "author_handle": "viewer_01",
        "text": "19:30 quán đã hết bàn rồi",
    }
    assert parsed[2] == {
        "comment_id": "c3",
        "author_handle": "viewer_3",
        "text": "Giá: 45k một tô đầy ắp",
    }
    flagged = detect_seeding_comments("v_url", [RawCommentInput(**parsed[0])])
    assert flagged[0].observable_label == "contact_or_link"

    # When 100% of comments are flagged, after-filter viewer sentiment must abstain rather than faking 0.0
    sens = compute_comment_filter_sensitivity(
        caption="Bún bò siêu ngon xuất sắc",
        transcript="Nước lèo đậm đà thịt mềm giá siêu rẻ",
        comments=flagged,
    )
    assert sens["unflagged_comment_count"] == 0
    assert sens["after_filter_abstained"] is True
    assert sens["after_filter_viewer_mean"] is None
    assert sens["mean_score_shift"] is None
    assert sens["after_filter_hype_gap"] == 0.0

