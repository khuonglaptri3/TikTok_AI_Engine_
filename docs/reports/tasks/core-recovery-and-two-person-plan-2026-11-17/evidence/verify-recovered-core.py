"""Measure the actual recovered CPU core without external generation calls."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
import json
import os
import platform
import sys
import time
from pathlib import Path

EVIDENCE = Path(__file__).resolve().parent
ROOT = EVIDENCE.parents[4]
# This standalone evidence script must measure checkout modules, not an older
# installed wheel whose data paths are relative to site-packages.
sys.path.insert(0, str(ROOT))

import httpx
import pandas as pd

from apps.api.app.main import create_app
from packages.analytics import load_verified_corpus
from packages.common.settings import AppSettings
from packages.retrieval.sparse.bm25 import BM25Index

def sha(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(4 * 1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main() -> None:
    assert Path(inspect.getfile(create_app)).resolve().is_relative_to(ROOT)
    assert Path(inspect.getfile(load_verified_corpus)).resolve().is_relative_to(ROOT)
    settings = AppSettings(gemini_api_key="")
    started = time.perf_counter()
    manifest, creators, videos = load_verified_corpus(settings.corpus_dir)
    tables = []
    for item in manifest.files:
        path = settings.corpus_dir / item.filename
        frame = pd.read_parquet(path)
        assert len(frame) == item.rows and len(frame.columns) == item.columns
        assert path.stat().st_size == item.size_bytes
        tables.append({"filename": item.filename, "rows": len(frame), "columns": len(frame.columns),
                       "sha256": sha(path), "size_bytes": path.stat().st_size})
    assert len(videos.columns) == 49
    assert videos.video_id.is_unique and creators.author_id.is_unique
    assert set(videos.author_id) <= set(creators.author_id)
    index = BM25Index.load(settings.bm25_index_dir)
    receipt = json.loads((settings.bm25_index_dir / "bm25-receipt.json").read_text(encoding="utf-8"))
    assert receipt["corpus_snapshot_id"] == manifest.snapshot_id
    assert len(index.video_ids) == receipt["document_count"]
    eligible = set(videos.loc[videos.has_transcript & videos.rag_document.str.len().gt(0), "video_id"])
    assert len(index.video_ids) == len(set(index.video_ids)) and set(index.video_ids) == eligible
    initialization = time.perf_counter()
    app = create_app(settings=settings, mount_demo=True)
    app_initialization_ms = (time.perf_counter() - initialization) * 1000
    observations = []

    async def probe(method: str, url: str, payload: dict | None = None, expected: int = 200) -> dict:
        before = time.perf_counter()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://local") as client:
            response = await client.request(method, url, json=payload, follow_redirects=True)
        elapsed = (time.perf_counter() - before) * 1000
        assert response.status_code == expected, (url, response.status_code, response.text[:500])
        body = response.json() if "application/json" in response.headers.get("content-type", "") else {}
        observations.append({"method": method, "path": url, "status": response.status_code,
                             "wall_ms": round(elapsed, 3), "timings_ms": body.get("timings_ms", {}),
                             "error_code": body.get("code")})
        return body

    async def run() -> dict:
        ready = await probe("GET", "/health/ready")
        await probe("GET", "/demo/")
        niche = await probe("POST", "/api/v1/analytics/niche-benchmark", {"video_format": "Review quán ăn", "city_norm": "hồ chí minh"})
        search = await probe("POST", "/api/v1/retrieval/search", {"query": "bánh mì thịt nướng Sài Gòn", "top_k": 4, "mode": "hybrid_rrf", "rerank": True})
        draft = await probe("POST", "/api/v1/script/generate", {"brief": "Review quán ốc sinh viên bình dân 35k ăn đêm ở Quận 4 Sài Gòn", "target_duration_sec": 45, "top_k_evidence": 4, "generation_mode": "offline_grounded"})
        assert draft["guardrail"]["passed"] is True
        assert draft["grounding_verified"] is False and draft["draft_status"] == "creative_draft"
        source_ids = {card["citation"]["video_id"] for card in draft["evidence_cards"]}
        assert source_ids and source_ids <= set(videos.video_id)
        assert all(beat["cited_video_ids"] and set(beat["cited_video_ids"]) <= source_ids for beat in draft["beats"])
        assert abs(draft["guardrail"]["duration_delta_sec"]) <= 2.25
        await probe("POST", "/api/v1/script/generate", {"brief": "Review phở bò Hà Nội", "generation_mode": "gemini_free"}, expected=503)
        await probe("POST", "/api/v1/script/generate", {"brief": "Phân tích đầu tư chứng khoán bitcoin", "generation_mode": "offline_grounded"}, expected=422)
        return {"readiness": ready, "niche_sample": niche, "search": search, "offline_draft": draft}

    outputs = asyncio.run(run())
    (EVIDENCE / "recovered-api-outputs.json").write_text(json.dumps(outputs, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result = {
        "status": "PASS", "snapshot_id": manifest.snapshot_id, "tables": tables,
        "total_creators": len(creators), "total_videos": len(videos),
        "transcribed_videos": int(videos.has_transcript.sum()), "poi_tagged_videos": int(videos.poi_name.notna().sum()),
        "index": receipt, "manifest_sha256": sha(settings.corpus_dir / "manifest.json"),
        "input_manifest_sha256": sha(EVIDENCE / "restore-input-manifest.json"),
        "source_revision": "f142e5656a220f94f8024de168b0832754b3bd9e",
        "code_sha256": {name: sha(ROOT / name) for name in ["pipelines/build_gold_corpus/builder.py", "packages/common/snapshots.py", "pipelines/build_dense_sparse_index/__main__.py", "packages/retrieval/sparse/bm25.py"]},
        "environment": {"platform": platform.platform(), "processor": platform.processor(), "logical_cpu_count": os.cpu_count(), "python": platform.python_version(), "concurrency": 1},
        "module_files": {"api": Path(inspect.getfile(create_app)).relative_to(ROOT).as_posix(),
                         "corpus_loader": Path(inspect.getfile(load_verified_corpus)).relative_to(ROOT).as_posix()},
        "app_initialization_ms": round(app_initialization_ms, 3), "requests": observations,
        "elapsed_seconds": round(time.perf_counter() - started, 3),
        "provider_calls": 0, "provider_spend_usd": 0,
        "limits": "One local ASGI observation per endpoint; app initialization excludes module imports. No p95 service gate, browser interaction, live provider, network crawl, dense quality, human factuality or Docker/hosting acceptance is inferred.",
    }
    (EVIDENCE / "recovered-core-verification.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in ["status", "snapshot_id", "total_creators", "total_videos", "transcribed_videos", "poi_tagged_videos", "app_initialization_ms", "elapsed_seconds", "provider_calls"]}))


if __name__ == "__main__":
    main()
