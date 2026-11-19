from __future__ import annotations

import asyncio

import httpx
import pandas as pd
import pytest

from apps.api.app.main import create_app
from apps.demo.presentation import format_trust_audit_markdown
from packages.absa import analyze_koc_vs_viewer_absa
from packages.absa.disclosure import (
    analyze_disclosure_and_promo,
    assert_no_feature_leakage,
    classify_observed_disclosure_flags,
)
from packages.absa.disclosure_eval import (
    evaluate_observed_ad_vs_ec_classifier,
    grouped_author_split,
)
from packages.common.settings import AppSettings
from packages.data_contracts.multimodal import RawCommentInput
from packages.seeding import detect_seeding_comments


def test_observed_flag_status_retains_unlabeled_unknown() -> None:
    assert classify_observed_disclosure_flags(False, False) == "unlabeled_unknown"
    assert classify_observed_disclosure_flags(True, False) == "observed_ad"
    assert classify_observed_disclosure_flags(False, True) == "observed_ecommerce"
    assert classify_observed_disclosure_flags(True, True) == "observed_ad_and_ecommerce"


def test_lexical_promo_indicators_separated_from_flags() -> None:
    unlabeled_promo = analyze_disclosure_and_promo(
        caption="Combo lẩu 199k giỏ hàng góc trái đặt hàng freeship",
        transcript="Mời cả nhà nhấn mua ngay trong giỏ hàng",
        is_ad=False,
        is_ec_video=False,
    )
    assert unlabeled_promo.disclosure_flag_status == "unlabeled_unknown"
    assert unlabeled_promo.lexical_promo_score > 0.0
    assert "commerce_cart_cta:giỏ hàng" in unlabeled_promo.matched_indicators
    assert "commerce_cart_cta:góc trái" in unlabeled_promo.matched_indicators
    assert "not verified negative" in unlabeled_promo.disclosure_target_note.lower()

    baseline_review = analyze_disclosure_and_promo(
        caption="Review quán phở bò ngon ở Hà Nội",
        transcript="Nước dùng thanh ngọt thịt mềm",
        is_ad=True,
        is_ec_video=False,
    )
    assert baseline_review.disclosure_flag_status == "observed_ad"
    assert baseline_review.matched_indicators == []
    assert baseline_review.lexical_promo_score == 0.0


def test_leakage_and_no_prosody_guards() -> None:
    assert_no_feature_leakage(["caption", "transcript", "food_category", "duration_sec"])
    for forbidden in (
        "is_ad",
        "is_ec_video",
        "disclosure_flag_status",
        "commerce_user",
        "undisclosed_pr_risk",
        "prosody_pitch_mean",
        "audio_f0_std",
        "whisper_wps",
    ):
        with pytest.raises(ValueError):
            assert_no_feature_leakage(["caption", forbidden])


def test_author_grouped_split_and_genuine_target_classifier() -> None:
    rows: list[dict[str, object]] = []
    for idx in range(12):
        author = f"creator_{idx:02d}"
        is_ad = idx % 2 == 0
        for j in range(3):
            rows.append(
                {
                    "video_id": f"v_{idx}_{j}",
                    "author_handle": author,
                    "is_ad": is_ad,
                    "is_ec_video": not is_ad,
                    "caption": (
                        "Khai trương buffet chi nhánh quận 1 voucher ưu đãi #ad"
                        if is_ad
                        else "Combo đồ ăn vặt giỏ hàng góc trái đặt hàng freeship"
                    ),
                    "transcript": (
                        "Quán mới khai trương menu đa dạng đặt bàn ngay"
                        if is_ad
                        else "Cả nhà bấm vào giỏ hàng đặt hàng giúp mình nha"
                    ),
                    "hashtags": ["reviewanngon", "ad"] if is_ad else ["ancungtiktok", "mukbang"],
                    "food_category": "Lẩu & Nướng" if is_ad else "Ăn vặt & Đường phố",
                }
            )
    # Include unlabeled_unknown and both rows that MUST be excluded from binary target training
    rows.append(
        {
            "video_id": "v_unlabeled",
            "author_handle": "creator_unlabeled",
            "is_ad": False,
            "is_ec_video": False,
            "caption": "Giảm giá khai trương",
            "transcript": "Review món ăn",
            "hashtags": [],
            "food_category": "Món nước & Sợi",
        }
    )
    rows.append(
        {
            "video_id": "v_both",
            "author_handle": "creator_both",
            "is_ad": True,
            "is_ec_video": True,
            "caption": "Combo giỏ hàng voucher",
            "transcript": "Ưu đãi combo",
            "hashtags": [],
            "food_category": "Ăn vặt & Đường phố",
        }
    )
    df = pd.DataFrame(rows)

    train_idx, test_idx = grouped_author_split(
        df[df["is_ad"] ^ df["is_ec_video"]].reset_index(drop=True),
        group_col="author_handle",
        test_fraction=0.33,
        seed=42,
    )
    train_authors = set(df[df["is_ad"] ^ df["is_ec_video"]].iloc[train_idx]["author_handle"])
    test_authors = set(df[df["is_ad"] ^ df["is_ec_video"]].iloc[test_idx]["author_handle"])
    assert train_authors
    assert test_authors
    assert train_authors.isdisjoint(test_authors)

    res = evaluate_observed_ad_vs_ec_classifier(df, test_fraction=0.33, seed=42, n_boot=50)
    assert res["target_name"] == "is_ad_only_vs_is_ec_only"
    assert res["unlabeled_excluded_count"] == 1
    assert res["both_flags_excluded_count"] == 1
    assert res["author_overlap_count"] == 0
    assert 0.5 <= res["metrics"]["pr_auc"] <= 1.0
    assert 0.0 <= res["metrics"]["brier_score"] <= 0.5


def test_absa_contract_trust_api_and_demo_presentation_separation() -> None:
    comments = detect_seeding_comments(
        "v_m4_2",
        [RawCommentInput(comment_id="c1", author_handle="diner", text="Nước dùng đậm đà giá hợp lý.")],
    )
    comp = analyze_koc_vs_viewer_absa(
        video_id="v_m4_2",
        caption="Khai trương tặng ngay voucher giảm giá!",
        transcript="Nước dùng ngon xuất sắc, nhấn giỏ hàng góc trái nhé.",
        comments=comments,
        is_ad=True,
        is_ec_video=False,
    )
    assert comp.disclosure_flag_status == "observed_ad"
    assert comp.sponsorship_ground_truth_status == "undisclosed_sponsorship_deferred"
    assert comp.lexical_promo_score > 0.0
    assert "branch_venue_promo:khai trương" in comp.promotional_language_indicators
    assert "commerce_cart_cta:giỏ hàng" in comp.promotional_language_indicators

    md = format_trust_audit_markdown(
        {"comparison": comp.model_dump(), "comments": [c.model_dump() for c in comments]}
    )
    assert "observed_ad" in md
    assert "chỉ dấu ngôn ngữ quảng bá" in md.lower()
    assert "không phải xác suất tài trợ ngầm" in md.lower()

    settings = AppSettings.from_env().model_copy(update={"gemini_api_key": ""})
    app = create_app(settings=settings, mount_demo=False)

    async def _post_trust() -> dict[str, object]:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/api/v1/trust/audit-video",
                json={
                    "video_id": "v_api",
                    "caption": "Combo lẩu giỏ hàng góc trái",
                    "transcript": "Món này ăn ngon nha mọi người",
                    "is_ad": False,
                    "is_ec_video": False,
                    "comments": [],
                },
            )
            assert resp.status_code == 200
            return dict(resp.json())

    body = asyncio.run(_post_trust())
    comparison = body["comparison"]
    assert isinstance(comparison, dict)
    assert comparison["disclosure_flag_status"] == "unlabeled_unknown"
    assert comparison["sponsorship_ground_truth_status"] == "undisclosed_sponsorship_deferred"


def test_sample_historical_review_100_invariants() -> None:
    from pipelines.audit_m4_2_disclosure.run_study import sample_historical_review_100

    rows = []
    for i in range(160):
        flag_type = i % 4
        rows.append(
            {
                "video_id": f"vid_{i:04d}",
                "author_handle": f"author_{i % 10}",
                "is_ad": flag_type in (0, 2),
                "is_ec_video": flag_type in (1, 2),
                "has_transcript": (i // 4) % 2 == 0,
                "caption": f"Caption {i} combo ưu đãi",
                "transcript": f"Transcript {i}" if (i // 4) % 2 == 0 else "",
                "hashtags": ["reviewanngon"],
                "food_category": "Món nước & Sợi",
            }
        )
    df = pd.DataFrame(rows)
    items = sample_historical_review_100(df, seed=42)
    assert len(items) == 100
    assert len({r["video_id"] for r in items}) == 100
    assert sum(1 for r in items if r["review_assignment"] == "double_review_N_K") == 30
    assert sum(1 for r in items if r["review_assignment"] == "N_only") == 35
    assert sum(1 for r in items if r["review_assignment"] == "K_only") == 35
    assert all(not r["N_human_verified"] and not r["K_human_verified"] for r in items)


def test_llm_blinded_prompt_strips_flags_and_validates_draft_schema() -> None:
    from pipelines.audit_m4_2_disclosure.llm_draft_annotate import (
        annotate_batch_with_client,
        build_blinded_disclosure_prompt,
    )

    sample = [
        {
            "item_id": "m4_2_001",
            "food_category": "Lẩu & Nướng",
            "has_transcript": True,
            "caption": "Lẩu ngon giảm giá 20%",
            "transcript_excerpt": "Ghé ăn nhé",
            "hashtags": ["ad", "quangcao", "monngon"],
            "observed_flag_status": "observed_ad",
            "N_human_verified": False,
            "K_human_verified": False,
        }
    ]
    prompt = build_blinded_disclosure_prompt(sample)
    assert "observed_ad" not in prompt
    assert '"ad"' not in prompt
    assert "quangcao" not in prompt
    assert "monngon" in prompt

    class _FakeClient:
        def generate_structured_json(self, _prompt: str, turn_calls_used: int = 0) -> dict[str, object]:
            assert turn_calls_used == 0
            return {
                "items": [
                    {
                        "item_id": "m4_2_001",
                        "llm_observed_wording_label": "explicit_promo_cta",
                        "llm_observed_promo_phrases": ["giảm giá 20%"],
                        "llm_domain_or_asr_error_note": "Có từ khóa giảm giá rõ ràng.",
                        "llm_commercial_cue_evident": True,
                    }
                ]
            }

    annotated = annotate_batch_with_client(
        sample,
        client=_FakeClient(),
        model_name="gemini-3.1-flash-lite",
    )
    assert annotated[0]["llm_observed_wording_label"] == "explicit_promo_cta"
    assert annotated[0]["N_human_verified"] is False
    assert annotated[0]["K_human_verified"] is False
    assert annotated[0]["llm_blinded_to_platform_flag"] is True
