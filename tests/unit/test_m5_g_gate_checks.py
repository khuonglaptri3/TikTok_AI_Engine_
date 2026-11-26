from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_g5_module() -> Any:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = repo_root / "docs" / "reports" / "milestones" / "M5.G" / "evidence" / "run_g5_checks.py"
    if not script_path.is_file():
        raise FileNotFoundError(f"Missing M5.G probe script: {script_path}")
    spec = importlib.util.spec_from_file_location("run_g5_checks", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_audit_m5_1_gate_criteria_accepts_diagnostic_only_and_rejects_false_auto_filter() -> None:
    mod = _load_g5_module()
    repo_root = Path(__file__).resolve().parents[2]
    import json

    eval_json = json.loads(
        (repo_root / "artifacts" / "benchmarks" / "m5_1_real_pilot_eval_v1.json").read_text(encoding="utf-8")
    )
    pool_rows = [
        json.loads(line)
        for line in (repo_root / "data" / "annotations" / "m5_1_pilot_pool.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    res = mod.audit_m5_1_gate_criteria(eval_receipt=eval_json, pool_rows=pool_rows)
    assert res["gate_check_passed"] is True
    assert res["ruling"] == "ACCEPTED_DIAGNOSTIC_ONLY_WITHOUT_AUTO_FILTERING"

    # Tampered receipt claiming auto_filter_eligible=True despite missing core positive classes must fail
    tampered = json.loads(json.dumps(eval_json))
    tampered["held_out_third_metrics"]["auto_filter_eligible"] = True
    tampered["held_out_third_metrics"]["recommended_mode"] = "auto_filter_validated"
    bad_res = mod.audit_m5_1_gate_criteria(eval_receipt=tampered, pool_rows=pool_rows)
    assert bad_res["gate_check_passed"] is False


def test_audit_m5_2_gate_criteria_enforces_human_signoff_disjoint_train_and_f1_gates() -> None:
    mod = _load_g5_module()
    repo_root = Path(__file__).resolve().parents[2]
    import json

    eval_json = json.loads(
        (repo_root / "artifacts" / "benchmarks" / "m5_2_real_pilot_eval_v1.json").read_text(encoding="utf-8")
    )
    pool_rows = [
        json.loads(line)
        for line in (repo_root / "data" / "annotations" / "m5_2_pilot_pool.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    train_summary = json.loads(
        (repo_root / "data" / "annotations" / "absa_annotation_summary_v1.json").read_text(encoding="utf-8")
    )
    res = mod.audit_m5_2_gate_criteria(
        eval_receipt=eval_json,
        pool_rows=pool_rows,
        expansion_summary=train_summary,
    )
    assert res["gate_check_passed"] is True
    assert res["ruling"] == "ACCEPTED_QUALIFIED_SPAN_GROUNDED_SENTIMENT_DISCREPANCY"
    assert res["conservative_4aspect_f1"] >= 0.65

    # Reject if train/eval video overlap > 0
    bad_train = dict(train_summary)
    bad_train["video_overlap_between_train_and_m5_2_pool"] = 2
    bad_res = mod.audit_m5_2_gate_criteria(
        eval_receipt=eval_json,
        pool_rows=pool_rows,
        expansion_summary=bad_train,
    )
    assert bad_res["gate_check_passed"] is False


def test_audit_live_trust_api_and_demo_limits_pass() -> None:
    mod = _load_g5_module()
    live = mod.audit_live_trust_api_and_demo_limits()
    assert live["gate_check_passed"] is True
    assert live["comment_filter_policy"] == "diagnostic_only_unvalidated"
    assert live["low_support_abstained"] is True
    assert live["demo_hide_seeding_default"] is False
