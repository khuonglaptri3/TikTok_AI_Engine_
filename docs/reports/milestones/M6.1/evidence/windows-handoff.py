"""Validate both task bundles and source-bound integration evidence."""
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
M6 = Path(__file__).resolve().parent.parent
G0 = ROOT / "docs/reports/milestones/M0.G"
OUT = M6 / "evidence"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    checks = []

    def check(name: str, ok: bool, detail=None) -> None:
        checks.append({"name": name, "passed": bool(ok), "detail": detail})

    result = read(OUT / "windows-check-results.json")
    runtime = read(G0 / "evidence/merge-runtime-receipt.json")
    package = read(G0 / "evidence/merge-package-results.json")
    source = result["source_sha256"]
    check("all_required_checks_green", bool(result.get("completed_at")) and len(result["checks"]) == 7 and all(c["exit_code"] == 0 for c in result["checks"]))
    check("check_log_hashes", all(sha(OUT / c["log"]) == c["sha256"] for c in result["checks"]))
    check("exact_tested_source", all(sha(ROOT / p) == value for p, value in source.items()))
    check("runtime_source_parity", runtime["source_sha256"] == source)
    check("package_source_parity", package["source_sha256"] == source)
    check("runtime_green", len(runtime["checks"]) == 38 and not runtime["failed_checks"] and not runtime.get("unexpected_error"))
    check("clean_package_install", package["clean_install"] and package["package_exit_code"] == 0)
    check("zero_live_provider_spend", runtime["live_provider_calls"] == 0 and runtime["provider_spend_usd"] == 0)
    check("runtime_gold_index_bytes_preserved", all(sha(ROOT / p) == value for p, value in runtime["runtime_sha256_before"].items()))
    sync = read(G0 / "evidence/peer-git-sync.json")
    check("unrelated_original_logs", all(sha(ROOT / p["path"]) == p["sha256"] for p in sync["preexisting_untracked"]))
    index = ROOT / "docs/reports/milestones/README.md"
    index_text = index.read_text(encoding="utf-8")
    docs = []
    for name, bundle in (("M0.G", G0), ("M6.1", M6)):
        check(name + "_bundle_layout", {p.name for p in bundle.iterdir()} == {"README.md", "evidence", "superpowers"})
        check(name + "_planning_layout", {p.name for p in (bundle / "superpowers").iterdir()} == {"spec.md", "plan.md"})
        report = (bundle / "README.md").read_text(encoding="utf-8")
        rows = [line for line in index_text.splitlines() if line.startswith("| " + name + " |")]
        check(name + "_index_status", len(rows) == 1 and "| IN_PROGRESS |" in rows[0] and "- Status: IN_PROGRESS" in report)
        check(name + "_planning_links", all(t in report for t in ("superpowers/spec.md", "superpowers/plan.md", "evidence/workflow.md")))
        docs += [bundle / "README.md", bundle / "superpowers/spec.md", bundle / "superpowers/plan.md", bundle / "evidence/workflow.md"]
    check("formal_g0_pending", "- Gate result: NOT_RUN" in (G0 / "README.md").read_text(encoding="utf-8"))
    broken = []
    generated = {OUT / "windows-handoff.json", OUT / "windows-artifact-hashes.json"}
    for document in docs + [OUT / "windows-code-review.md"]:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", document.read_text(encoding="utf-8")):
            target = target.strip("<>").split("#", 1)[0]
            if not target or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target):
                continue
            path = (document.parent / unquote(target)).resolve()
            if not path.exists() and path not in generated:
                broken.append({"document": document.relative_to(ROOT).as_posix(), "target": target})
    check("current_document_links", not broken, broken)
    check("regression_red_green", "8 failed" in (OUT / "windows-red.log").read_text(encoding="utf-8") and "14 passed" in (OUT / "windows-green.log").read_text(encoding="utf-8"))
    reviewed = {
        "packages/common/resources.py": "13fcf66e3128dc37c1df8ed74bac2113667b3f211cbfccb6cfc6e6e8d7052cbe",
        "tests/unit/test_resource_measurements.py": "644e73406cab472b948910e2bcf87fbaafedc93bdee848cd8c5220e766bffa86",
        "pipelines/build_dense_sparse_index/dense.py": "3c4abf35526533f812e8b9f4c5dae4df3283034e53de52a918485988d7d22319",
        "pipelines/benchmark_retrieval/dense_hybrid_pilot.py": "ead11bbb23750b6ec3a60bbb72431c7baa7bdb0415a493e45b974469789d99ed",
    }
    check("reviewed_source_matches", all(source[p] == value for p, value in reviewed.items()))
    protected = subprocess.check_output(["git", "diff", "--name-only", "HEAD", "--", "data", "artifacts", "README.md", "AGENTS.md", "pyproject.toml", "infra", "configs", "scripts"], cwd=ROOT, text=True).splitlines()
    check("protected_paths_unchanged", not protected, protected)
    changed = subprocess.check_output(["git", "diff", "--name-only", "HEAD"], cwd=ROOT, text=True).splitlines()
    allowed = lambda p: p in source or p in {".gitattributes", "docs/reports/milestones/README.md"} or p.startswith(("docs/reports/milestones/M0.G/", "docs/reports/milestones/M6.1/"))
    check("authorized_change_scope", all(allowed(p) for p in changed), changed)
    for p in (OUT / "windows-run-checks.py", OUT / "windows-handoff.py", G0 / "evidence/merge-probe.py", G0 / "evidence/merge-package.py"):
        ast.parse(p.read_text(encoding="utf-8"), filename=p.name)
    check("current_runner_syntax", True)
    check("final_secret_scan", "Zero secret leaks detected" in (OUT / "windows-secrets-final.log").read_text(encoding="utf-8"))
    check("english_authored_prose", not any(re.search(r"kết quả|thực hiện|kiểm tra|báo cáo|hoàn thành|kế hoạch", p.read_text(encoding="utf-8"), re.I) for p in docs))
    receipt = {"checked_at": datetime.now(UTC).isoformat(), "status": "PASS" if all(c["passed"] for c in checks) else "FAIL",
               "formal_gate": "NOT_RUN", "scientific_m6_1": "IN_PROGRESS", "source_sha256": source, "checks": checks}
    (OUT / "windows-handoff.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    files = sorted(p for folder in (M6, G0) for p in folder.rglob("*") if p.is_file() and p.name != "windows-artifact-hashes.json")
    files += [index, ROOT / ".gitattributes"] + [ROOT / p for p in source]
    manifest = {"algorithm": "SHA256", "files": {p.relative_to(ROOT).as_posix(): sha(p) for p in files}}
    (OUT / "windows-artifact-hashes.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    inventory_ok = all(sha(ROOT / p) == value for p, value in manifest["files"].items())
    print(json.dumps({"status": receipt["status"], "checks": len(checks), "failed": [c for c in checks if not c["passed"]], "inventory_files": len(files), "inventory_verified": inventory_ok}))
    return int(receipt["status"] != "PASS" or not inventory_ok)


if __name__ == "__main__":
    raise SystemExit(main())
