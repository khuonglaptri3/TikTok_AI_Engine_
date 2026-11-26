from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pandas as pd


def _load_g4_module() -> Any:
    root = Path(__file__).resolve().parents[2]
    mod_path = root / "docs/reports/milestones/M4.G/evidence/run_g4_checks.py"
    if not mod_path.is_file():
        raise FileNotFoundError(f"Missing M4.G gate check module: {mod_path}")
    spec = importlib.util.spec_from_file_location("run_g4_checks", mod_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_audit_m4_1_gate_criteria_enforces_two_person_50utt_resource_and_boundary_gates() -> None:
    mod = _load_g4_module()

    pilot_receipt = {
        "timestamp_provenance_labels_observed": ["audio_derived"],
        "audio_scope": {
            "processed_mp3_count": 29,
            "total_audio_minutes": 46.875,
            "within_60m_cap": True,
        },
        "temporal_invariant_audit": {
            "total_segments": 436,
            "valid_segments": 436,
            "invariant_violation_count": 0,
            "invariant_pass_rate": 1.0,
            "meets_100pct_invariant_gate": True,
        },
        "resources": {
            "prosody_wall_seconds": 25.331,
            "m3_3_asr_wall_seconds": 197.269,
            "peak_rss_mib": 240.14,
        },
    }

    sheet_rows: list[dict[str, Any]] = []
    for i in range(60):
        vid = f"v{i // 6}"
        if i < 22:
            asgn = "N_only"
            extra: dict[str, Any] = {}
        elif i < 44:
            asgn = "K_only"
            extra = {}
        else:
            asgn = "double_review_N_K"
            extra = {
                "N_verified": True,
                "N_ref_start_sec": 1.0,
                "N_ref_end_sec": 3.0,
                "N_ref_text": "Bún bò sườn sụn ngon",
                "K_verified": True,
                "K_ref_start_sec": 1.04,
                "K_ref_end_sec": 2.98,
                "K_ref_text": "Bún bò sườn sụn ngon",
            }
        sheet_rows.append(
            {
                "segment_id": f"{vid}_s{i:03d}",
                "video_id": vid,
                "audio_duration_sec": 90.0,
                "timestamp_provenance": "audio_derived",
                "pred_start_sec": 1.0,
                "pred_end_sec": 3.0,
                "ref_start_sec": 1.02,
                "ref_end_sec": 2.99,
                "pred_text": "Bún bò sườn sụn ngon",
                "ref_text": "Bún bò sườn sụn ngon",
                "review_assignment": asgn,
                "human_verified": True,
                **extra,
            }
        )

    ok = mod.audit_m4_1_gate_criteria(pilot_receipt=pilot_receipt, sheet_rows=sheet_rows)
    assert ok["m4_1_gate_pass"] is True
    assert ok["audio_timing_feature_decision"] == "ACCEPTED_BOUNDED_AUDIO_DERIVED_ESTIMATES"
    assert ok["prosody_feature_decision"] == "DESCRIPTIVE_ACOUSTIC_ONLY_NEVER_INTENT"

    # Missing K verification on one overlap row -> fail closed
    incomplete_k = [dict(r) for r in sheet_rows]
    incomplete_k[-1]["K_verified"] = False
    bad_k = mod.audit_m4_1_gate_criteria(pilot_receipt=pilot_receipt, sheet_rows=incomplete_k)
    assert bad_k["m4_1_gate_pass"] is False

    # Boundary p95 > 3.0s -> fail closed & abstain precise playback
    bad_bound_rows = [dict(r) for r in sheet_rows]
    for idx in range(8):
        bad_bound_rows[idx]["ref_end_sec"] = 9.0
    bad_b = mod.audit_m4_1_gate_criteria(pilot_receipt=pilot_receipt, sheet_rows=bad_bound_rows)
    assert bad_b["m4_1_gate_pass"] is False
    assert bad_b["audio_timing_feature_decision"] == "ABSTAIN_PRECISE_PLAYBACK"


def test_audit_m4_2_gate_criteria_rejects_undisclosed_claim_unlabeled_negatives_and_missing_human_audit() -> None:
    mod = _load_g4_module()

    good_study: dict[str, Any] = {
        "target_policy": {
            "undisclosed_sponsorship_status": "DEFERRED",
            "unlabeled_items_treated_as_verified_negative": False,
            "flag_feature_leakage_excluded": True,
            "inline_caption_hashtag_bigram_leakage_blocked": True,
            "historical_audio_prosody_joined": False,
            "bootstrap_mode": "author_cluster_resample",
        },
        "grouped_genuine_target_classifiers": {
            "all_observed_ad_only_vs_ec_only": {
                "author_overlap_count": 0,
                "prosody_features_joined": False,
                "bootstrap_mode": "author_cluster_resample",
                "metrics": {
                    "pr_auc": 0.8915,
                    "brier_score": 0.1322,
                },
            }
        },
    }
    good_audit_summary = {
        "total_unique_items": 100,
        "N_human_verified_count": 65,
        "K_human_verified_count": 65,
        "both_contributors_complete": True,
        "double_review_overlap_count": 30,
        "overlap_cohens_kappa": 0.6364,
    }
    workbook_rows = [
        {
            "item_id": f"m4_2_{i:03d}",
            "N_human_verified": i < 65,
            "K_human_verified": i < 30 or i >= 65,
        }
        for i in range(100)
    ]

    ok = mod.audit_m4_2_gate_criteria(
        study_receipt=good_study,
        combined_audit_summary=good_audit_summary,
        workbook_rows=workbook_rows,
    )
    assert ok["m4_2_gate_pass"] is True
    assert ok["undisclosed_sponsorship_decision"] == "DEFERRED_NO_GROUND_TRUTH"

    bad_policy = {
        **good_study,
        "target_policy": {
            **good_study["target_policy"],
            "unlabeled_items_treated_as_verified_negative": True,
        },
    }
    res_bad = mod.audit_m4_2_gate_criteria(
        study_receipt=bad_policy,
        combined_audit_summary=good_audit_summary,
        workbook_rows=workbook_rows,
    )
    assert res_bad["m4_2_gate_pass"] is False


def test_audit_fresh_pilot_prosody_vs_promo_keeps_prosody_strictly_descriptive() -> None:
    mod = _load_g4_module()

    prosody_rows = [
        {"video_id": "p1", "decoded_duration_sec": 60.0, "pitch_std": 52.1, "energy_cv": 0.48},
        {"video_id": "p2", "decoded_duration_sec": 55.0, "pitch_std": 47.8, "energy_cv": 0.53},
    ]
    videos_df = pd.DataFrame(
        [
            {
                "video_id": "p1",
                "is_ad": False,
                "is_ec_video": False,
                "caption": "Bún bò sườn sụn ngon ở Sài Gòn",
                "transcript": "Nước lèo thanh ngọt",
                "hashtags": ["ancungtiktok"],
            },
            {
                "video_id": "p2",
                "is_ad": False,
                "is_ec_video": True,
                "caption": "Khai trương chi nhánh mới giảm giá 20% ấn vào giỏ hàng",
                "transcript": "Đặt hàng ngay hôm nay",
                "hashtags": ["tiktokshop"],
            },
        ]
    )
    summary = mod.audit_fresh_pilot_prosody_vs_promo(
        per_video_prosody=prosody_rows,
        pilot_videos_df=videos_df,
    )
    assert summary["joined_fresh_audio_video_count"] == 2
    assert summary["prosody_promotion_classifier_accepted"] is False
    assert summary["undisclosed_sponsorship_from_prosody"] == "REJECTED_EPISTEMICALLY_INVALID"


def test_verify_g4_epistemic_and_leakage_guardrails_live() -> None:
    mod = _load_g4_module()
    root = Path(__file__).resolve().parents[2]
    res = mod.verify_g4_epistemic_and_leakage_guardrails(repo_root=root)
    assert res["leakage_guard_pass"] is True
    assert res["trust_api_separation_pass"] is True
    assert res["hidden_pr_refusal_pass"] is True
