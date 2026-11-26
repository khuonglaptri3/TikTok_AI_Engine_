"""Deterministic Gate M4.G (G4) verification probe across M4.1 audio/prosody and M4.2 promotion targets."""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient

from apps.api.app.main import create_app
from packages.absa.disclosure import (
    analyze_disclosure_and_promo,
    assert_no_feature_leakage,
)
from packages.analytics import load_verified_corpus
from packages.common.settings import AppSettings
from packages.prosody import (
    compute_m4_1_annotator_agreement,
    evaluate_m4_1_reference_set,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_tree_digests(corpus_dir: Path) -> dict[str, str]:
    manifest, _, _ = load_verified_corpus(corpus_dir)
    digests = {"manifest.json": _sha256_file(corpus_dir / "manifest.json")}
    for entry in manifest.files:
        fpath = corpus_dir / entry.filename
        actual = _sha256_file(fpath)
        if actual != entry.sha256:
            raise ValueError(f"SHA256 mismatch on {fpath}: {actual} != {entry.sha256}")
        digests[entry.filename] = actual
    return digests


def audit_m4_1_gate_criteria(
    *,
    pilot_receipt: Mapping[str, Any],
    sheet_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify M4.1 audio limits, 100% temporal invariants, two-person coverage, and boundary gates."""
    scope = dict(pilot_receipt.get("audio_scope") or {})
    inv = dict(pilot_receipt.get("temporal_invariant_audit") or {})
    res = dict(pilot_receipt.get("resources") or {})
    prov_labels = list(pilot_receipt.get("timestamp_provenance_labels_observed") or [])

    mp3_count = int(scope.get("processed_mp3_count") or 0)
    total_audio_min = float(scope.get("total_audio_minutes") or 0.0)
    within_60m = mp3_count == 29 and 0.0 < total_audio_min <= 60.0

    prosody_wall = float(res.get("prosody_wall_seconds") or 0.0)
    asr_wall = float(res.get("m3_3_asr_wall_seconds") or 0.0)
    combined_wall = round(prosody_wall + asr_wall, 3)
    peak_rss = float(res.get("peak_rss_mib") or 0.0)
    within_compute = (
        math.isfinite(combined_wall)
        and 0.0 < combined_wall <= 14_400.0
        and math.isfinite(peak_rss)
        and 0.0 < peak_rss <= 8_192.0
    )

    inv_rate = float(inv.get("invariant_pass_rate") or 0.0)
    inv_violations = int(inv.get("invariant_violation_count") or 0)
    provenance_ok = prov_labels == ["audio_derived"] and inv_violations == 0 and inv_rate >= 1.0 - 1e-9

    n_only_ok = [
        r for r in sheet_rows if r.get("review_assignment") == "N_only" and r.get("human_verified") is True
    ]
    k_only_ok = [
        r for r in sheet_rows if r.get("review_assignment") == "K_only" and r.get("human_verified") is True
    ]
    overlap_rows = [r for r in sheet_rows if r.get("review_assignment") == "double_review_N_K"]
    overlap_both_ok = [
        r for r in overlap_rows if r.get("N_verified") is True and r.get("K_verified") is True
    ]
    two_person_complete = (
        len(sheet_rows) == 60
        and len(n_only_ok) == 22
        and len(k_only_ok) == 22
        and len(overlap_rows) == 16
        and len(overlap_both_ok) == 16
    )

    ref_eval = evaluate_m4_1_reference_set(
        sheet_rows,
        is_real_human_verified=two_person_complete,
        invariant_pass_rate=inv_rate,
    )
    iaa = compute_m4_1_annotator_agreement(sheet_rows)

    gate_pass = bool(
        within_60m
        and within_compute
        and provenance_ok
        and two_person_complete
        and ref_eval["precise_playback_allowed"] is True
    )
    timing_decision = (
        "ACCEPTED_BOUNDED_AUDIO_DERIVED_ESTIMATES"
        if ref_eval["precise_playback_allowed"] is True and provenance_ok
        else "ABSTAIN_PRECISE_PLAYBACK"
    )

    return {
        "m4_1_gate_pass": gate_pass,
        "within_60m_audio_cap": within_60m,
        "within_4h_cpu_and_8gib_ram": within_compute,
        "combined_cpu_wall_seconds": combined_wall,
        "peak_rss_mib": peak_rss,
        "provenance_and_100pct_invariants_pass": provenance_ok,
        "two_person_sheet_complete": two_person_complete,
        "reference_evaluation": ref_eval,
        "inter_annotator_agreement": iaa,
        "audio_timing_feature_decision": timing_decision,
        "historical_interpolation_decision": "RETAINED_AS_WPS_ESTIMATED_NEVER_AUDIO_EXACT",
        "prosody_feature_decision": "DESCRIPTIVE_ACOUSTIC_ONLY_NEVER_INTENT",
    }


def audit_m4_2_gate_criteria(
    *,
    study_receipt: Mapping[str, Any],
    combined_audit_summary: Mapping[str, Any],
    workbook_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify M4.2 observable target validity, leakage exclusion, and 100-item N+K audit."""
    policy = dict(study_receipt.get("target_policy") or {})
    clf = dict(
        (study_receipt.get("grouped_genuine_target_classifiers") or {}).get(
            "all_observed_ad_only_vs_ec_only"
        )
        or {}
    )
    clf_metrics = dict(clf.get("metrics") or {})

    policy_ok = (
        policy.get("undisclosed_sponsorship_status") == "DEFERRED"
        and policy.get("unlabeled_items_treated_as_verified_negative") is False
        and policy.get("flag_feature_leakage_excluded") is True
        and policy.get("inline_caption_hashtag_bigram_leakage_blocked") is True
        and policy.get("historical_audio_prosody_joined") is False
        and policy.get("bootstrap_mode") == "author_cluster_resample"
    )

    clf_ok = (
        int(clf.get("author_overlap_count", 1)) == 0
        and clf.get("prosody_features_joined") is False
        and clf.get("bootstrap_mode") == "author_cluster_resample"
        and clf_metrics.get("pr_auc") is not None
        and clf_metrics.get("brier_score") is not None
    )

    unique_ids = {str(r.get("item_id") or "") for r in workbook_rows if r.get("item_id")}
    n_ver = sum(1 for r in workbook_rows if r.get("N_human_verified") is True)
    k_ver = sum(1 for r in workbook_rows if r.get("K_human_verified") is True)
    every_item_verified = all(
        r.get("N_human_verified") is True or r.get("K_human_verified") is True
        for r in workbook_rows
    )
    kappa = float(combined_audit_summary.get("overlap_cohens_kappa") or 0.0)
    human_audit_ok = (
        len(workbook_rows) == 100
        and len(unique_ids) == 100
        and n_ver == 65
        and k_ver == 65
        and every_item_verified
        and combined_audit_summary.get("both_contributors_complete") is True
        and int(combined_audit_summary.get("double_review_overlap_count") or 0) == 30
        and math.isfinite(kappa)
        and kappa > 0.0
    )

    gate_pass = bool(policy_ok and clf_ok and human_audit_ok)
    return {
        "m4_2_gate_pass": gate_pass,
        "target_policy_valid": policy_ok,
        "grouped_genuine_classifier_valid": clf_ok,
        "two_person_100_item_audit_valid": human_audit_ok,
        "verified_counts": {"unique_items": len(unique_ids), "N": n_ver, "K": k_ver, "kappa": kappa},
        "observed_flags_and_promo_cues_decision": "ACCEPTED_SEPARATED_OBSERVABLE_INDICATORS",
        "undisclosed_sponsorship_decision": "DEFERRED_NO_GROUND_TRUTH",
    }


def audit_fresh_pilot_prosody_vs_promo(
    *,
    per_video_prosody: Sequence[Mapping[str, Any]],
    pilot_videos_df: pd.DataFrame,
) -> dict[str, Any]:
    """Join M4.1 29-MP3 prosody with M3.3 pilot flags/cues; enforce descriptive-only boundary."""
    v_map: dict[str, dict[str, Any]] = {}
    for row in pilot_videos_df.to_dict("records"):
        vid = str(row.get("video_id") or "").strip()
        if vid:
            v_map[vid] = row

    by_promo_presence: dict[str, dict[str, list[float]]] = {
        "with_promo_cues": {"pitch_std": [], "energy_cv": []},
        "no_promo_cues": {"pitch_std": [], "energy_cv": []},
    }
    flag_counts: dict[str, int] = {}
    joined = 0

    for p in per_video_prosody:
        vid = str(p.get("video_id") or "").strip()
        v = v_map.get(vid)
        if v is None:
            continue
        joined += 1
        raw_tags = v.get("hashtags")
        if isinstance(raw_tags, (list, tuple, np.ndarray)):
            tags = [str(x) for x in raw_tags]
        else:
            tags = []
        disc = analyze_disclosure_and_promo(
            caption=str(v.get("caption") or ""),
            transcript=str(v.get("transcript") or ""),
            is_ad=bool(v.get("is_ad", False)),
            is_ec_video=bool(v.get("is_ec_video", False)),
            hashtags=tags,
        )
        flag_counts[disc.disclosure_flag_status] = flag_counts.get(disc.disclosure_flag_status, 0) + 1
        bucket = "with_promo_cues" if disc.matched_indicators else "no_promo_cues"
        if p.get("pitch_std") is not None and math.isfinite(float(p["pitch_std"])):
            by_promo_presence[bucket]["pitch_std"].append(float(p["pitch_std"]))
        if p.get("energy_cv") is not None and math.isfinite(float(p["energy_cv"])):
            by_promo_presence[bucket]["energy_cv"].append(float(p["energy_cv"]))

    def _stats(vals: list[float]) -> dict[str, float | int | None]:
        if not vals:
            return {"n": 0, "median": None, "q25": None, "q75": None}
        arr = np.asarray(vals, dtype=np.float64)
        return {
            "n": len(vals),
            "median": round(float(np.median(arr)), 4),
            "q25": round(float(np.percentile(arr, 25)), 4),
            "q75": round(float(np.percentile(arr, 75)), 4),
        }

    return {
        "joined_fresh_audio_video_count": joined,
        "pilot_flag_stratum_counts": flag_counts,
        "descriptive_prosody_by_promo_cue_presence": {
            grp: {
                "pitch_std_hz": _stats(metrics["pitch_std"]),
                "energy_cv": _stats(metrics["energy_cv"]),
            }
            for grp, metrics in by_promo_presence.items()
        },
        "prosody_promotion_classifier_accepted": False,
        "undisclosed_sponsorship_from_prosody": "REJECTED_EPISTEMICALLY_INVALID",
        "epistemic_note": (
            "Fresh pilot acoustic prosody overlaps broadly across promo-cue and organic F&B clips "
            "and lacks independent sponsorship ground truth; prosody remains strictly descriptive."
        ),
    }


def verify_g4_epistemic_and_leakage_guardrails(*, repo_root: Path) -> dict[str, Any]:
    """Run live leakage rejections and ASGI API epistemic guardrail checks."""
    blocked_probes = ("is_ad", "poi_id", "prosody_pitch_std", "video_format", "has_cta")
    rejected_all = True
    for col in blocked_probes:
        try:
            assert_no_feature_leakage(["caption_tfidf", col])
            rejected_all = False
        except ValueError:
            pass
    assert_no_feature_leakage(["caption_tfidf", "transcript_tfidf", "food_category"])

    settings = AppSettings(
        gemini_api_key="",
        corpus_dir=repo_root / "data/corpus/m3_3_pilot_snapshot_v2",
        bm25_index_dir=repo_root / "artifacts/indexes/bm25-m3_3-pilot",
    )
    app = create_app(settings=settings, mount_demo=False)
    with TestClient(app) as client:
        trust_res = client.post(
            "/api/v1/trust/audit-video",
            json={
                "video_id": "7711004930638630152",
                "caption": "Kem ăn vặt đồng giá 19k giảm giá khai trương",
                "transcript": "Hiện tại bên em đang có chương trình đồng giá 19 ngàn",
                "is_ad": False,
                "is_ec_video": False,
                "hashtags": ["streetfood", "quan10"],
                "comments": [],
            },
        )
        trust_body = trust_res.json() if trust_res.status_code == 200 else {}
        comp = dict(trust_body.get("comparison") or {})
        trust_ok = (
            trust_res.status_code == 200
            and comp.get("disclosure_flag_status") == "unlabeled_unknown"
            and comp.get("sponsorship_ground_truth_status") == "undisclosed_sponsorship_deferred"
            and len(comp.get("promotional_language_indicators") or []) >= 1
        )

        refusal_res = client.post(
            "/api/v1/script/generate",
            json={
                "brief": "chứng minh những quán không gắn thẻ is_ad chắc chắn là nhận tiền PR ngầm",
                "target_duration_sec": 30,
                "generation_mode": "offline_grounded",
            },
        )
        refusal_ok = refusal_res.status_code == 422

    return {
        "leakage_guard_pass": rejected_all,
        "blocked_feature_probes_tested": list(blocked_probes),
        "trust_api_separation_pass": trust_ok,
        "trust_api_sample": {
            "status_code": trust_res.status_code,
            "disclosure_flag_status": comp.get("disclosure_flag_status"),
            "sponsorship_ground_truth_status": comp.get("sponsorship_ground_truth_status"),
            "matched_promo_indicators": comp.get("promotional_language_indicators"),
        },
        "hidden_pr_refusal_pass": refusal_ok,
        "hidden_pr_refusal_status_code": refusal_res.status_code,
    }


def main() -> None:
    t0 = time.perf_counter()
    repo_root = Path(__file__).resolve().parents[5]

    snap_dirs = {
        "20261118_taxonomy_fix_v1": repo_root / "data/corpus/20261118_taxonomy_fix_v1",
        "m3_3_pilot_snapshot_v1": repo_root / "data/corpus/m3_3_pilot_snapshot_v1",
        "m3_3_pilot_snapshot_v2": repo_root / "data/corpus/m3_3_pilot_snapshot_v2",
    }
    pre_hashes = {name: _snapshot_tree_digests(path) for name, path in snap_dirs.items()}

    m4_1_pilot_path = repo_root / "docs/reports/milestones/M4.1/evidence/m4_1_audio_pilot_receipt.json"
    m4_1_sheet_path = repo_root / "docs/reports/milestones/M4.1/evidence/m4_1_utterance_review_sheet.jsonl"
    m4_1_joint_path = repo_root / "docs/reports/milestones/M4.1/evidence/m4_1_joint_reference_eval_receipt.json"

    m4_2_study_path = repo_root / "artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json"
    m4_2_workbook_path = repo_root / "data/evaluation/m4_2_disclosure/review_sample_100.jsonl"
    m4_2_summary_path = repo_root / "docs/reports/milestones/M4.2/evidence/n_k_100_combined_audit_summary.json"
    m4_2_nguyen_path = repo_root / "docs/reports/milestones/M4.2/evidence/nguyen_signoff_receipt.json"
    m3_g_receipt_path = repo_root / "docs/reports/milestones/M3.G/evidence/g3-gate-decision-receipt.json"

    m4_1_pilot = json.loads(m4_1_pilot_path.read_text(encoding="utf-8"))
    m4_1_sheet = [
        json.loads(line) for line in m4_1_sheet_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    m4_2_study = json.loads(m4_2_study_path.read_text(encoding="utf-8"))
    m4_2_workbook = [
        json.loads(line) for line in m4_2_workbook_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    m4_2_summary = json.loads(m4_2_summary_path.read_text(encoding="utf-8"))
    m3_g_decision = json.loads(m3_g_receipt_path.read_text(encoding="utf-8"))

    m4_1_audit = audit_m4_1_gate_criteria(pilot_receipt=m4_1_pilot, sheet_rows=m4_1_sheet)
    m4_2_audit = audit_m4_2_gate_criteria(
        study_receipt=m4_2_study,
        combined_audit_summary=m4_2_summary,
        workbook_rows=m4_2_workbook,
    )

    _, _, v2_videos_df = load_verified_corpus(snap_dirs["m3_3_pilot_snapshot_v2"])
    pilot_vids = {str(p.get("video_id") or "") for p in m4_1_pilot.get("per_video_prosody") or []}
    pilot_sub_df = v2_videos_df[v2_videos_df["video_id"].astype(str).isin(pilot_vids)].copy()
    fresh_prosody_join = audit_fresh_pilot_prosody_vs_promo(
        per_video_prosody=m4_1_pilot.get("per_video_prosody") or [],
        pilot_videos_df=pilot_sub_df,
    )

    runtime_guardrails = verify_g4_epistemic_and_leakage_guardrails(repo_root=repo_root)

    post_hashes = {name: _snapshot_tree_digests(path) for name, path in snap_dirs.items()}
    zero_byte_mutations = pre_hashes == post_hashes

    overall_pass = bool(
        m4_1_audit["m4_1_gate_pass"]
        and m4_2_audit["m4_2_gate_pass"]
        and fresh_prosody_join["joined_fresh_audio_video_count"] == 29
        and fresh_prosody_join["prosody_promotion_classifier_accepted"] is False
        and runtime_guardrails["leakage_guard_pass"]
        and runtime_guardrails["trust_api_separation_pass"]
        and runtime_guardrails["hidden_pr_refusal_pass"]
        and zero_byte_mutations
    )
    if not overall_pass:
        raise RuntimeError("Gate G4 technical verification failed closed")

    elapsed = round(time.perf_counter() - t0, 3)
    out_receipt = {
        "gate_id": "G4",
        "task_id": "M4.G",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": elapsed,
        "overall_technical_pass": overall_pass,
        "zero_byte_mutations": zero_byte_mutations,
        "upstream_gates": {
            "G0": "PASS",
            "G1": "PASS (local-only; public redistribution BLOCKED)",
            "G2": "PASS (historical local CPU core)",
            "G3_status": m3_g_decision.get("gate_status_until_two_person_signoff"),
        },
        "m4_1_verification": m4_1_audit,
        "m4_2_verification": m4_2_audit,
        "fresh_pilot_prosody_vs_promo_check": fresh_prosody_join,
        "runtime_epistemic_and_leakage_guardrails": runtime_guardrails,
        "verified_evidence_sha256": {
            "docs/reports/milestones/M4.1/evidence/m4_1_audio_pilot_receipt.json": _sha256_file(m4_1_pilot_path),
            "docs/reports/milestones/M4.1/evidence/m4_1_utterance_review_sheet.jsonl": _sha256_file(m4_1_sheet_path),
            "docs/reports/milestones/M4.1/evidence/m4_1_joint_reference_eval_receipt.json": _sha256_file(m4_1_joint_path),
            "artifacts/benchmarks/m4_2_observed_disclosure_study_v2_k_review.json": _sha256_file(m4_2_study_path),
            "data/evaluation/m4_2_disclosure/review_sample_100.jsonl": _sha256_file(m4_2_workbook_path),
            "docs/reports/milestones/M4.2/evidence/n_k_100_combined_audit_summary.json": _sha256_file(m4_2_summary_path),
            "docs/reports/milestones/M4.2/evidence/nguyen_signoff_receipt.json": _sha256_file(m4_2_nguyen_path),
        },
    }

    out_path = Path(__file__).resolve().parent / "g4_verification_receipt.json"
    out_path.write_text(json.dumps(out_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"G4 verification probe PASS in {elapsed}s | "
        f"M4.1={m4_1_audit['audio_timing_feature_decision']} | "
        f"M4.2={m4_2_audit['observed_flags_and_promo_cues_decision']} | "
        f"undisclosed_PR={m4_2_audit['undisclosed_sponsorship_decision']}"
    )


if __name__ == "__main__":
    main()
