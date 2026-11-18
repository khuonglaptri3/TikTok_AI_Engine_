"""Verify publication integrity and explicitly retain failed integration checks."""
from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
BUNDLE = OUT.parent
PUBLISHED = "--published" in sys.argv


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail=None) -> None:
        checks.append({"name": name, "passed": bool(ok), "detail": detail})

    baseline = json.loads((OUT / "publish-baseline.json").read_text(encoding="utf-8"))
    result = json.loads((OUT / "publish-check-results.json").read_text(encoding="utf-8"))
    runtime = json.loads((OUT / "publish-runtime-receipt.json").read_text(encoding="utf-8"))
    report = (BUNDLE / "README.md").read_text(encoding="utf-8")
    index = ROOT / "docs/reports/milestones/README.md"
    check("exact_bundle", {p.name for p in BUNDLE.iterdir()} == {"README.md", "evidence", "superpowers"})
    check("exact_planning", {p.name for p in (BUNDLE / "superpowers").iterdir()} == {"spec.md", "plan.md"})
    rows = [s for s in index.read_text(encoding="utf-8").splitlines() if s.startswith("| M0.G |")]
    check("index_status", len(rows) == 1 and "| IN_PROGRESS |" in rows[0] and "- Status: IN_PROGRESS" in report)
    check("formal_gate_pending", "- Gate result: NOT_RUN" in report)
    check("draft_and_failures_visible", "draft" in report.lower() and "G0-INTEGRATION-1" in report and "FAIL" in report)
    check("actual_workflow_described", "not classic Gitflow" in report and "develop" in report)
    expected = {"secrets": 0, "pip-check": 0, "mypy": 1, "ruff": 0, "contract-smoke": 0, "pytest-full": 2}
    check("required_results_recorded", bool(result.get("completed_at")) and {c["name"]: c["exit_code"] for c in result["checks"]} == expected)
    check("command_log_hashes", all(digest(OUT / c["log"]) == c["sha256"] for c in result["checks"]))
    check("source_hashes", all(digest(ROOT / p) == value for p, value in result["source_sha256"].items()))
    check("runtime_source_parity", runtime["source_sha256"] == result["source_sha256"])
    check("runtime_passes", len(runtime["checks"]) == 38 and not runtime["failed_checks"] and not runtime.get("unexpected_error"))
    check("zero_provider_calls", runtime["live_provider_calls"] == 0 and runtime["provider_spend_usd"] == 0)
    check("focused_budget_passes", "38 passed" in (OUT / "publish-budget.log").read_text(encoding="utf-8"))
    check("runtime_artifacts_untouched", all(digest(ROOT / p) == value for p, value in runtime["runtime_sha256_before"].items()))
    upstream_files = ["pipelines/build_dense_sparse_index/dense.py", "pipelines/benchmark_retrieval/dense_hybrid_pilot.py", "tests/unit/test_dense_hybrid_retrieval.py"]
    check(
        "failing_upstream_git_content_unchanged",
        subprocess.run(
            ["git", "diff", "--quiet", baseline["fetched_main"], "--", *upstream_files],
            cwd=ROOT,
        ).returncode == 0,
    )
    sync = json.loads((OUT / "peer-git-sync.json").read_text(encoding="utf-8"))
    check("unrelated_logs_preserved", all(digest(ROOT / p["path"]) == p["sha256"] for p in sync["preexisting_untracked"]))
    for manifest_name in ("peer-artifact-hashes.json", "fix-artifact-hashes.json"):
        old = json.loads((OUT / manifest_name).read_text(encoding="utf-8"))["files"]
        prefix = OUT.relative_to(ROOT).as_posix() + "/"
        immutable = {p: value for p, value in old.items() if p.startswith(prefix) and not p.endswith("/workflow.md")}
        check("historical_evidence:" + manifest_name, all(digest(ROOT / p) == value for p, value in immutable.items()))
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    check("topic_branch", branch == baseline["topic_branch"])
    changed = subprocess.check_output(["git", "diff", baseline["fetched_main"], "--name-only"], cwd=ROOT, text=True).splitlines()
    authorized = set(baseline["authorized_paths"]) | {".gitattributes"}
    check("change_scope", all(p in authorized or p.startswith("docs/reports/milestones/M0.G/") for p in changed), changed)
    check("no_conflicts", not subprocess.check_output(["git", "ls-files", "--unmerged"], cwd=ROOT, text=True).strip())
    paths = [BUNDLE / "README.md", BUNDLE / "superpowers/spec.md", BUNDLE / "superpowers/plan.md", OUT / "workflow.md", OUT / "publish-pr-body.md"]
    broken = []
    for path in paths:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", path.read_text(encoding="utf-8")):
            target = target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            if not (path.parent / unquote(target)).exists():
                broken.append({"file": path.name, "target": target})
    check("live_links", not broken, broken)
    for path in OUT.glob("publish-*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    check("verification_script_syntax", True)
    check("final_secret_scan", "Zero secret leaks detected" in (OUT / "publish-secrets-final.log").read_text(encoding="utf-8"))
    if PUBLISHED:
        publication = json.loads((OUT / "publish-github-receipt.json").read_text(encoding="utf-8"))
        check("published_draft_pr", publication["push_exit"] == 0 and publication["pr"]["isDraft"] and publication["pr"]["baseRefName"] == "main" and publication["pr"]["headRefName"] == branch)
    receipt = {"checked_at": datetime.now(UTC).isoformat(), "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
               "scope": "Publication/evidence integrity only; integrated full pytest and mypy FAIL remain visible; not merge approval.",
               "formal_gate": "NOT_RUN", "draft": True, "source_sha256": result["source_sha256"], "checks": checks}
    (OUT / "publish-handoff.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    files = sorted(p for p in BUNDLE.rglob("*") if p.is_file() and p.name != "publish-artifact-hashes.json")
    files += [index, ROOT / ".gitattributes"] + [ROOT / p for p in result["source_sha256"]]
    manifest = {"algorithm": "SHA256", "scope": receipt["scope"], "files": {p.relative_to(ROOT).as_posix(): digest(p) for p in files}}
    (OUT / "publish-artifact-hashes.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"status": receipt["status"], "checks": len(checks), "failed": [c for c in checks if not c["passed"]], "inventory_files": len(files), "published_mode": PUBLISHED}))
    return int(receipt["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
