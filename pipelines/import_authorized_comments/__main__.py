from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from .importer import import_authorized_comments


def main() -> None:
    parser = argparse.ArgumentParser(description="Import authorized comments for existing fresh Gold videos.")
    parser.add_argument("--comments-file", type=Path, required=True)
    parser.add_argument("--source-label", required=True)
    parser.add_argument("--base-corpus", type=Path, default=Path("data/corpus/m3_3_pilot_snapshot_v1"))
    parser.add_argument("--work-dir", type=Path, default=Path("data/raw_incremental/authorized_comments_import"))
    parser.add_argument("--output-gold", type=Path, default=Path("data/corpus/m3_3_authorized_comments_v1"))
    parser.add_argument("--as-of", default=None, help="ISO-8601 UTC reference time; defaults to now.")
    parser.add_argument("--max-rows", type=int, default=1000)
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if not 1 <= args.max_rows <= 5000:
        parser.error("--max-rows must be from 1 to 5000")
    try:
        as_of = datetime.fromisoformat(args.as_of.replace("Z", "+00:00")) if args.as_of else datetime.now(UTC)
    except ValueError:
        parser.error("--as-of must be an ISO-8601 datetime")
    receipt = import_authorized_comments(
        args.comments_file,
        args.base_corpus,
        args.work_dir,
        args.output_gold,
        source_label=args.source_label,
        as_of_utc=as_of,
        preflight_only=args.preflight_only,
        max_rows=args.max_rows,
    )
    print(json.dumps(receipt.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
