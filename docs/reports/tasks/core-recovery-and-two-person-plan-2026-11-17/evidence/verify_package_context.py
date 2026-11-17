"""Reproduce root and Docker COPY-only wheel builds without Docker or image pulls."""
from __future__ import annotations

import argparse
from email import message_from_bytes
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tempfile
from zipfile import ZipFile


def build_wheel(source: Path, output: Path) -> tuple[bool, list[str]]:
    command = [sys.executable, "-m", "build", "--wheel", "--no-isolation", "--outdir", str(output)]
    print(f"cwd={source}; command={command}", flush=True)
    result = subprocess.run(command, cwd=source, text=True, capture_output=True)
    print(result.stdout, flush=True)
    print(result.stderr, flush=True)
    print(f"wheel_build_exit={result.returncode}", flush=True)
    if result.returncode:
        return False, []
    wheel = next(output.glob("*.whl"))
    with ZipFile(wheel) as archive:
        metadata = next(name for name in archive.namelist() if name.endswith(".dist-info/METADATA"))
        requirements = message_from_bytes(archive.read(metadata)).get_all("Requires-Dist", [])
        members = archive.namelist()
    print(f"wheel={wheel.name}; requirements={requirements}", flush=True)
    for module in ["apps/api/app/main.py", "pipelines/benchmark_retrieval/__main__.py", "packages/retrieval/service.py"]:
        assert module in members, f"wheel omitted {module}"
    return True, requirements


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--expect-broken", action="store_true")
    args = parser.parse_args()
    repo = Path.cwd()
    with tempfile.TemporaryDirectory(prefix="tiktok-package-check-") as tmp:
        scratch = Path(tmp)
        root_ok, requirements = build_wheel(repo, scratch / "root-dist")
        assert root_ok, "root wheel did not build"
        core_gradio = any(req.lower().startswith("gradio") and "extra ==" not in req for req in requirements)
        print(f"gradio_in_default_dependencies={core_gradio}", flush=True)
        context = scratch / "docker-copy-context"
        context.mkdir()
        # The Dockerfile currently uses simple COPY sources; deliberately fail on
        # an unsupported future format instead of silently approximating it.
        for line in (repo / "infra/docker/Dockerfile.api").read_text(encoding="utf-8").splitlines():
            if not line.startswith("COPY "):
                continue
            parts = shlex.split(line[5:])
            assert not parts[0].startswith("--") and not parts[0].startswith("[")
            destination = context / parts[-1]
            for item in parts[:-1]:
                source = repo / item
                target = destination / source.name if len(parts[:-1]) > 1 or parts[-1] in ("./", ".") else destination
                print(f"COPY {source.relative_to(repo)} -> {target.relative_to(context)}", flush=True)
                if source.is_dir():
                    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, target)
        context_ok, _ = build_wheel(context, scratch / "context-dist")
        print(f"docker_copy_context_build={context_ok}; docker_engine_used=False; image_pulls=0", flush=True)
        if args.expect_broken:
            assert not core_gradio, "old dependency problem did not reproduce"
            assert not context_ok, "old COPY omission did not reproduce"
            print("EXPECTED RED: root builds; core Gradio missing; Docker COPY context cannot build")
        else:
            assert core_gradio, "base install does not require Gradio"
            assert context_ok, "Docker COPY context cannot build"
            print("PASS: root wheel, default Gradio dependency, Docker COPY context wheel")


if __name__ == "__main__":
    main()
