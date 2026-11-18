"""Validate this read-only synchronization report and its recorded evidence."""

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
REVISION = "c3348e93d66ad4eeba133c1d05752d26da18d774"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8-sig"))


def git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True, encoding="utf-8").strip()


def main() -> int:
    checks = {}
    checks["layout"] = set(p.name for p in TASK.iterdir()) == {"README.md", "evidence", "superpowers"}
    checks["planning"] = set(p.name for p in (TASK / "superpowers").iterdir()) == {"spec.md", "plan.md"}
    checks["current_revision"] = git("rev-parse", "HEAD") == git("rev-parse", "origin/main") == REVISION
    checks["source_mutation_scope"] = set(git("diff", "--name-only").splitlines()) <= {"docs/reports/tasks/README.md"}
    old_logs = ["git-push-data-first-http408.log", "git-push-data.log", "git-push-retry.log"]
    checks["preexisting_logs_retained"] = all((TASK.parent / "full-data-publication-2026-11-17/evidence" / n).is_file() for n in old_logs)
    checks["old_worktree_retained"] = Path("C:/Users/lanph/.codex/worktrees/bf1f/TikTok_AI_Engine_/.git").is_file()
    report = (TASK / "README.md").read_text(encoding="utf-8")
    index = (TASK.parent / "README.md").read_text(encoding="utf-8")
    row = [line for line in index.splitlines() if line.startswith("| team-progress-sync-2026-11-18 |")]
    checks["current_status_index"] = "- Status: COMPLETE\n" in report and len(row) == 1 and "| COMPLETE |" in row[0]
    required = ["git-sync.json", "nguyen-progress.md", "nguyen-probes.json", "data-progress.md", "data-verification.json",
                "pytest-current.log", "pytest-result.json", "mypy-current.log", "mypy-result.json", "workflow.md"]
    checks["required_evidence"] = all((EVIDENCE / p).is_file() for p in required)

    data = read_json("data-verification.json")
    checks["data_record_consistency"] = (
        data["status"] == "PASS" and data["head"] == data["head_at_end"] == REVISION
        and not data["failure_counts"] and data["historical"]["verified_files"] == 37840
        and data["publication"]["verified_local_files"] == 37849
        and data["gold"]["counts"]["videos"] == 70996
        and all(data["bm25"]["checks"].values())
    )
    checks["current_check_exit_codes"] = all(read_json(n)["exit_code"] == 0 and read_json(n)["head"] == REVISION
                                            for n in ["pytest-result.json", "mypy-result.json"])
    checks["pytest_count"] = "63 passed" in (EVIDENCE / "pytest-current.log").read_text(encoding="utf-8")
    link_errors, checked = [], 0
    for md in [*TASK.rglob("*.md"), TASK.parent / "README.md"]:
        for raw in re.findall(r"\[[^\]]*\]\(([^)]+)\)", md.read_text(encoding="utf-8-sig")):
            if re.match(r"[a-zA-Z]+://", raw) or raw.startswith("mailto:"):
                continue
            target = unquote(raw.split("#", 1)[0]).strip("<>")
            if target:
                checked += 1
                if not (md.parent / target).resolve().exists():
                    link_errors.append({"source": md.relative_to(ROOT).as_posix(), "target": raw})
    checks["local_links"] = not link_errors
    secret = subprocess.run([sys.executable, "scripts/check_secrets.py"], cwd=ROOT, capture_output=True, text=True)
    (EVIDENCE / "secrets-final.log").write_text(secret.stdout + secret.stderr, encoding="utf-8")
    checks["secret_scan"] = secret.returncode == 0
    diff = subprocess.run(["git", "diff", "--check"], cwd=ROOT, capture_output=True, text=True)
    checks["diff_whitespace"] = diff.returncode == 0
    excluded = {"artifact-hashes.json", "handoff-verification.json"}
    files = sorted(p for p in TASK.rglob("*") if p.is_file() and p.name not in excluded)
    hashes = {"algorithm": "SHA256", "excluded_to_avoid_cycles": sorted(excluded),
              "files": [{"path": p.relative_to(TASK).as_posix(), "bytes": p.stat().st_size, "sha256": sha(p)} for p in files]}
    manifest = EVIDENCE / "artifact-hashes.json"
    manifest.write_text(json.dumps(hashes, indent=2) + "\n", encoding="utf-8")
    checks["artifact_hashes"] = all(sha(TASK / x["path"]) == x["sha256"] for x in hashes["files"])
    result = {"verified_at_utc": datetime.now(timezone.utc).isoformat(), "revision": REVISION,
              "checks": checks, "pass": all(checks.values()), "local_links_checked": checked,
              "link_errors": link_errors, "artifact_files": len(files), "hash_manifest_sha256": sha(manifest),
              "secret_scan": {"exit_code": secret.returncode, "output": secret.stdout.strip()},
              "diff_check": {"exit_code": diff.returncode, "output": (diff.stdout + diff.stderr).strip()},
              "scope": "Report handoff only. Product/milestone acceptance is not granted; runtime redaction findings remain open."}
    (EVIDENCE / "handoff-verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
