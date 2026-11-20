from __future__ import annotations

from pathlib import Path
from typing import Any

import httpx
import numpy as np
import pandas as pd
import pytest

from packages.common.exceptions import IndexNotReadyError
from packages.data_contracts.query import RetrievalRequest
from packages.retrieval.dense.encoder import TruncatedSvdDenseEncoder
from packages.retrieval.dense.local_index import LocalDenseIndex
from packages.retrieval.dense.qdrant_adapter import QdrantDenseAdapter
from packages.retrieval.service import HybridRetrievalService
from packages.retrieval.sparse.bm25 import BM25Index
from pipelines.benchmark_retrieval.dense_hybrid_pilot import paired_bootstrap_ci
from pipelines.build_dense_sparse_index.dense import select_eligible_corpus_slice


def _sample_docs() -> tuple[list[str], list[str]]:
    topics = [
        "bún bò huế nước dùng đậm đà sả ớt thơm ngon",
        "tô bún bò tái nạm chả cua huế chuẩn vị",
        "phở bò tái chín Hà Nội nước lèo thanh ngọt",
        "bánh mì thịt nướng chả lụa giòn rụm buổi sáng",
        "ốc hương xào bơ tỏi ốc móng tay bình dân quận 4",
        "trà sữa trân châu đường đen kem cheese béo ngậy",
        "cà phê muối đà lạt view đồi thông sáng sớm",
        "cơm tấm sườn bì chả trứng ốp la sài gòn",
        "bún đậu mắm tôm chả cốm nem chua rán giòn",
        "lẩu thái chua cay hải sản tôm mực ngập tràn",
        "gà rán sốt cay hàn quốc giòn tan cùng phô mai",
        "salad ức gà bơ healthy giảm cân giữ dáng",
    ]
    ids = [f"v{i:02d}" for i in range(len(topics))]
    return ids, topics


def test_truncated_svd_encoder_fit_normalize_and_roundtrip(tmp_path: Path) -> None:
    _, docs = _sample_docs()
    enc = TruncatedSvdDenseEncoder.fit(docs, dimension=8)
    assert enc.dimension == 8

    q_vec = np.asarray(enc.encode_query("bún bò huế cay"), dtype=np.float32)
    d_vecs = np.asarray(enc.encode_documents(docs), dtype=np.float32)
    assert q_vec.shape == (8,)
    assert d_vecs.shape == (len(docs), 8)
    assert float(np.linalg.norm(q_vec)) == pytest.approx(1.0, abs=1e-4)
    assert float(np.linalg.norm(d_vecs[0])) == pytest.approx(1.0, abs=1e-4)

    enc_dir = tmp_path / "svd_enc"
    enc.save(enc_dir)
    loaded = TruncatedSvdDenseEncoder.load(enc_dir)
    np.testing.assert_allclose(loaded.encode_query("bún bò huế cay"), q_vec, atol=1e-5)


def test_local_dense_index_build_filter_and_integrity(tmp_path: Path) -> None:
    vids, docs = _sample_docs()
    enc = TruncatedSvdDenseEncoder.fit(docs, dimension=8)
    vecs = enc.encode_documents(docs)

    idx_dir = tmp_path / "dense_idx"
    idx = LocalDenseIndex.build(video_ids=vids, embeddings=vecs, model_id=enc.model_id)
    receipt = idx.save(idx_dir, corpus_snapshot_id="snap_test")
    assert receipt["document_count"] == len(vids)

    # Collision fails closed
    with pytest.raises(FileExistsError):
        idx.save(idx_dir, corpus_snapshot_id="snap_test")

    loaded = LocalDenseIndex.load(idx_dir)
    assert loaded.check_collection_ready() == (True, len(vids))

    q_vec = enc.encode_query("bún bò huế")
    filtered = loaded.search_vectors(q_vec, top_k=5, allowed_video_ids={"v00", "v05"})
    assert {vid for vid, _ in filtered}.issubset({"v00", "v05"})
    assert filtered[0][0] == "v00"

    # Corrupt embeddings fail closed
    (idx_dir / "embeddings.npy").write_bytes(b"corrupted_npy")
    with pytest.raises(IndexNotReadyError):
        LocalDenseIndex.load(idx_dir)


def test_qdrant_adapter_ensure_collection_and_upsert(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, str, dict[str, Any]]] = []

    def _fake_put(url: str, json: dict[str, Any], timeout: float) -> httpx.Response:
        calls.append(("PUT", url, json))
        return httpx.Response(200, json={"result": True, "status": "ok"})

    monkeypatch.setattr(httpx, "put", _fake_put)
    adapter = QdrantDenseAdapter("http://127.0.0.1:6333", "tiktok_test")
    adapter.ensure_collection(vector_size=8)
    adapter.upsert_vectors(
        [("7304970581181549826", [0.1] * 8, {"video_id": "7304970581181549826"})]
    )
    assert len(calls) == 2
    assert calls[0][1].endswith("/collections/tiktok_test")
    assert calls[0][2]["vectors"]["size"] == 8
    assert calls[1][1].endswith("/collections/tiktok_test/points?wait=true")
    assert calls[1][2]["points"][0]["payload"]["video_id"] == "7304970581181549826"


def test_hybrid_service_parity_bm25_dense_rrf(tmp_path: Path) -> None:
    vids, docs = _sample_docs()
    df = pd.DataFrame(
        [
            {
                "video_id": vid,
                "author_handle": f"creator_{i}",
                "tiktok_url": f"https://www.tiktok.com/@creator_{i}/video/{vid}",
                "play_count": 10000 + i * 500,
                "viral_multiplier": 2.0,
                "engagement_rate": 0.05,
                "video_format": "Review món ăn",
                "food_category": "Món nước & Sợi" if i in (0, 1, 2, 8) else "Ăn vặt & Đường phố",
                "dishes": [],
                "city_norm": "hồ chí minh" if i % 2 == 0 else "hà nội",
                "region": "nam" if i % 2 == 0 else "bắc",
                "district_norm": None,
                "poi_name": None,
                "price_tier": "budget_lt50k",
                "occasions": ["an_sang_trua_nhanh"],
                "duration_sec": 35,
                "duration_bucket": "short_20_45s",
                "has_transcript": True,
                "transcript": doc,
                "hook_text": doc,
                "body_beats": [doc],
                "cta_text": "Lưu lại nha",
                "rag_document": doc,
            }
            for i, (vid, doc) in enumerate(zip(vids, docs))
        ]
    )

    bm25 = BM25Index.build(vids, docs, min_bigram_df=1)
    enc = TruncatedSvdDenseEncoder.fit(docs, dimension=8)
    dense = LocalDenseIndex.build(vids, enc.encode_documents(docs), model_id=enc.model_id)

    svc = HybridRetrievalService(
        df_videos=df,
        bm25_index=bm25,
        dense_index=dense,
        dense_encoder=enc,
    )
    for mode in ("bm25", "dense", "hybrid_rrf"):
        resp = svc.search(RetrievalRequest(query="bún bò huế", mode=mode, top_k=3, rerank=False))
        assert resp.mode == mode
        assert len(resp.items) == 3
        assert resp.items[0].citation.video_id in {"v00", "v01"}
    assert "dense_ms" in resp.timings_ms
    assert "fusion_ms" in resp.timings_ms


def test_max_records_cap_and_paired_bootstrap_ci() -> None:
    df = pd.DataFrame(
        {
            "video_id": [f"id_{i:04d}" for i in range(60)],
            "has_transcript": [True] * 60,
            "rag_document": [f"document {i}" for i in range(60)],
            "play_count": list(range(60)),
        }
    )
    with pytest.raises(ValueError):
        select_eligible_corpus_slice(df, max_records=5001)

    sliced = select_eligible_corpus_slice(df, max_records=20)
    assert len(sliced) == 20

    summary = paired_bootstrap_ci([0.8, 0.6, 0.4, 0.9], [0.5, 0.6, 0.2, 0.7], n_resamples=200, seed=7)
    assert summary["mean_diff"] == pytest.approx(0.175, abs=1e-4)
    assert summary["ci_low"] <= summary["mean_diff"] <= summary["ci_high"]


def test_from_dirs_and_settings_wire_dense_index_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from packages.common.settings import AppSettings

    vids, docs = _sample_docs()
    df = pd.DataFrame(
        [
            {
                "video_id": vid,
                "author_handle": f"creator_{i}",
                "tiktok_url": f"https://www.tiktok.com/@creator_{i}/video/{vid}",
                "play_count": 10000,
                "viral_multiplier": 1.0,
                "engagement_rate": 0.05,
                "video_format": "Review món ăn",
                "food_category": "Món nước & Sợi",
                "dishes": [],
                "city_norm": "hồ chí minh",
                "region": "nam",
                "district_norm": None,
                "poi_name": None,
                "price_tier": "budget_lt50k",
                "occasions": [],
                "duration_sec": 30,
                "duration_bucket": "short_20_45s",
                "has_transcript": True,
                "transcript": doc,
                "hook_text": doc,
                "body_beats": [doc],
                "cta_text": "",
                "rag_document": doc,
            }
            for i, (vid, doc) in enumerate(zip(vids, docs))
        ]
    )
    bm25_dir = tmp_path / "bm25"
    dense_dir = tmp_path / "dense"
    BM25Index.build(vids, docs, min_bigram_df=1).save(bm25_dir, corpus_snapshot_id="s1")
    enc = TruncatedSvdDenseEncoder.fit(docs, dimension=8)
    LocalDenseIndex.build(vids, enc.encode_documents(docs), model_id=enc.model_id).save(
        dense_dir, corpus_snapshot_id="s1", encoder=enc
    )

    monkeypatch.setenv("TIKTOK_RAG_DENSE_INDEX_DIR", str(dense_dir))
    cfg = AppSettings.from_env()
    assert cfg.dense_index_dir == dense_dir

    svc = HybridRetrievalService.from_dirs(df_videos=df, bm25_dir=bm25_dir, dense_dir=dense_dir)
    resp = svc.search(RetrievalRequest(query="bún bò huế", mode="dense", top_k=2, rerank=False))
    assert resp.mode == "dense"
    assert len(resp.items) == 2


def test_v2_pilot_split_mode_and_eligible_pool_parity() -> None:
    from pipelines.benchmark_retrieval.pilot_m2_2 import (
        evaluate_pilot_split,
        measure_warm_latency,
    )

    vids, docs = _sample_docs()
    df = pd.DataFrame(
        [
            {
                "video_id": vid,
                "author_handle": f"creator_{i}",
                "tiktok_url": f"https://www.tiktok.com/@creator_{i}/video/{vid}",
                "play_count": 10000 + i * 500,
                "viral_multiplier": 2.0,
                "engagement_rate": 0.05,
                "video_format": "Review món ăn",
                "food_category": "Món nước & Sợi" if i in (0, 1, 2, 8) else "Ăn vặt & Đường phố",
                "dishes": [],
                "city_norm": "hồ chí minh" if i % 2 == 0 else "hà nội",
                "region": "nam" if i % 2 == 0 else "bắc",
                "district_norm": None,
                "poi_name": None,
                "price_tier": "budget_lt50k",
                "occasions": [],
                "duration_sec": 35,
                "duration_bucket": "short_20_45s",
                "has_transcript": True,
                "transcript": doc,
                "hook_text": doc,
                "body_beats": [doc],
                "cta_text": "",
                "rag_document": doc,
            }
            for i, (vid, doc) in enumerate(zip(vids, docs))
        ]
    )
    bm25 = BM25Index.build(vids, docs, min_bigram_df=1)
    enc = TruncatedSvdDenseEncoder.fit(docs, dimension=8)
    dense = LocalDenseIndex.build(vids, enc.encode_documents(docs), model_id=enc.model_id)
    eligible = {"v00", "v02", "v03", "v04", "v05", "v06"}
    svc = HybridRetrievalService(
        df_videos=df[df["video_id"].isin(eligible)].copy(),
        bm25_index=bm25,
        dense_index=dense,
        dense_encoder=enc,
        restrict_to_df=True,
    )
    queries = [
        {
            "query_id": "q1",
            "phenomenon": "exact_dish",
            "expect_no_answer": False,
            "filters": {},
            "query": "bún bò huế sả ớt",
        },
        {
            "query_id": "q2",
            "phenomenon": "zero_in_slice",
            "expect_no_answer": False,
            "filters": {},
            "query": "tái nạm chả cua huế",
        },
        {
            "query_id": "q3",
            "phenomenon": "out_of_corpus_city",
            "expect_no_answer": True,
            "filters": {"city_norm": "cần thơ"},
            "query": "lẩu mắm cần thơ",
        },
    ]
    qrels = {
        "q1": {"v00": "1", "v01": "1", "v02": "0"},
        "q2": {"v01": "1"},
        "q3": {},
    }
    res = evaluate_pilot_split(
        svc,
        queries,
        qrels,
        mode="hybrid_rrf",
        rerank=False,
        k=5,
        eligible_video_ids=eligible,
    )
    assert res["evaluated_answerable_count"] == 1
    assert res["zero_relevant_pool_count"] == 1
    assert res["no_answer_abstained_count"] == 1
    assert res["fabricated_support_count"] == 0
    assert res["per_query"][0]["relevant_pool_size"] == 1

    lat = measure_warm_latency(svc, queries[:2], mode="hybrid_rrf", rerank=False, n_warm=2, k=5)
    assert lat["n_warm_requests"] == 2
    assert lat["peak_rss_mib"] > 0


def test_v2_pilot_suite_benchmark_structure(tmp_path: Path) -> None:
    from pipelines.benchmark_retrieval.dense_hybrid_v2_pilot import benchmark_dense_backend

    vids, docs = _sample_docs()
    df = pd.DataFrame(
        [
            {
                "video_id": vid,
                "author_handle": f"creator_{i}",
                "tiktok_url": f"https://www.tiktok.com/@creator_{i}/video/{vid}",
                "play_count": 10000 + (12 - i) * 500,
                "viral_multiplier": 2.0,
                "engagement_rate": 0.05,
                "video_format": "Review món ăn",
                "food_category": "Món nước & Sợi" if i in (0, 1, 2, 8) else "Ăn vặt & Đường phố",
                "dishes": [],
                "city_norm": "hồ chí minh" if i % 2 == 0 else "hà nội",
                "region": "nam" if i % 2 == 0 else "bắc",
                "district_norm": None,
                "poi_name": None,
                "price_tier": "budget_lt50k",
                "occasions": [],
                "duration_sec": 35,
                "duration_bucket": "short_20_45s",
                "has_transcript": True,
                "transcript": doc,
                "hook_text": doc,
                "body_beats": [doc],
                "cta_text": "",
                "rag_document": doc,
            }
            for i, (vid, doc) in enumerate(zip(vids, docs))
        ]
    )
    bm25_dir = tmp_path / "bm25"
    dense_dir = tmp_path / "dense"
    BM25Index.build(vids, docs, min_bigram_df=1).save(bm25_dir, corpus_snapshot_id="s1")
    sliced_df = select_eligible_corpus_slice(df, max_records=6)
    s_vids = sliced_df["video_id"].astype(str).tolist()
    s_docs = sliced_df["rag_document"].astype(str).tolist()
    enc = TruncatedSvdDenseEncoder.fit(s_docs, dimension=4)
    LocalDenseIndex.build(s_vids, enc.encode_documents(s_docs), model_id=enc.model_id).save(
        dense_dir, corpus_snapshot_id="s1", encoder=enc
    )

    dev_queries = [
        {
            "query_id": "d1",
            "phenomenon": "exact_dish",
            "expect_no_answer": False,
            "filters": {},
            "query": "bún bò huế sả ớt",
        }
    ]
    test_queries = [
        {
            "query_id": "t1",
            "phenomenon": "exact_dish",
            "expect_no_answer": False,
            "filters": {},
            "query": "bánh mì thịt nướng",
        }
    ]
    qrels = {"d1": {"v00": "1"}, "t1": {"v03": "1"}}

    out = benchmark_dense_backend(
        df_videos=df,
        bm25_dir=bm25_dir,
        dense_dir=dense_dir,
        dev_queries=dev_queries,
        test_queries=test_queries,
        qrels=qrels,
        n_warm=2,
        n_boot=50,
    )
    assert out["parity_slice_doc_count"] == 6
    for split_name in ("dev", "locked_test"):
        assert set(out["splits"][split_name]["configs"].keys()) == {
            "bm25",
            "bm25_reranked",
            "dense",
            "dense_reranked",
            "hybrid_rrf",
            "hybrid_rrf_reranked",
        }
        assert "dense_minus_bm25" in out["splits"][split_name]["paired_bootstrap_comparisons"]
        cmp_d = out["splits"][split_name]["paired_bootstrap_comparisons"]["dense_minus_bm25"]["mrr_at_10"]
        dense_mrr = out["splits"][split_name]["configs"]["dense"]["mrr_at_10"]
        bm25_mrr = out["splits"][split_name]["configs"]["bm25"]["mrr_at_10"]
        assert cmp_d["mean_diff"] == pytest.approx(dense_mrr - bm25_mrr, abs=1e-4)
    assert set(out["latency_warm_requests"].keys()) == {
        "bm25",
        "bm25_reranked",
        "dense",
        "dense_reranked",
        "hybrid_rrf",
        "hybrid_rrf_reranked",
    }


def test_k_review_v2_pilot_enforces_restrict_to_df_when_bm25_exceeds_candidate_limit(
    tmp_path: Path,
) -> None:
    from pipelines.benchmark_retrieval.dense_hybrid_v2_pilot import benchmark_dense_backend

    rows: list[dict[str, Any]] = []
    vids: list[str] = []
    docs: list[str] = []
    # First 10 docs have highest play_count (selected into parity slice); next 90 out-of-slice docs
    # repeat the query terms heavily so global BM25 top-80 would completely starve the 10-doc slice
    # unless restrict_to_df=True is enforced inside benchmark_dense_backend.
    for i in range(100):
        in_slice = i < 10
        vid = f"v_{i:03d}"
        doc = (
            f"bún bò huế sả ớt ngon số {i}"
            if in_slice
            else ("bún bò huế sả ớt bún bò huế sả ớt bún bò huế đậm đà " * 3)
        )
        vids.append(vid)
        docs.append(doc)
        rows.append(
            {
                "video_id": vid,
                "author_handle": f"creator_{i}",
                "tiktok_url": f"https://www.tiktok.com/@creator_{i}/video/{vid}",
                "play_count": (500_000 - i * 100) if in_slice else (1_000 + i),
                "viral_multiplier": 2.0,
                "engagement_rate": 0.05,
                "video_format": "Review món ăn",
                "food_category": "Món nước & Sợi",
                "dishes": [],
                "city_norm": "hồ chí minh",
                "region": "nam",
                "district_norm": None,
                "poi_name": None,
                "price_tier": "budget_lt50k",
                "occasions": [],
                "duration_sec": 35,
                "duration_bucket": "short_20_45s",
                "has_transcript": True,
                "transcript": doc,
                "hook_text": doc,
                "body_beats": [doc],
                "cta_text": "",
                "rag_document": doc,
            }
        )
    df = pd.DataFrame(rows)
    bm25_dir = tmp_path / "bm25_100"
    dense_dir = tmp_path / "dense_10"
    BM25Index.build(vids, docs, min_bigram_df=1).save(bm25_dir, corpus_snapshot_id="s_100")

    sliced_df = select_eligible_corpus_slice(df, max_records=10)
    s_vids = sliced_df["video_id"].astype(str).tolist()
    s_docs = sliced_df["rag_document"].astype(str).tolist()
    enc = TruncatedSvdDenseEncoder.fit(s_docs, dimension=4)
    LocalDenseIndex.build(s_vids, enc.encode_documents(s_docs), model_id=enc.model_id).save(
        dense_dir, corpus_snapshot_id="s_100", encoder=enc
    )

    q_list = [
        {
            "query_id": "q_starve",
            "phenomenon": "exact_dish",
            "expect_no_answer": False,
            "filters": {},
            "query": "bún bò huế sả ớt",
        }
    ]
    qrels = {"q_starve": {"v_000": "1"}}
    out = benchmark_dense_backend(
        df_videos=df,
        bm25_dir=bm25_dir,
        dense_dir=dense_dir,
        dev_queries=q_list,
        test_queries=q_list,
        qrels=qrels,
        n_warm=2,
        n_boot=20,
    )
    bm25_cfg = out["splits"]["locked_test"]["configs"]["bm25"]
    assert len(bm25_cfg["per_query"][0]["retrieved_ids"]) == 10
    assert bm25_cfg["mrr_at_10"] > 0.0
    assert "unjudged_rate_at_10" in bm25_cfg


def test_k_review_qdrant_large_allowed_pool_never_leaks_unallowed_ids_and_oov_fast_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_post(url: str, json: dict[str, Any], timeout: float) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "result": [
                    {"id": 1, "score": 0.99, "payload": {"video_id": "v_wrong_city"}},
                    {"id": 2, "score": 0.88, "payload": {"video_id": "v_allowed_1"}},
                    {"id": 3, "score": 0.77, "payload": {"video_id": "v_allowed_2"}},
                ]
            },
        )

    monkeypatch.setattr(httpx, "post", _fake_post)
    adapter = QdrantDenseAdapter("http://127.0.0.1:6333", "tiktok_test")
    big_allowed = {f"v_allowed_{i}" for i in range(5005)}
    hits = adapter.search_vectors([0.1, 0.2], top_k=5, allowed_video_ids=big_allowed)
    assert [vid for vid, _ in hits] == ["v_allowed_1", "v_allowed_2"]

    # Early OOV anchor check must also avoid needless dense query encoding on dense / hybrid_rrf
    vids, docs = _sample_docs()
    df = pd.DataFrame(
        [
            {
                "video_id": vid,
                "author_handle": f"creator_{i}",
                "tiktok_url": f"https://www.tiktok.com/@creator_{i}/video/{vid}",
                "play_count": 10000,
                "viral_multiplier": 1.0,
                "engagement_rate": 0.05,
                "video_format": "Review món ăn",
                "food_category": "Món nước & Sợi",
                "dishes": [],
                "city_norm": "hồ chí minh",
                "region": "nam",
                "district_norm": None,
                "poi_name": None,
                "price_tier": "budget_lt50k",
                "occasions": [],
                "duration_sec": 30,
                "duration_bucket": "short_20_45s",
                "has_transcript": True,
                "transcript": doc,
                "hook_text": doc,
                "body_beats": [doc],
                "cta_text": "",
                "rag_document": doc,
            }
            for i, (vid, doc) in enumerate(zip(vids, docs))
        ]
    )
    bm25 = BM25Index.build(vids, docs, min_bigram_df=1)
    enc = TruncatedSvdDenseEncoder.fit(docs, dimension=8)
    dense = LocalDenseIndex.build(vids, enc.encode_documents(docs), model_id=enc.model_id)

    encode_calls = 0
    orig_encode = enc.encode_query

    def _counted_encode(q: str) -> list[float]:
        nonlocal encode_calls
        encode_calls += 1
        return orig_encode(q)

    monkeypatch.setattr(enc, "encode_query", _counted_encode)
    svc = HybridRetrievalService(df_videos=df, bm25_index=bm25, dense_index=dense, dense_encoder=enc)
    for mode in ("dense", "hybrid_rrf"):
        resp = svc.search(RetrievalRequest(query="lẩu sao hỏa zzzqx99", mode=mode, top_k=3))  # type: ignore[arg-type]
        assert resp.insufficient_evidence is True
    assert encode_calls == 0

