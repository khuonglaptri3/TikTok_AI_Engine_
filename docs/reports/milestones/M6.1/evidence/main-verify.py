"""Run full tests on the actual merged main revision, preserving exact evidence."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def main() -> int:
    merged = json.loads((ROOT / "docs/reports/milestones/M0.G/evidence/merge-github-receipt.json").read_text(encoding="utf-8"))
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    if not merged["merged"]:
        raise SystemExit("PR3 is not confirmed merged.")
    subprocess.run(["git", "merge-base", "--is-ancestor", merged["merge_commit_sha"], head], cwd=ROOT, check=True)
    source = merged["source_sha256"]
    source_ok = all(hashlib.sha256(subprocess.check_output(["git", "show", "HEAD:" + p], cwd=ROOT)).hexdigest() == value for p, value in source.items())
    if not source_ok:
        raise SystemExit("Merged main source differs from verified source; investigate before validation.")
    env = dict(os.environ)
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        env[key] = ""
    env.update(PYTHONUTF8="1", GRADIO_ANALYTICS_ENABLED="False", PYTHONDONTWRITEBYTECODE="1")
    command = [sys.executable, "-m", "pytest", "-v"]
    start = time.perf_counter()
    log = OUT / "main-pytest.log"
    with log.open("w", encoding="utf-8") as stream:
        proc = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
    receipt = {
        "checked_at": datetime.now(UTC).isoformat(), "head": head,
        "merged_pr": 3, "source_merge_commit": merged["merge_commit_sha"],
        "source_matches_premerge_verification": source_ok, "source_sha256": source,
        "pytest_command": command, "pytest_exit": proc.returncode,
        "seconds": round(time.perf_counter() - start, 3), "log": log.name,
        "log_sha256": hashlib.sha256(log.read_bytes()).hexdigest(),
        "provider_keys_blanked": True, "formal_g0": "NOT_RUN", "scientific_m6_1": "IN_PROGRESS",
    }
    (OUT / "main-verification.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    print(json.dumps(receipt), flush=True)
    print("\n".join(log.read_text(encoding="utf-8").splitlines()[-3:]), flush=True)
    return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
