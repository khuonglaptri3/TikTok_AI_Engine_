from __future__ import annotations

import unicodedata
from pathlib import Path

import pandas as pd
import pytest

from apps.demo.presentation import format_benchmark_markdown
from packages.analytics import NicheAnalyticsEngine
from packages.common.exceptions import CorpusNotReadyError, IndexNotReadyError
from packages.common.settings import AppSettings
from packages.data_contracts.corpus import CorpusFileChecksum, CorpusManifest
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest
from packages.retrieval import BM25Index, HybridRetrievalService, tokenize_vietnamese


def test_vietnamese_nfc_nfd_tokenization_identity() -> None:
    nfc_query = unicodedata.normalize("NFC", "Quán ốc đêm Quận 7 giá rẻ")
    nfd_query = unicodedata.normalize("NFD", "Quán ốc đêm Quận 7 giá rẻ")
    assert nfc_query != nfd_query
    assert tokenize_vietnamese(nfc_query) == tokenize_vietnamese(nfd_query)


def test_fail_closed_corpus_loader_rejects_missing_manifest(tmp_path: Path) -> None:
    with pytest.raises(CorpusNotReadyError):
        NicheAnalyticsEngine.from_corpus_dir(tmp_path)


def test_niche_analytics_and_hybrid_retrieval_end_to_end() -> None:
    corpus_dir = AppSettings().corpus_dir
    bm25_dir = AppSettings().bm25_index_dir

    engine = NicheAnalyticsEngine.from_corpus_dir(corpus_dir)
    bench = engine.compute_benchmark(
        NicheQueryFilter(video_format="Review quán ăn", city_norm="hồ chí minh")
    )
    assert bench.matched_videos > 500
    assert bench.median_plays > 0
    assert bench.duration_q25_sec <= bench.duration_median_sec <= bench.duration_q75_sec
    assert bench.median_word_per_second > 1.0
    assert len(bench.top_posting_hours) >= 1
    assert "total_ms" in bench.timings_ms

    service = HybridRetrievalService.from_dirs(df_videos=engine.df_videos, bm25_dir=bm25_dir)
    resp = service.search(
        RetrievalRequest(
            query="quán ốc bình dân ăn đêm ở Sài Gòn",
            mode="bm25",
            top_k=5,
            rerank=True,
            filters=NicheQueryFilter(city_norm="hồ chí minh"),
        )
    )
    assert len(resp.items) == 5
    assert resp.reranked is True
    assert resp.items[0].citation.tiktok_url.startswith("https://www.tiktok.com/@")
    assert resp.items[0].hook_text != ""
    assert "bm25_ms" in resp.timings_ms

    # Explicit dense mode must raise bounded IndexNotReadyError when Qdrant container is offline
    if service.qdrant and not service.qdrant.check_collection_ready()[0]:
        with pytest.raises(IndexNotReadyError):
            service.search(RetrievalRequest(query="bún bò", mode="dense", top_k=3))

    # BM25 save/load round-trip on tiny fixture
    mini = BM25Index.build(["v1", "v2"], ["phở bò hà nội đậm đà", "cơm tấm sườn bì chả sài gòn"])
    hits = mini.search("phở bò hà nội", top_k=2)
    assert hits[0][0] == "v1"


def _mini_manifest(total_videos: int) -> CorpusManifest:
    return CorpusManifest(
        snapshot_id="mini_m2_1",
        created_at="2026-11-18T00:00:00+00:00",
        date_window_start="2024-01-01",
        date_window_end="2025-03-01",
        total_creators=1,
        total_videos=max(1, total_videos),
        transcribed_videos=0,
        poi_tagged_videos=0,
        ec_tagged_videos=0,
        files=[
            CorpusFileChecksum(
                filename="dim_creators.parquet", rows=1, columns=1, sha256="a" * 64, size_bytes=10
            ),
            CorpusFileChecksum(
                filename="fact_videos.parquet", rows=total_videos, columns=1, sha256="b" * 64, size_bytes=10
            ),
        ],
        caveats=["Engagement metrics are single-snapshot observations captured in Mar-Apr 2025."],
    )


def _mini_df(n: int = 5) -> pd.DataFrame:
    rows = []
    for i in range(n):
        idx = i + 1
        has_tr = idx in (2, 3, 4)
        rows.append(
            {
                "video_id": f"v{idx}",
                "play_count": idx * 100,
                "engagement_rate": round(i * 0.02, 4),
                "duration_sec": idx * 10,
                "duration_bucket": "short_20_45s" if idx <= 4 else "medium_45_90s",
                "has_transcript": has_tr,
                "word_per_second": float(idx) if has_tr else 0.0,
                "hashtags": [f"tag{j}" for j in range(idx)],
                "hashtag_count": idx,
                "create_hour": 19 if idx <= 3 else 20,
                "poi_name": f"Quán {idx}" if idx <= 2 else None,
                "city_norm": "hồ chí minh" if idx <= 2 else None,
                "region": "south" if idx <= 2 else "unknown",
                "video_format": "Review quán ăn",
                "food_category": "Món nước & Sợi",
                "price_tier": "budget_lt50k" if idx <= 2 else "unspecified",
                "occasions": ["an_dem"] if idx == 1 else [],
            }
        )
    return pd.DataFrame(rows)


def test_hand_checkable_quantiles_provenance_missingness_and_relaxation() -> None:
    df_v = _mini_df(5)
    engine = NicheAnalyticsEngine(manifest=_mini_manifest(5), df_creators=pd.DataFrame([{"author_id": "a1"}]), df_videos=df_v)

    bench = engine.compute_benchmark(NicheQueryFilter())
    assert bench.matched_videos == 5
    assert bench.sparse_slice_abstained is False
    assert bench.median_plays == 300.0
    assert bench.p75_plays == 400.0
    assert bench.median_engagement_rate == 0.04
    assert bench.duration_q25_sec == 20.0
    assert bench.duration_median_sec == 30.0
    assert bench.duration_q75_sec == 40.0
    assert bench.hashtag_q25 == 2
    assert bench.hashtag_q75 == 4
    assert bench.median_word_per_second == 3.0
    assert bench.cohort_window_start == "2024-01-01"
    assert bench.cohort_window_end == "2025-03-01"
    assert "2025" in bench.observation_snapshot
    assert bench.missingness["transcript_missing_pct"] == 40.0
    assert bench.missingness["poi_missing_pct"] == 60.0
    assert bench.missingness["city_missing_pct"] == 60.0
    assert bench.missingness["price_unspecified_pct"] == 60.0

    # Progressive filter relaxation drops duration_bucket/occasion/price_tier cleanly when combination has 0 matches
    relaxed = engine.compute_benchmark(
        NicheQueryFilter(
            video_format="Review quán ăn",
            city_norm="hồ chí minh",
            occasion="hen_ho",
            duration_bucket="long_gt90s",
        )
    )
    assert relaxed.matched_videos == 2
    assert "relaxed_filters" in relaxed.applied_filters
    assert "duration_bucket" in relaxed.applied_filters["relaxed_filters"]


def test_sparse_slice_abstention_zero_division_and_descriptive_wording() -> None:
    # 1. Sparse slice (n=3 < 5): abstains from top_posting_hours and top_poi_venues
    df_sparse = _mini_df(3)
    eng_sparse = NicheAnalyticsEngine(
        manifest=_mini_manifest(3), df_creators=pd.DataFrame([{"author_id": "a1"}]), df_videos=df_sparse
    )
    sparse_bench = eng_sparse.compute_benchmark(NicheQueryFilter())
    assert sparse_bench.matched_videos == 3
    assert sparse_bench.sparse_slice_abstained is True
    assert sparse_bench.top_posting_hours == []
    assert sparse_bench.top_poi_venues == []

    # 2. Empty DataFrame (n=0): returns 0.0 durations instead of fabricated defaults
    df_empty = _mini_df(5).iloc[0:0].copy()
    eng_empty = NicheAnalyticsEngine(
        manifest=_mini_manifest(1), df_creators=pd.DataFrame([{"author_id": "a1"}]), df_videos=df_empty
    )
    empty_bench = eng_empty.compute_benchmark(NicheQueryFilter())
    assert empty_bench.matched_videos == 0
    assert empty_bench.sparse_slice_abstained is True
    assert empty_bench.duration_q25_sec == 0.0
    assert empty_bench.duration_median_sec == 0.0
    assert empty_bench.duration_q75_sec == 0.0
    assert empty_bench.median_word_per_second == 0.0

    # 3. Descriptive wording check (no optimum/causal assertions)
    md = format_benchmark_markdown(sparse_bench.model_dump())
    lower_md = md.lower()
    assert "tối ưu" not in lower_md
    assert "hiệu quả nhất" not in lower_md
    assert "đảm bảo viral" not in lower_md
    assert "2024-01-01" in md
    assert "không đủ mẫu" in lower_md or "tạm dừng xếp hạng" in lower_md
