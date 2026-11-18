"""Build populated CPU dense vector index over at most 5,000 Gold records (M6.1)."""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from typing import Any

import pandas as pd

from packages.analytics import load_verified_corpus
from packages.common.resources import get_peak_rss_mib
from packages.retrieval.dense import LocalDenseIndex, QdrantDenseAdapter, build_dense_encoder

MAX_M6_1_RECORDS = 5000


def select_eligible_corpus_slice(
    df_videos: pd.DataFrame,
    max_records: int = MAX_M6_1_RECORDS,
) -> pd.DataFrame:
    """Select up to max_records (<= 5,000) eligible transcribed records deterministically."""
    if max_records <= 0 or max_records > MAX_M6_1_RECORDS:
        raise ValueError(
            f"max_records must be within [1, {MAX_M6_1_RECORDS}] for M6.1 pilot, got {max_records}"
        )
    sub = df_videos[df_videos["has_transcript"] & (df_videos["rag_document"].astype(str).str.len() > 0)].copy()
    sub = sub.sort_values(by=["play_count", "video_id"], ascending=[False, True], kind="mergesort")
    return sub.head(max_records).reset_index(drop=True)


def build_dense_index(
    *,
    corpus_dir: Path,
    output_dir: Path,
    backend: str = "tfidf_svd",
    model_name: str = "intfloat/multilingual-e5-small",
    dimension: int = 128,
    max_records: int = MAX_M6_1_RECORDS,
    qdrant_url: str | None = None,
    qdrant_collection: str = "tiktok_fnb_videos_v1",
) -> dict[str, Any]:
    """Encode <= 5,000 eligible documents on CPU and persist a versioned dense index."""
    manifest, _, df_videos = load_verified_corpus(corpus_dir)
    sliced = select_eligible_corpus_slice(df_videos, max_records=max_records)
    video_ids = sliced["video_id"].astype(str).tolist()
    documents = sliced["rag_document"].astype(str).tolist()

    t0 = time.perf_counter()
    encoder = build_dense_encoder(
        backend=backend,
        documents=documents,
        model_name=model_name,
        dimension=dimension,
    )
    embeddings = encoder.encode_documents(documents)
    build_time_sec = round(time.perf_counter() - t0, 3)
    peak_rss_mb = round(get_peak_rss_mib(), 2)

    index = LocalDenseIndex.build(
        video_ids=video_ids,
        embeddings=embeddings,
        model_id=encoder.model_id,
    )
    receipt = index.save(
        index_dir=output_dir,
        corpus_snapshot_id=manifest.snapshot_id,
        encoder=encoder,
        extra_receipt={
            "encoder_backend": backend,
            "max_records_cap": MAX_M6_1_RECORDS,
            "selection_rule": "eligible transcribed rag_document sorted by (-play_count, video_id)",
            "build_time_sec": build_time_sec,
            "peak_rss_mb": peak_rss_mb,
            "peak_rss_unit": "MiB",
            "peak_rss_scope": "process_lifetime",
            "qdrant_populated": False,
        },
    )

    if qdrant_url:
        adapter = QdrantDenseAdapter(qdrant_url=qdrant_url, collection_name=qdrant_collection)
        adapter.ensure_collection(vector_size=encoder.dimension)
        points = [
            (vid, embeddings[idx].tolist(), {"video_id": vid})
            for idx, vid in enumerate(video_ids)
        ]
        adapter.upsert_vectors(points)
        receipt["qdrant_populated"] = True
        receipt["qdrant_collection"] = qdrant_collection
        (output_dir / "dense-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Build CPU dense vector index for M6.1 pilot (<= 5,000 docs).")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/20261117_recovered_v1"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/indexes/dense-svd-v1"))
    parser.add_argument(
        "--backend",
        choices=("tfidf_svd", "fastembed", "sentence_transformers"),
        default="tfidf_svd",
    )
    parser.add_argument("--model-name", default="intfloat/multilingual-e5-small")
    parser.add_argument("--dimension", type=int, default=128)
    parser.add_argument("--max-records", type=int, default=MAX_M6_1_RECORDS)
    parser.add_argument("--qdrant-url", default=None)
    parser.add_argument("--qdrant-collection", default="tiktok_fnb_videos_v1")
    args = parser.parse_args()

    receipt = build_dense_index(
        corpus_dir=args.corpus,
        output_dir=args.output,
        backend=args.backend,
        model_name=args.model_name,
        dimension=args.dimension,
        max_records=args.max_records,
        qdrant_url=args.qdrant_url,
        qdrant_collection=args.qdrant_collection,
    )
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
