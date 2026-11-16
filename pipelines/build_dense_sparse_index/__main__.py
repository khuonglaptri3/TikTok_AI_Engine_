from __future__ import annotations

import argparse
import json
from pathlib import Path

from packages.analytics import load_verified_corpus
from packages.retrieval.sparse.bm25 import BM25Index


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Vietnamese NFC BM25 sparse index over Gold corpus.")
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/20261116_v1"))
    parser.add_argument("--output", type=Path, default=Path("artifacts/indexes/bm25-v1"))
    args = parser.parse_args()

    manifest, _, df_videos = load_verified_corpus(args.corpus)
    sub = df_videos[df_videos["has_transcript"] & (df_videos["rag_document"].str.len() > 0)]

    video_ids = sub["video_id"].astype(str).tolist()
    documents = sub["rag_document"].astype(str).tolist()

    bm25 = BM25Index.build(video_ids=video_ids, documents=documents, min_bigram_df=2)
    receipt = bm25.save(index_dir=args.output, corpus_snapshot_id=manifest.snapshot_id)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
