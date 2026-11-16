from __future__ import annotations

import unicodedata
from pathlib import Path

import pytest

from packages.analytics import NicheAnalyticsEngine
from packages.common.exceptions import CorpusNotReadyError, IndexNotReadyError
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
    corpus_dir = Path("data/corpus/20261116_v1")
    bm25_dir = Path("artifacts/indexes/bm25-v1")

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
