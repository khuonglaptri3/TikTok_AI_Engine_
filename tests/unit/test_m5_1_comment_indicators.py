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
