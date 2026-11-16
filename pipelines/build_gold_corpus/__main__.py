from __future__ import annotations

import argparse
import json
from pathlib import Path

from pipelines.build_gold_corpus.builder import build_gold_corpus


def main() -> None:
    parser = argparse.ArgumentParser(description="Build immutable Gold Parquet corpus snapshot.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[2],
        help="Repository root containing read-only data/ directory.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/corpus/20261116_v1"),
        help="Output snapshot directory.",
    )
    args = parser.parse_args()
    out_dir = args.output if args.output.is_absolute() else (args.root / args.output)
    manifest = build_gold_corpus(root_dir=args.root, output_dir=out_dir)
    print(json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
