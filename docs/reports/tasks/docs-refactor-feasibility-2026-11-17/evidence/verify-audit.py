"""Validate this audit's deliverables; does not alter source/data or milestone status."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import unquote

EVIDENCE = Path(__file__).resolve().parent
TASK = EVIDENCE.parent
ROOT = TASK.parents[3]
AUTHORIZED = {"docs/reports/milestones/README.md"}


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path: Path) -> str:
    data = path.read_bytes()
    return data.decode("utf-16") if data.startswith((b"\xff\xfe", b"\xfe\xff")) else data.decode("utf-8-sig")


def slug(title: str) -> str:
    return re.sub(r"[^\w\- ]", "", title.strip().lower()).replace(" ", "-")


def links(paths: list[Path]) -> dict:
    checked, errors = 0, []
    for path in paths:
        for target in re.findall(r"\[[^\]]*\]\(([^)]+)\)", read(path)):
            target = target.strip().strip("<>")
            if re.match(r"[a-zA-Z]+://", target) or target.startswith("mailto:"):
                continue
            target_path, _, fragment = unquote(target).partition("#")
            destination = (path.parent / target_path).resolve() if target_path else path
            checked += 1
            if not destination.exists():
                errors.append({"source": path.relative_to(ROOT).as_posix(), "target": target, "issue": "missing file"})
            elif fragment:
                content = read(destination)
                if re.fullmatch(r"L\d+", fragment):
                    if int(fragment[1:]) > len(content.splitlines()):
                        errors.append({"source": path.relative_to(ROOT).as_posix(), "target": target, "issue": "line outside source"})
                elif destination.suffix.lower() == ".md":
                    anchors = {slug(m.group(1)) for m in re.finditer(r"^#{1,6}\s+(.+)$", content, flags=re.M)}
                    if fragment not in anchors:
                        errors.append({"source": path.relative_to(ROOT).as_posix(), "target": target, "issue": "heading anchor missing"})
    return {"checked": checked, "errors": errors}


def main() -> int:
    checks: dict = {}
    expected_top = {"README.md", "evidence", "superpowers"}
    checks["bundle_layout"] = {"actual": sorted(p.name for p in TASK.iterdir()), "expected": sorted(expected_top)}
    checks["bundle_layout"]["pass"] = set(checks["bundle_layout"]["actual"]) == expected_top
    checks["planning_layout"] = {"actual": sorted(p.name for p in (TASK / "superpowers").iterdir())}
    checks["planning_layout"]["pass"] = checks["planning_layout"]["actual"] == ["plan.md", "spec.md"]

    inventory = json.loads(read(EVIDENCE / "document-inventory.json"))
    unchanged, authorized_changes, unexpected = [], [], []
    for item in inventory["files"]:
        path = ROOT / item["path"]
        actual = sha(path) if path.is_file() else None
        if actual == item["sha256"]:
            unchanged.append(item["path"])
        elif item["path"] in AUTHORIZED:
            authorized_changes.append({"path": item["path"], "before": item["sha256"], "after": actual})
        else:
            unexpected.append(item["path"])
    checks["original_document_integrity"] = {"pass": not unexpected, "unchanged": unchanged,
                                               "authorized_navigation_changes": authorized_changes, "unexpected": unexpected}

    owned_md = list(TASK.rglob("*.md")) + [TASK.parent / "README.md"]
    checks["audit_local_links"] = links(owned_md)
    checks["audit_local_links"]["pass"] = not checks["audit_local_links"]["errors"]
    checks["original_document_local_links"] = links([ROOT / x["path"] for x in inventory["files"]])

    task_index = read(TASK.parent / "README.md")
    report = read(TASK / "README.md")
    checks["navigation_and_status"] = {
        "pass": "- Status: COMPLETE\n" in report and task_index.count("| docs-refactor-feasibility-2026-11-17 |") == 1
                and "| COMPLETE |" in task_index and "../tasks/README.md" in read(ROOT / "docs/reports/milestones/README.md"),
        "scope": "Independent task status only; existing milestone status is unchanged.",
    }

    secrets = subprocess.run([sys.executable, "scripts/check_secrets.py"], cwd=ROOT, capture_output=True, text=True)
    checks["secret_scan"] = {"pass": secrets.returncode == 0, "exit_code": secrets.returncode,
                              "stdout": secrets.stdout.strip(), "stderr": secrets.stderr.strip()}
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    checks["git_diff_check"] = {"pass": diff.returncode == 0, "exit_code": diff.returncode,
                                 "output": (diff.stdout + diff.stderr).strip()}
    tracked = subprocess.check_output(["git", "diff", "--name-only"], cwd=ROOT, text=True).splitlines()
    checks["tracked_mutation_scope"] = {"pass": set(tracked) <= AUTHORIZED, "changed_paths": tracked}
    checks["repository_head_unchanged"] = {
        "pass": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip() == inventory["repository_commit"],
        "commit": inventory["repository_commit"],
    }

    required = ["docs-review.md", "refactor-review.md", "upstream-data-review.md", "upstream-metadata.json",
                "external-and-runtime-review.md", "pytest-full.log", "mypy.log", "runtime-probes.json", "runtime-probes.py",
                "base-install-import.log", "docker-context-build.log", "report-review.md", "workflow.md"]
    checks["required_evidence"] = {"pass": all((EVIDENCE / p).is_file() for p in required),
                                     "missing": [p for p in required if not (EVIDENCE / p).is_file()]}
    probes = json.loads(read(EVIDENCE / "runtime-probes.json"))
    checks["controlled_findings_consistency"] = {
        "pass": probes["guardrails"]["empty_script"]["passed"] is True
                and probes["incremental"]["after_A_then_replay_A"]["fact_comments.parquet"] == 0,
        "scope": "Verifies that the report refers to the recorded defect reproductions; not a passing product gate.",
    }

    excluded = {"artifact-hashes.json", "verification.json"}
    hash_files = sorted(p for p in TASK.rglob("*") if p.is_file() and p.name not in excluded)
    hash_payload = {"algorithm": "SHA256", "excluded_to_avoid_cycles": sorted(excluded),
                    "files": [{"path": p.relative_to(TASK).as_posix(), "sha256": sha(p), "bytes": p.stat().st_size} for p in hash_files]}
    hash_path = EVIDENCE / "artifact-hashes.json"
    hash_path.write_text(json.dumps(hash_payload, indent=2) + "\n", encoding="utf-8")
    checks["audit_artifact_hashes"] = {"pass": all(sha(TASK / x["path"]) == x["sha256"] for x in hash_payload["files"]),
                                        "files": len(hash_files), "manifest_sha256": sha(hash_path)}
    result = {"verified_at": datetime.now(timezone.utc).isoformat(), "checks": checks,
              "runtime_summary": {"existing_pytest": "15 passed, 5 failed (missing historical inputs/Gold payloads)",
                                  "mypy": "PASS: 74 source files", "product_defects": "reproduced; not fixed",
                                  "live_provider_crawl_deployment": "NOT_RUN"},
              "manual_review_scope": "English authored prose and source/evidence qualifications reviewed; retained original raw logs may contain Vietnamese."}
    result["audit_handoff_pass"] = all(c["pass"] for c in checks.values() if "pass" in c)
    (EVIDENCE / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["audit_handoff_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
