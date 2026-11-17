#!/usr/bin/env python3
"""Cross-platform developer workflow runner (SenticRAG style)."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _run(cmd: list[str]) -> int:
    print(f"+ {' '.join(cmd)}")
    return subprocess.call(cmd, cwd=ROOT)


def main() -> int:
    parser = argparse.ArgumentParser(description="ViralFoodRAG developer CLI")
    parser.add_argument(
        "command",
        choices=[
            "check-secrets",
            "build-corpus",
            "build-index",
            "benchmark",
            "crawl-4m-demo",
            "ingest-4m",
            "lint",
            "typecheck",
            "test",
            "run-api",
            "run-demo",
        ],
    )
    args = parser.parse_args()
    py = sys.executable

    if args.command == "check-secrets":
        return _run([py, "scripts/check_secrets.py"])
    if args.command == "build-corpus":
        return _run([py, "-m", "pipelines.build_gold_corpus", "--output", "data/corpus/20261117_recovered_v1"])
    if args.command == "build-index":
        return _run(
            [
                py,
                "-m",
                "pipelines.build_dense_sparse_index",
                "--corpus",
                "data/corpus/20261117_recovered_v1",
                "--output",
                "artifacts/indexes/bm25-v2",
            ]
        )
    if args.command == "benchmark":
        return _run(
            [
                py,
                "-m",
                "pipelines.benchmark_retrieval",
                "--corpus",
                "data/corpus/20261117_recovered_v1",
                "--index",
                "artifacts/indexes/bm25-v2",
                "--output",
                "artifacts/benchmarks/retrieval_v2.json",
            ]
        )
    if args.command == "crawl-4m-demo":
        return _run([py, "-m", "pipelines.crawl_incremental", "--seed-demo-batch"])
    if args.command == "ingest-4m":
        return _run(
            [
                py,
                "-m",
                "pipelines.ingest_incremental_to_gold",
                "--output-corpus",
                "data/corpus/20261117_incremental_v1",
            ]
        )
    if args.command == "lint":
        return _run([py, "scripts/check_secrets.py"])
    if args.command == "typecheck":
        return _run([py, "-m", "mypy", "packages", "apps", "pipelines"])
    if args.command == "test":
        return _run([py, "-m", "pytest"])
    if args.command == "run-api":
        return _run(
            [
                py,
                "-m",
                "uvicorn",
                "apps.api.app.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ]
        )
    if args.command == "run-demo":
        return _run(
            [
                py,
                "-m",
                "uvicorn",
                "apps.demo.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                "8000",
            ]
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
