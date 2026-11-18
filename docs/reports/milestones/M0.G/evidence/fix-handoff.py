"""Validate remediation evidence without rewriting the earlier failed review."""
from __future__ import annotations

import ast
import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[5]
BUNDLE = Path(__file__).resolve().parent.parent
OUT = BUNDLE / "evidence"
SOURCE_PATHS = {
    "packages/common/settings/__init__.py",
    "packages/llm/clients/gemini.py",
    "apps/api/app/routers/health.py",
    "packages/retrieval/sparse/bm25.py",
    "tests/unit/test_llm_call_budget.py",
}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(name: str) -> dict:
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def main() -> int:
    checks = []

    def check(name: str, passed: bool, detail=None) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    report = (BUNDLE / "README.md").read_text(encoding="utf-8")
    index = ROOT / "docs/reports/milestones/README.md"
    rows = [line for line in index.read_text(encoding="utf-8").splitlines() if line.startswith("| M0.G |")]
    check("exact_bundle_layout", {p.name for p in BUNDLE.iterdir()} == {"README.md", "evidence", "superpowers"})
    check("exact_planning_layout", {p.name for p in (BUNDLE / "superpowers").iterdir()} == {"spec.md", "plan.md"})
    check("index_status_matches", len(rows) == 1 and "| IN_PROGRESS |" in rows[0] and "- Status: IN_PROGRESS" in report)
    check("owner_decision_pending", "- Gate result: NOT_RUN" in report and "owner" in report.lower())
    check("technical_recommendation_only", "Technical recommendation: PASS" in report)
    check("planning_workflow_linked", all(s in report for s in ("superpowers/spec.md", "superpowers/plan.md", "evidence/workflow.md")))
    broken = []
    documents = [BUNDLE / "README.md", BUNDLE / "superpowers/spec.md", BUNDLE / "superpowers/plan.md", OUT / "workflow.md", OUT / "fix-code-review.md"]
    generated = {OUT / "fix-handoff.json", OUT / "fix-artifact-hashes.json"}
    for document in documents:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            target = target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            path = (document.parent / unquote(target)).resolve()
            if not path.exists() and path not in generated:
                broken.append({"document": document.name, "target": target})
    check("live_document_links", not broken, broken)
    for path in OUT.glob("fix-*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=path.name)
    check("verification_script_syntax", True)
    result = read("fix-check-results.json")
    check("all_required_commands_pass", bool(result.get("completed_at")) and len(result["checks"]) == 6 and all(c["exit_code"] == 0 for c in result["checks"]))
    check("fresh_command_log_hashes", all(sha(OUT / c["log"]) == c["sha256"] for c in result["checks"]))
    check("tested_source_hashes_match", set(result["source_sha256"]) == SOURCE_PATHS and all(sha(ROOT / p) == value for p, value in result["source_sha256"].items()))
    check("red_green_recorded", "12 failed, 9 passed" in (OUT / "fix-red-budget.log").read_text(encoding="utf-8") and "34 passed" in (OUT / "fix-green-budget.log").read_text(encoding="utf-8"))
    check("review_fix_red_green_recorded", "3 failed, 1 passed" in (OUT / "fix-red-review-budget.log").read_text(encoding="utf-8") and "38 passed" in (OUT / "fix-green-reviewed-budget.log").read_text(encoding="utf-8"))
    runtime = read("fix-runtime-receipt.json")
    check("runtime_assertions_all_pass", bool(runtime["checks"]) and not runtime.get("unexpected_error") and not runtime["failed_checks"] and all(c["passed"] for c in runtime["checks"]))
    check("runtime_source_matches_suite", runtime["source_sha256"] == result["source_sha256"])
    check("no_live_provider_calls", runtime["live_provider_calls"] == 0 and runtime["provider_spend_usd"] == 0)
    check("runtime_original_bytes_preserved", all(sha(ROOT / p) == expected for p, expected in runtime["runtime_sha256_before"].items()))
    historical = read("peer-artifact-hashes.json")["files"]
    evidence_prefix = OUT.relative_to(ROOT).as_posix() + "/"
    immutable = {p: value for p, value in historical.items() if p.startswith(evidence_prefix) and not p.endswith("/workflow.md")}
    check("earlier_evidence_preserved", bool(immutable) and all(sha(ROOT / p) == value for p, value in immutable.items()))
    check("previous_review_archived", sha(OUT / "peer-review-report-before-fixes.md") == historical[(BUNDLE / "README.md").relative_to(ROOT).as_posix()])
    originals = read("peer-git-sync.json")["preexisting_untracked"]
    check("unrelated_logs_preserved", len(originals) == 3 and all(sha(ROOT / p["path"]) == p["sha256"] for p in originals))
    changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=ROOT, text=True).splitlines()
    allowed = lambda p: p in SOURCE_PATHS or p.startswith("docs/reports/milestones/M0.G/") or p == "docs/reports/milestones/README.md"
    check("tracked_source_scope", all(allowed(p) for p in changed), changed)
    protected = subprocess.check_output(["git", "diff", "--name-only", "HEAD", "--", "data", "artifacts", "README.md", "AGENTS.md", "pyproject.toml", "infra", "configs", "scripts"], cwd=ROOT, text=True).splitlines()
    check("protected_paths_unchanged", not protected, protected)
    package = read("fix-package-results.json")
    check("clean_package_install", package["clean_install"] and package["package_exit_code"] == 0)
    check("package_source_matches_suite", package["source_sha256"] == result["source_sha256"])
    check("final_secret_scan", "Zero secret leaks detected" in (OUT / "fix-secrets-final.log").read_text(encoding="utf-8"))
    check("english_authored_prose", not any(re.search(r"kết quả|thực hiện|kiểm tra|báo cáo|hoàn thành|kế hoạch", p.read_text(encoding="utf-8"), re.I) for p in documents))
    receipt = {"checked_at": datetime.now(UTC).isoformat(), "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
               "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
               "source_sha256": result["source_sha256"], "checks": checks,
               "formal_gate": "NOT_RUN", "technical_recommendation": "PASS; owner decision pending"}
    (OUT / "fix-handoff.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    files = sorted(p for p in BUNDLE.rglob("*") if p.is_file() and p.name != "fix-artifact-hashes.json") + [index] + [ROOT / p for p in sorted(SOURCE_PATHS)]
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in files}
    (OUT / "fix-artifact-hashes.json").write_text(json.dumps({"algorithm": "SHA256", "files": hashes}, indent=2), encoding="utf-8")
    inventory_ok = all(sha(ROOT / p) == value for p, value in hashes.items())
    print(json.dumps({"status": receipt["status"], "checks": len(checks), "failed": [c for c in checks if not c["passed"]], "inventory_files": len(hashes), "inventory_verified": inventory_ok}))
    return int(receipt["status"] != "PASS" or not inventory_ok)


if __name__ == "__main__":
    raise SystemExit(main())
