"""Reproducible Gate M0.G (G0) verification probe over recovered corpus and ASGI app."""

from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.app.main import create_app
from packages.analytics import load_verified_corpus
from packages.common.settings import AppSettings


def _cmd(args: list[str]) -> dict[str, str | int]:
    proc = subprocess.run(args, capture_output=True, text=True, check=False)
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> None:
    repo_root = Path(__file__).resolve().parents[5]
    head_sha = _cmd(["git", "rev-parse", "HEAD"])["stdout"]

    # 1. Verify active and v2 Gold snapshots
    snap_v1_dir = repo_root / "data/corpus/20261117_recovered_v1"
    m_v1, c_v1, v_v1 = load_verified_corpus(snap_v1_dir)
    snap_v2_dir = repo_root / "data/corpus/20261118_taxonomy_fix_v1"
    m_v2, c_v2, v_v2 = load_verified_corpus(snap_v2_dir)

    # 2. Boot single-process FastAPI + ASGI Gradio app with zero provider calls
    settings = AppSettings(
        gemini_api_key="",
        corpus_dir=snap_v1_dir,
        bm25_index_dir=repo_root / "artifacts/indexes/bm25-v2",
    )
    app = create_app(settings=settings, mount_demo=True)
    with TestClient(app) as client:
        live = client.get("/health/live")
        ready = client.get("/health/ready")
        demo = client.get("/demo/")
        bench = client.post(
            "/api/v1/analytics/niche-benchmark",
            json={"video_format": "Review quán ăn", "city_norm": "hồ chí minh"},
        )
        search = client.post(
            "/api/v1/retrieval/search",
            json={"query": "bánh mì thịt nướng Sài Gòn", "mode": "bm25", "top_k": 5},
        )
        draft = client.post(
            "/api/v1/script/generate",
            json={
                "brief": "Review quán ốc bình dân Quận 4 Sài Gòn khoảng 35k",
                "target_duration_sec": 45,
                "generation_mode": "offline_grounded",
            },
        )
        ood = client.post(
            "/api/v1/script/generate",
            json={
                "brief": "Phân tích đầu tư Bitcoin và chứng khoán hôm nay",
                "target_duration_sec": 30,
                "generation_mode": "offline_grounded",
            },
        )

    docker_cli = _cmd(["docker", "--version"])
    docker_info = _cmd(["docker", "info", "--format", "{{.ServerVersion}}"])

    receipt = {
        "gate_id": "M0.G",
        "checked_at_utc": datetime.now(UTC).isoformat(),
        "git_head": head_sha,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "executable": sys.executable,
        },
        "snapshots": {
            "20261117_recovered_v1": {
                "snapshot_id": m_v1.snapshot_id,
                "creators": len(c_v1),
                "videos": len(v_v1),
            },
            "20261118_taxonomy_fix_v1": {
                "snapshot_id": m_v2.snapshot_id,
                "creators": len(c_v2),
                "videos": len(v_v2),
            },
        },
        "docker": {
            "cli_status": docker_cli,
            "daemon_status": docker_info,
        },
        "asgi_smoke": {
            "health_live_status": live.status_code,
            "health_ready_status": ready.status_code,
            "health_ready_body": ready.json(),
            "demo_html_status": demo.status_code,
            "demo_html_bytes": len(demo.text.encode("utf-8")),
            "niche_benchmark_status": bench.status_code,
            "niche_benchmark_matched": bench.json().get("matched_videos"),
            "retrieval_search_status": search.status_code,
            "retrieval_search_items": len(search.json().get("items", [])),
            "script_offline_status": draft.status_code,
            "script_offline_model": draft.json().get("model_used"),
            "script_offline_beats": len(draft.json().get("beats", [])),
            "script_ood_status": ood.status_code,
            "script_ood_code": ood.json().get("code"),
        },
    }

    out_path = Path(__file__).resolve().parent / "g0_verification_receipt.json"
    out_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
