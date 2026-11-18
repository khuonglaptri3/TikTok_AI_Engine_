from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipelines.ingest_incremental_to_gold.converter import ingest_incremental_batch_to_gold


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert 4-month incremental JSONL batch into extended Gold Corpus snapshot."
    )
    parser.add_argument("--base-corpus", type=Path, default=Path("data/corpus/20261117_recovered_v1"))
    parser.add_argument(
        "--incremental-jsonl",
        type=Path,
        default=Path("data/raw_incremental/batch_latest/videos_4m.jsonl"),
    )
    parser.add_argument("--output-corpus", type=Path, default=Path("data/corpus/20261117_incremental_v1"))
    parser.add_argument(
        "--update-existing",
        action="store_true",
        help="Enrich already-ingested video IDs with new transcripts or comments without discarding base metadata.",
    )
    args = parser.parse_args()

    manifest = ingest_incremental_batch_to_gold(
        base_corpus_dir=args.base_corpus,
        incremental_jsonl=args.incremental_jsonl,
        output_corpus_dir=args.output_corpus,
        update_existing=args.update_existing,
    )
    print(json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
