"""Run independent G0 checks and retain complete outputs without provider keys."""
from __future__ import annotations

import hashlib
import importlib.metadata as md
import json
import os
import platform
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def main() -> int:
    env = dict(os.environ)
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        env[key] = ""
    env.update(GRADIO_ANALYTICS_ENABLED="False", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    versions = {}
    for name in ("fastapi", "gradio", "pydantic", "numpy", "pandas", "pyarrow", "scipy", "google-genai", "pytest", "mypy", "ruff"):
        try:
            versions[name] = md.version(name)
        except md.PackageNotFoundError:
            versions[name] = None
    receipt = {
        "started_at": datetime.now(UTC).isoformat(),
        "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "python": sys.version, "executable": sys.executable,
        "platform": platform.platform(), "cpu_count": os.cpu_count(),
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ["packages/common/settings/__init__.py", "packages/llm/clients/gemini.py", "apps/api/app/routers/health.py", "packages/retrieval/sparse/bm25.py", "tests/unit/test_llm_call_budget.py"]},
        "versions": versions, "provider_keys_blanked": True, "checks": [],
    }
    commands = [
        ("secrets", [sys.executable, "scripts/check_secrets.py"]),
        ("pip-check", [sys.executable, "-m", "pip", "check"]),
        ("mypy", [sys.executable, "-m", "mypy", "packages", "apps", "pipelines"]),
        ("ruff", [sys.executable, "-m", "ruff", "check", "packages", "apps", "tests/contract", "tests/smoke", "tests/unit/test_llm_call_budget.py"]),
        ("contract-smoke", [sys.executable, "-m", "pytest", "tests/contract", "tests/smoke", "-v"]),
        ("pytest-full", [sys.executable, "-m", "pytest", "-v"]),
    ]
    for name, command in commands:
        start = time.perf_counter()
        log = OUT / f"publish-{name}.log"
        with log.open("w", encoding="utf-8") as stream:
            try:
                proc = subprocess.run(command, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=600)
                code = proc.returncode
            except subprocess.TimeoutExpired:
                code = 124
                stream.write("\nTIMEOUT after 600 seconds\n")
        item = {"name": name, "command": command, "exit_code": code,
                "seconds": round(time.perf_counter() - start, 3), "log": log.name,
                "sha256": hashlib.sha256(log.read_bytes()).hexdigest()}
        receipt["checks"].append(item)
        (OUT / "publish-check-results.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(item), flush=True)
    receipt["completed_at"] = datetime.now(UTC).isoformat()
    (OUT / "publish-check-results.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return int(any(c["exit_code"] != 0 for c in receipt["checks"]))


if __name__ == "__main__":
    raise SystemExit(main())
