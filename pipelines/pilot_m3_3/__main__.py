from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from pipelines.pilot_m3_3.models import M33PilotConfig
from pipelines.pilot_m3_3.runner import run_m3_3_pilot


def main() -> None:
    parser = argparse.ArgumentParser(
        description="M3.3 capped capture-to-ASR-to-Gold-to-search pilot orchestrator."
    )
    parser.add_argument(
        "--mode",
        choices=("dry_run_fixture", "live_pilot"),
        default="live_pilot",
    )
    parser.add_argument("--allow-live-network", action="store_true")
    parser.add_argument(
        "--base-corpus",
        type=Path,
        default=Path("data/corpus/20261118_taxonomy_fix_v1"),
    )
    parser.add_argument(
        "--work-dir",
        type=Path,
        default=Path("data/raw_incremental/m3_3_pilot_run"),
    )
    parser.add_argument(
        "--output-gold",
        type=Path,
        default=Path("data/corpus/m3_3_pilot_snapshot_v1"),
    )
    parser.add_argument(
        "--output-bm25",
        type=Path,
        default=Path("artifacts/indexes/bm25-m3_3-pilot"),
    )
    parser.add_argument(
        "--receipt-path",
        type=Path,
        default=Path("docs/reports/milestones/M3.3/evidence/m3_3_pilot_receipt.json"),
    )
    parser.add_argument(
        "--inspection-sheet",
        type=Path,
        default=Path("docs/reports/milestones/M3.3/evidence/sample_inspection_sheet.jsonl"),
    )
    parser.add_argument("--fixture-path", type=Path, default=None)
    parser.add_argument("--creator", action="append", default=[])
    parser.add_argument("--asr-model", type=str, default="small")
    parser.add_argument("--as-of", type=str, default=None)
    args = parser.parse_args()

    as_of_dt = (
        datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if args.as_of
        else datetime.now(UTC)
    )
    if as_of_dt.tzinfo is None:
        as_of_dt = as_of_dt.replace(tzinfo=UTC)

    cfg = M33PilotConfig(
        mode=args.mode,
        allow_live_network=args.allow_live_network,
        base_corpus_dir=args.base_corpus,
        batch_dir=args.work_dir / "batch",
        output_gold_dir=args.output_gold,
        output_bm25_dir=args.output_bm25,
        receipt_path=args.receipt_path,
        inspection_sheet_path=args.inspection_sheet,
        fixture_path=args.fixture_path,
        creators=args.creator,
        as_of_utc=as_of_dt,
        asr_model_size=args.asr_model,
    )
    receipt = run_m3_3_pilot(cfg)
    print(json.dumps(receipt.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
