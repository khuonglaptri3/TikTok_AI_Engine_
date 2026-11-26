"""Deterministic Gate M5.G (G5) verification probe across M5.1 comment diagnostics and M5.2 4-aspect ABSA."""

from __future__ import annotations

import ast
import asyncio
import hashlib
import json
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import httpx

from apps.api.app.main import create_app
from apps.demo.presentation import format_trust_audit_markdown
from packages.analytics import load_verified_corpus
from packages.common.settings import AppSettings


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


def audit_m5_1_gate_criteria(
    *,
    eval_receipt: Mapping[str, Any],
    pool_rows: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Verify M5.1 real double-annotation, disjoint splits, uncertainty, and diagnostic-only gating."""
    ann = dict(eval_receipt.get("annotation_summary") or {})
    iaa = dict(ann.get("inter_annotator_agreement") or {})
    splits = dict(eval_receipt.get("split_video_counts") or {})
    held = dict(eval_receipt.get("held_out_third_metrics") or {})
    ablation = dict(eval_receipt.get("organic_duplicate_ablation_real_pool") or {})

    n_only_ok = [
        r for r in pool_rows if r.get("review_assignment") == "N_only" and r.get("N_human_verified") is True
    ]
    k_only_ok = [
        r for r in pool_rows if r.get("review_assignment") == "K_only" and r.get("K_human_verified") is True
    ]
    double_ok = [
        r
        for r in pool_rows
        if r.get("review_assignment") == "double_review_N_K"
        and r.get("N_human_verified") is True
        and r.get("K_human_verified") is True
    ]
    all_adj_ok = all(r.get("adjudicated_label") is not None for r in pool_rows)

    human_complete = (
        150 <= len(pool_rows) <= 300
        and len(double_ok) >= 60
        and len(n_only_ok) + len(k_only_ok) + len(double_ok) == len(pool_rows)
        and all_adj_ok
        and bool(eval_receipt.get("real_pilot_comments_available")) is True
    )
    disjoint_ok = int(splits.get("video_overlap_count", -1)) == 0 and int(held.get("evaluated_comment_count", 0)) >= 45

    missing_core = list(held.get("core_positive_classes_missing_support") or [])
    macro_p = float(held.get("macro_precision") or 0.0)
    macro_r = float(held.get("macro_recall") or 0.0)
    expected_auto_eligible = (
        human_complete
        and disjoint_ok
        and len(missing_core) == 0
        and macro_p >= 0.85
        and macro_r >= 0.60
    )
    actual_auto_eligible = bool(held.get("auto_filter_eligible"))
    rec_mode = str(held.get("recommended_mode") or "")

    policy_honest = (
        actual_auto_eligible == expected_auto_eligible
        and (
            (actual_auto_eligible and rec_mode == "auto_filter_validated")
            or (not actual_auto_eligible and rec_mode == "diagnostic_only_without_filtering")
        )
    )
    org_dup_ok = int(ablation.get("guarded_min_words_5_false_positives", 99)) == 0

    passed = human_complete and disjoint_ok and policy_honest and org_dup_ok
    return {
        "gate_check_passed": passed,
        "ruling": (
            "ACCEPTED_AUTO_FILTER_VALIDATED"
            if (passed and actual_auto_eligible)
            else "ACCEPTED_DIAGNOSTIC_ONLY_WITHOUT_AUTO_FILTERING"
            if passed
            else "REJECTED_POLICY_OR_ANNOTATION_VIOLATION"
        ),
        "total_pool_rows": len(pool_rows),
        "double_verified_count": len(double_ok),
        "raw_agreement_6class": float(iaa.get("raw_agreement") or 0.0),
        "cohens_kappa_6class": float(iaa.get("cohens_kappa") or 0.0),
        "positive_indicator_cohens_kappa": float(iaa.get("positive_indicator_cohens_kappa") or 0.0),
        "organic_duplicate_fp_before_after": [
            int(ablation.get("legacy_min_words_1_false_positives") or 0),
            int(ablation.get("guarded_min_words_5_false_positives") or 0),
        ],
        "held_out_core_missing_support": missing_core,
        "auto_filter_eligible": actual_auto_eligible,
        "recommended_mode": rec_mode,
    }


def audit_m5_2_gate_criteria(
    *,
    eval_receipt: Mapping[str, Any],
    pool_rows: Sequence[Mapping[str, Any]],
    expansion_summary: Mapping[str, Any],
) -> dict[str, Any]:
    """Verify M5.2 120-200 real double-annotation, disjoint train/dev/held_out, >=95% NFC spans, and F1 gates."""
    ann = dict(eval_receipt.get("annotation_summary") or {})
    iaa = dict(ann.get("inter_annotator_agreement") or {})
    gold_span = dict(ann.get("gold_span_audit") or {})
    splits = dict(eval_receipt.get("split_counts") or {})
    held = dict(eval_receipt.get("held_out_metrics") or {})
    pred_span = dict(held.get("span_audit") or {})
    per_aspect = dict(held.get("per_aspect_detection") or {})

    n_only_ok = [
        r for r in pool_rows if r.get("review_assignment") == "N_only" and r.get("N_human_verified") is True
    ]
    k_only_ok = [
        r for r in pool_rows if r.get("review_assignment") == "K_only" and r.get("K_human_verified") is True
    ]
    double_ok = [
        r
        for r in pool_rows
        if r.get("review_assignment") == "double_review_N_K"
        and r.get("N_human_verified") is True
        and r.get("K_human_verified") is True
    ]

    human_complete = (
        120 <= len(pool_rows) <= 200
        and len(double_ok) >= 50
        and len(n_only_ok) + len(k_only_ok) + len(double_ok) == len(pool_rows)
        and int(ann.get("unique_video_count") or 0) >= 10
        and bool(eval_receipt.get("real_pilot_data_available")) is True
    )
    disjoint_ok = (
        int(splits.get("video_overlap_count", -1)) == 0
        and int(expansion_summary.get("video_overlap_between_train_and_m5_2_pool", -1)) == 0
        and expansion_summary.get("human_verified") is False
    )

    spans_ok = (
        float(gold_span.get("validity_rate") or 0.0) >= 0.95
        and int(gold_span.get("invalid_spans", 1)) == 0
        and float(pred_span.get("validity_rate") or 0.0) >= 0.95
        and bool(held.get("all_predicted_aspects_span_backed")) is True
    )

    det_f1 = float(held.get("aspect_detection_macro_f1") or 0.0)
    sent_f1 = float(held.get("observed_sentiment_macro_f1") or 0.0)
    aspect_f1s = [
        float((per_aspect.get(a) or {}).get("f1") or 0.0)
        for a in ("taste", "price", "hygiene", "service")
    ]
    conservative_4aspect_f1 = round(sum(aspect_f1s) / 4.0, 4)
    service_gold_support = int(((per_aspect.get("service") or {}).get("gold_support")) or 0)

    f1_gates_ok = (
        det_f1 >= 0.65
        and sent_f1 >= 0.60
        and conservative_4aspect_f1 >= 0.65
        and bool(held.get("m5_2_pilot_gate_eligible")) is True
    )

    passed = human_complete and disjoint_ok and spans_ok and f1_gates_ok
    return {
        "gate_check_passed": passed,
        "ruling": (
            "ACCEPTED_QUALIFIED_SPAN_GROUNDED_SENTIMENT_DISCREPANCY"
            if passed
            else "REJECTED_F1_SPAN_OR_LEAKAGE_VIOLATION"
        ),
        "total_units": len(pool_rows),
        "unique_videos": int(ann.get("unique_video_count") or 0),
        "double_verified_units": len(double_ok),
        "cohens_kappa_presence": float(iaa.get("cohens_kappa_presence") or 0.0),
        "cohens_kappa_4state": float(iaa.get("cohens_kappa_4state") or 0.0),
        "gold_span_validity_rate": float(gold_span.get("validity_rate") or 0.0),
        "predicted_span_validity_rate": float(pred_span.get("validity_rate") or 0.0),
        "held_out_aspect_detection_macro_f1": det_f1,
        "conservative_4aspect_f1": conservative_4aspect_f1,
        "held_out_observed_sentiment_macro_f1": sent_f1,
        "service_gold_support": service_gold_support,
        "qualifications": [
            "Creator-vs-viewer deltas are framed strictly as observed sentiment_discrepancy (>=3 viewer comments), never deception, hygiene truth, or diner consensus.",
            f"service had gold_support={service_gold_support} in the 180-unit real pilot sample; runtime enforces min_viewer_comments=3 support abstention.",
        ],
    }


def _check_ui_hide_seeding_default_false(ui_path: Path) -> bool:
    tree = ast.parse(ui_path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "hide_seed_chk":
                    if isinstance(node.value, ast.Call):
                        for kw in node.value.keywords:
                            if kw.arg == "value" and isinstance(kw.value, ast.Constant):
                                return kw.value.value is False
    return False


def audit_live_trust_api_and_demo_limits() -> dict[str, Any]:
    """Verify live FastAPI /api/v1/trust/audit-video & /demo/ diagnostic defaults, abstention, and wording."""
    app = create_app(
        settings=AppSettings.from_env().model_copy(update={"gemini_api_key": ""}),
        mount_demo=False,
    )

    async def _probe() -> tuple[dict[str, Any], dict[str, Any]]:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app), base_url="http://testserver"
        ) as client:
            r_low = await client.post(
                "/api/v1/trust/audit-video",
                json={
                    "video_id": "v_g5_low",
                    "caption": "Bún bò Huế đậm đà",
                    "transcript": "Nước dùng ngon xuất sắc",
                    "comments": [
                        {"comment_id": "c1", "author_handle": "u1", "text": "Nước dùng hơi mặn"},
                        {"comment_id": "c2", "author_handle": "u2", "text": "Vị nhạt quá"},
                    ],
                },
            )
            assert r_low.status_code == 200
            r_full = await client.post(
                "/api/v1/trust/audit-video",
                json={
                    "video_id": "v_g5_full",
                    "caption": "Phở bò giá 45k",
                    "transcript": "Nước dùng đậm đà ngon lắm",
                    "utterances": [{"start_sec": 0.0, "end_sec": 2.5, "text": "Nước dùng đậm đà ngon lắm"}],
                    "comments": [
                        {"comment_id": "c1", "author_handle": "u1", "text": "Nước dùng hơi mặn, giá 45k bình thường"},
                        {"comment_id": "c2", "author_handle": "u2", "text": "Thịt bò không ngon"},
                        {"comment_id": "c3", "author_handle": "u3", "text": "Nước lèo dở quá"},
                        {"comment_id": "s1", "author_handle": "sp1", "text": "Inbox zalo 0909123456 nhận voucher"},
                    ],
                },
            )
            assert r_full.status_code == 200
            return dict(r_low.json()), dict(r_full.json())

    low_body, full_body = asyncio.run(_probe())
    low_comp = dict(low_body.get("comparison") or {})
    full_comp = dict(full_body.get("comparison") or {})

    low_abstained = (
        low_comp.get("supported_overlapping_aspects") == []
        and low_comp.get("supported_sentiment_discrepancy") is None
        and (low_comp.get("aspect_discrepancies") or {}).get("taste", {}).get("comparison_status")
        == "abstained_viewer_low_support"
    )
    full_policy = str(full_body.get("comment_filter_policy") or "")
    md = format_trust_audit_markdown(full_body, hide_seeding=False)
    ui_default_false = _check_ui_hide_seeding_default_false(_REPO_ROOT / "apps" / "demo" / "ui.py")

    md_ok = (
        "0909123456" in md
        and "absent_unknown" in md
        and "v_g5_full_utt_000" in md
        and ("sentiment discrepancy" in md.lower() or "độ lệch cảm xúc quan sát được" in md.lower())
    )

    passed = (
        low_abstained
        and full_policy == "diagnostic_only_unvalidated"
        and full_comp.get("supported_overlapping_aspects") == ["taste"]
        and len(full_body.get("filter_sensitivity", {}).get("threshold_sensitivity") or []) == 9
        and ui_default_false
        and md_ok
    )
    return {
        "gate_check_passed": passed,
        "comment_filter_policy": full_policy,
        "low_support_abstained": low_abstained,
        "demo_hide_seeding_default": not ui_default_false,
        "markdown_limits_and_spans_rendered": md_ok,
    }


def run_g5_gate_probe() -> dict[str, Any]:
    t0 = time.perf_counter()
    snapshots = (
        "20261118_taxonomy_fix_v1",
        "m3_3_pilot_snapshot_v1",
        "m3_3_pilot_snapshot_v2",
        "m3_3_playwright_comments_20261125_v5",
    )
    before_digests = {
        sid: _snapshot_tree_digests(_REPO_ROOT / "data" / "corpus" / sid) for sid in snapshots
    }

    m5_1_eval_path = _REPO_ROOT / "artifacts" / "benchmarks" / "m5_1_real_pilot_eval_v1.json"
    m5_1_pool_path = _REPO_ROOT / "data" / "annotations" / "m5_1_pilot_pool.jsonl"
    m5_2_eval_path = _REPO_ROOT / "artifacts" / "benchmarks" / "m5_2_real_pilot_eval_v1.json"
    m5_2_locked_eval_path = _REPO_ROOT / "artifacts" / "benchmarks" / "m5_2_real_pilot_locked_eval_v1.json"
    m5_2_pool_path = _REPO_ROOT / "data" / "annotations" / "m5_2_pilot_pool.jsonl"
    expansion_summary_path = _REPO_ROOT / "data" / "annotations" / "absa_annotation_summary_v1.json"

    m5_1_eval = json.loads(m5_1_eval_path.read_text(encoding="utf-8"))
    m5_1_pool = [
        json.loads(line) for line in m5_1_pool_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    m5_2_eval = json.loads(m5_2_eval_path.read_text(encoding="utf-8"))
    m5_2_pool = [
        json.loads(line) for line in m5_2_pool_path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    expansion_summary = json.loads(expansion_summary_path.read_text(encoding="utf-8"))

    m5_1_res = audit_m5_1_gate_criteria(eval_receipt=m5_1_eval, pool_rows=m5_1_pool)
    m5_2_res = audit_m5_2_gate_criteria(
        eval_receipt=m5_2_eval,
        pool_rows=m5_2_pool,
        expansion_summary=expansion_summary,
    )
    live_res = audit_live_trust_api_and_demo_limits()

    after_digests = {
        sid: _snapshot_tree_digests(_REPO_ROOT / "data" / "corpus" / sid) for sid in snapshots
    }
    zero_mutations = before_digests == after_digests
    all_passed = (
        m5_1_res["gate_check_passed"]
        and m5_2_res["gate_check_passed"]
        and live_res["gate_check_passed"]
        and zero_mutations
    )
    elapsed_sec = round(time.perf_counter() - t0, 3)

    ev_dir = Path(__file__).resolve().parent
    ver_receipt = {
        "gate_id": "G5",
        "report_id": "M5.G",
        "executed_at": datetime.now(UTC).isoformat(),
        "elapsed_seconds": elapsed_sec,
        "provider_spend_usd": 0.0,
        "all_technical_checks_passed": all_passed,
        "zero_snapshot_byte_mutations": zero_mutations,
        "m5_1_audit": m5_1_res,
        "m5_2_audit": m5_2_res,
        "live_api_and_demo_audit": live_res,
        "evidence_sha256": {
            "artifacts/benchmarks/m5_1_real_pilot_eval_v1.json": _sha256_file(m5_1_eval_path),
            "data/annotations/m5_1_pilot_pool.jsonl": _sha256_file(m5_1_pool_path),
            "artifacts/benchmarks/m5_2_real_pilot_eval_v1.json": _sha256_file(m5_2_eval_path),
            "artifacts/benchmarks/m5_2_real_pilot_locked_eval_v1.json": _sha256_file(m5_2_locked_eval_path),
            "data/annotations/m5_2_pilot_pool.jsonl": _sha256_file(m5_2_pool_path),
            "data/annotations/absa_annotation_summary_v1.json": _sha256_file(expansion_summary_path),
        },
        "verified_snapshots": after_digests,
    }
    decision_receipt = {
        "gate_id": "G5",
        "report_id": "M5.G",
        "technical_probe_status": "PASS" if all_passed else "FAIL",
        "global_gate_status": "NOT_RUN",
        "governance_note": "Two-person reciprocal gate rule: K sign-off recorded; global G5 flips from NOT_RUN to PASS once N co-signs.",
        "feature_decisions": {
            "observable_comment_indicators_m5_1": {
                "ruling": m5_1_res["ruling"],
                "auto_filter_accepted": False,
                "accepted_runtime_mode": "diagnostic_only_without_filtering",
            },
            "four_aspect_absa_with_source_spans_m5_2": {
                "ruling": m5_2_res["ruling"],
                "min_viewer_comments_abstention": 3,
                "service_qualification": "gold_support=0 in 180-unit real sample; sparse-thread abstention enforced",
            },
            "automated_bot_payment_or_diner_consensus_claims": {
                "ruling": "REJECTED_AND_UNACCEPTED",
            },
        },
        "contributor_signoff": {
            "K_status": "PASS" if all_passed else "BLOCKED",
            "K_signed_at": datetime.now(UTC).isoformat(),
            "N_status": "PENDING_CO_SIGN",
        },
    }

    (ev_dir / "g5_verification_receipt.json").write_text(
        json.dumps(ver_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (ev_dir / "g5-gate-decision-receipt.json").write_text(
        json.dumps(decision_receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if not all_passed:
        raise RuntimeError(f"G5 gate probe failed: {ver_receipt}")
    print(f"PASS: Gate G5 technical checks passed in {elapsed_sec}s (0 snapshot byte mutations)")
    return ver_receipt


if __name__ == "__main__":
    run_g5_gate_probe()
