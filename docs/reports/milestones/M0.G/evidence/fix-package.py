"""Build the Docker COPY source context and verify a clean offline wheel install."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent


def main() -> int:
    env = dict(os.environ)
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        env[key] = ""
    env.update(GRADIO_ANALYTICS_ENABLED="False", PYTHONUTF8="1", PYTHONDONTWRITEBYTECODE="1")
    uv = shutil.which("uv") or "C:/Users/lanph/.local/bin/uv.exe"
    receipt = {"started_at": datetime.now(UTC).isoformat(), "steps": [], "clean_install": False,
               "actual_docker_container_run": False, "provider_calls": 0}

    def run(name: str, command: list[str], cwd: Path, timeout: int = 180) -> int:
        start = time.perf_counter()
        log = OUT / f"fix-{name}.log"
        with log.open("w", encoding="utf-8") as stream:
            try:
                proc = subprocess.run(command, cwd=cwd, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=timeout)
                code = proc.returncode
            except subprocess.TimeoutExpired:
                stream.write(f"\nTIMEOUT after {timeout} seconds\n")
                code = 124
            except FileNotFoundError:
                stream.write("Executable not available\n")
                code = 127
        receipt["steps"].append({"name": name, "command": command, "exit_code": code,
                                  "seconds": round(time.perf_counter() - start, 3), "log": log.name})
        print(f"{name}: exit={code}", flush=True)
        (OUT / "fix-package-results.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
        return code

    receipt["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in ['packages/common/settings/__init__.py', 'packages/llm/clients/gemini.py', 'apps/api/app/routers/health.py', 'packages/retrieval/sparse/bm25.py', 'tests/unit/test_llm_call_budget.py']}
    with tempfile.TemporaryDirectory(prefix="g0-fix-package-") as scratch:
        base = Path(scratch)
        context = base / "source"
        context.mkdir()
        for name in ("pyproject.toml", "README.md"):
            shutil.copy2(ROOT / name, context / name)
        for name in ("apps", "packages", "pipelines", "configs"):
            shutil.copytree(ROOT / name, context / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        wheel_dir = base / "wheels"
        code = run("wheel-build", [uv, "build", "--offline", "--wheel", "--out-dir", str(wheel_dir), str(context)], base)
        if code == 0:
            wheel = next(wheel_dir.glob("*.whl"))
            with zipfile.ZipFile(wheel) as archive:
                names = archive.namelist()
            modules = {name: any(p.startswith(name + "/") for p in names) for name in ("apps", "packages", "pipelines")}
            receipt["wheel"] = {"name": wheel.name, "bytes": wheel.stat().st_size,
                                "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest(), "modules_present": modules}
            assert all(modules.values()), modules
            virtual = base / "installed"
            code = run("clean-venv", [uv, "venv", "--python", sys.executable, str(virtual)], base)
            vpython = virtual / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
            if code == 0:
                code = run("wheel-install", [uv, "pip", "install", "--offline", "--python", str(vpython), str(wheel)], base)
            if code == 0:
                code = run("installed-pip-check", [uv, "pip", "check", "--python", str(vpython)], base)
            if code == 0:
                payload = (
                    "import json, pathlib, sys; from fastapi.testclient import TestClient; "
                    "import apps.api.app.main as api; import packages.common.settings as settings; import pipelines; "
                    "root=pathlib.Path(sys.argv[1]); prefix=pathlib.Path(sys.prefix); "
                    "locations=[api.__file__,settings.__file__,pipelines.__file__]; "
                    "assert all(pathlib.Path(p).is_relative_to(prefix) for p in locations), locations; "
                    "app=api.create_app(settings=settings.AppSettings(gemini_api_key='', "
                    "corpus_dir=root/'data/corpus/20261117_recovered_v1',bm25_index_dir=root/'artifacts/indexes/bm25-v2')); "
                    "client=TestClient(app); live=client.get('/health/live'); demo=client.get('/demo/'); "
                    "assert live.status_code==200 and demo.status_code==200; "
                    "print(json.dumps({'installed_modules':locations,'health_live':live.status_code,'demo':demo.status_code}))"
                )
                code = run("installed-asgi", [str(vpython), "-c", payload, str(ROOT)], base)
                receipt["clean_install"] = code == 0
        receipt["package_exit_code"] = code
    docker = shutil.which("docker") or "docker"
    run("docker-version", [docker, "--version"], ROOT, timeout=20)
    run("docker-info", [docker, "info", "--format", "{{.ServerVersion}}"], ROOT, timeout=20)
    receipt["completed_at"] = datetime.now(UTC).isoformat()
    (OUT / "fix-package-results.json").write_text(json.dumps(receipt, indent=2), encoding="utf-8")
    return int(receipt["package_exit_code"] != 0)


if __name__ == "__main__":
    raise SystemExit(main())
