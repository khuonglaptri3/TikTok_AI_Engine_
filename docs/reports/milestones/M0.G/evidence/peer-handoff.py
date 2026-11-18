"""Validate the G0 review handoff and generate its SHA256 inventory."""
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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    checks = []

    def check(name: str, passed: bool, detail=None) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    check("exact_bundle_layout", {p.name for p in BUNDLE.iterdir()} == {"README.md", "evidence", "superpowers"})
    check("exact_planning_layout", {p.name for p in (BUNDLE / "superpowers").iterdir()} == {"spec.md", "plan.md"})
    report = (BUNDLE / "README.md").read_text(encoding="utf-8")
    index = ROOT / "docs/reports/milestones/README.md"
    rows = [line for line in index.read_text(encoding="utf-8").splitlines() if line.startswith("| M0.G |")]
    check("single_consistent_index_row", len(rows) == 1 and "| IN_PROGRESS |" in rows[0] and "- Status: IN_PROGRESS" in report)
    check("owner_decision_still_pending", "- Gate result: NOT_RUN" in report and "HOLD unconditional G0" in report)
    check("mandatory_report_links", all(s in report for s in ("superpowers/spec.md", "superpowers/plan.md", "evidence/workflow.md")))
    documents = [BUNDLE / "README.md", BUNDLE / "superpowers/spec.md", BUNDLE / "superpowers/plan.md", OUT / "workflow.md", OUT / "peer-review.md"]
    broken = []
    for path in documents:
        text = path.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", text):
            target = target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            if not (path.parent / unquote(target)).exists():
                broken.append({"document": path.relative_to(ROOT).as_posix(), "target": target})
    check("live_report_local_links", not broken, broken)
    for script in OUT.glob("peer-*.py"):
        ast.parse(script.read_text(encoding="utf-8"), filename=script.name)
    check("audit_script_syntax", True)
    current = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    check("pinned_synchronized_revision", current == "c6c36131d2750b33fcede38871656e7c0ae703fc")
    sync = json.loads((OUT / "peer-git-sync.json").read_text(encoding="utf-8"))
    preserved = sync["preexisting_untracked"]
    check("preexisting_untracked_logs_preserved", all((ROOT / item["path"]).is_file() and sha(ROOT / item["path"]) == item["sha256"] for item in preserved), [item["path"] for item in preserved])
    changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=ROOT, text=True).splitlines()
    allowed = lambda p: p.startswith("docs/reports/milestones/M0.G/") or p == "docs/reports/milestones/README.md"
    check("tracked_changes_limited_to_review_bundle_and_index", all(allowed(p) for p in changed), changed)
    product_changes = subprocess.check_output(["git", "diff", "--name-only", "HEAD", "--", "packages", "apps", "pipelines", "tests", "pyproject.toml", "README.md", "AGENTS.md", "configs", "infra", "data", "artifacts", "scripts"], cwd=ROOT, text=True).splitlines()
    check("production_and_data_paths_unchanged", not product_changes, product_changes)
    check("tracked_mutation_scope", all(allowed(p) for p in changed), changed)
    raw_original = subprocess.check_output(["git", "show", "HEAD:docs/reports/milestones/M0.G/README.md"], cwd=ROOT)
    check("original_contributor_report_preserved", (OUT / "contributor-report-c6c36131.md").read_bytes() == raw_original)
    sync = json.loads((OUT / "peer-git-sync.json").read_text(encoding="utf-8"))
    preserved = sync.get("preexisting_untracked", sync.get("preserved_untracked", []))
    check("original_untracked_logs_preserved", len(preserved) == 3 and all(sha(ROOT / p["path"]) == p["sha256"] for p in preserved))
    result = json.loads((OUT / "peer-check-results.json").read_text(encoding="utf-8"))
    check("check_log_hashes_match", all(sha(OUT / c["log"]) == c["sha256"] for c in result["checks"]))
    runtime = json.loads((OUT / "peer-runtime-receipt.json").read_text(encoding="utf-8"))
    check("runtime_bytes_still_preserved", all(sha(ROOT / p) == expected for p, expected in runtime["runtime_sha256_before"].items()))
    check("two_policy_failures_reported_honestly", set(runtime["failed_checks"]) == {"policy_configuration_rejects_above_two", "policy_third_call_blocked"} and "G0-REV-1" in report)
    check("lint_failure_reported_honestly", any(c["name"] == "ruff" and c["exit_code"] == 1 for c in result["checks"]) and "G0-REV-2" in report)
    package = json.loads((OUT / "peer-package-results.json").read_text(encoding="utf-8"))
    check("clean_install_receipt", package["clean_install"] and package["package_exit_code"] == 0)
    check("english_authored_documentation", not any(re.search(r"kết quả|thực hiện|kiểm tra|báo cáo|hoàn thành|kế hoạch", p.read_text(encoding="utf-8"), re.I) for p in documents))
    check("final_secret_scan_recorded", "Zero secret leaks detected" in (OUT / "peer-secrets-final.log").read_text(encoding="utf-8"))
    receipt = {"checked_at": datetime.now(UTC).isoformat(), "head": current,
               "status": "PASS" if all(c["passed"] for c in checks) else "FAIL", "checks": checks,
               "scope": "Handoff integrity only; product policy and clean-lint acceptance gaps remain unresolved.",
               "excluded_archived_links": "contributor-report-c6c36131.md is a byte-exact historical archive retaining original link context."}
    (OUT / "peer-handoff.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    paths = sorted(p for p in BUNDLE.rglob("*") if p.is_file() and p.name != "peer-artifact-hashes.json") + [index]
    inventory = {"algorithm": "SHA256", "files": {p.relative_to(ROOT).as_posix(): sha(p) for p in paths}}
    inventory_path = OUT / "peer-artifact-hashes.json"
    inventory_path.write_text(json.dumps(inventory, indent=2), encoding="utf-8")
    inventory_ok = all(sha(ROOT / p) == expected for p, expected in inventory["files"].items())
    print(json.dumps({"handoff": receipt["status"], "checks": len(checks), "failed": [c for c in checks if not c["passed"]], "inventory_files": len(paths), "inventory_verified": inventory_ok}, ensure_ascii=False))
    return int(receipt["status"] != "PASS" or not inventory_ok)


if __name__ == "__main__":
    raise SystemExit(main())
