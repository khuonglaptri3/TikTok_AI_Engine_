from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any


def _load_g6_module() -> Any:
    repo_root = Path(__file__).resolve().parents[2]
    script_path = (
        repo_root / "docs" / "reports" / "milestones" / "M6.G" / "evidence" / "run_g6_checks.py"
    )
    if not script_path.is_file():
        raise FileNotFoundError(f"Missing M6.G probe script: {script_path}")
    spec = importlib.util.spec_from_file_location("run_g6_checks", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_audit_upstream_gates_and_tasks_fails_closed_on_incomplete_gate_or_task() -> None:
    mod = _load_g6_module()
    ok = mod.audit_upstream_gates_and_tasks(
        gate_statuses={"G0": "PASS", "G1": "PASS", "G2": "PASS", "G3": "PASS", "G4": "PASS", "G5": "PASS"},
        task_statuses={tid: "COMPLETE" for tid in mod.REQUIRED_UPSTREAM_TASKS},
    )
    assert ok["upstream_all_ready"] is True

    bad_gate = mod.audit_upstream_gates_and_tasks(
        gate_statuses={"G0": "PASS", "G1": "PASS", "G2": "PASS", "G3": "PASS", "G4": "NOT_RUN", "G5": "PASS"},
        task_statuses={tid: "COMPLETE" for tid in mod.REQUIRED_UPSTREAM_TASKS},
    )
    assert bad_gate["upstream_all_ready"] is False
    assert "G4" in bad_gate["unready_gates"]

    bad_task_map = {tid: "COMPLETE" for tid in mod.REQUIRED_UPSTREAM_TASKS}
    bad_task_map["M6.2"] = "IN_PROGRESS"
    bad_task = mod.audit_upstream_gates_and_tasks(
        gate_statuses={"G0": "PASS", "G1": "PASS", "G2": "PASS", "G3": "PASS", "G4": "PASS", "G5": "PASS"},
        task_statuses=bad_task_map,
    )
    assert bad_task["upstream_all_ready"] is False
    assert "M6.2" in bad_task["incomplete_tasks"]


def test_evaluate_hosting_eligibility_blocks_public_upload_without_redistribution_rights() -> None:
    mod = _load_g6_module()
    hosting = mod.evaluate_public_hosting_candidates(
        measured_peak_rss_mib=1150.0,
        measured_artifact_disk_mib=118.5,
        source_redistribution_licensed=False,
    )
    assert hosting["local_cpu_release_decision"] == "PASS"
    assert hosting["public_hosting_decision"] == "BLOCKED"
    assert hosting["blocking_reasons"]
    assert "redistribution" in " ".join(hosting["blocking_reasons"]).lower()
    assert len(hosting["candidates"]) >= 3


def test_probe_live_release_runtime_verifies_end_to_end_demo_and_error_guards() -> None:
    mod = _load_g6_module()
    runtime = mod.probe_live_release_runtime()
    assert runtime["runtime_all_passed"] is True
    assert runtime["corpus_snapshot_id"] == "m3_3_pilot_snapshot_v2"
    assert runtime["multimodal_snapshot_id"] == "m3_3_playwright_comments_20261125_v5"
    assert runtime["multimodal_total_comments"] == 2823
    assert runtime["missing_key_status_code"] == 503
    assert runtime["ood_status_code"] == 422
    assert runtime["epistemic_disclosure_status_code"] == 422
    assert runtime["demo_html_status_code"] == 200
