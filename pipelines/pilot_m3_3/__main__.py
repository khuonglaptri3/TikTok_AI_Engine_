from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from pipelines.crawl_incremental.crawler_service import load_dotenv_if_present
from pipelines.crawl_incremental.models import CollectorBackend
from pipelines.pilot_m3_3.models import M33PilotConfig
from pipelines.pilot_m3_3.runner import run_m3_3_pilot, run_m3_3_preflight


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
        "--backend",
        choices=("auto", "tiktokapi", "ytdlp"),
        default="auto",
        help="Live collector backend: auto (TikTokApi -> yt-dlp fallback), tiktokapi, or ytdlp.",
    )
    parser.add_argument(
        "--cookies-file",
        type=Path,
        default=None,
        help="Optional Netscape cookies.txt path for yt-dlp metadata/audio extraction.",
    )
    parser.add_argument(
        "--tiktok-browser",
        choices=("chromium", "webkit", "firefox"),
        default=None,
        help="Playwright browser engine when TikTokApi is active (default: TIKTOK_BROWSER env or chromium).",
    )
    parser.add_argument(
        "--tiktok-headless",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Run Playwright headless (default True; pass --no-tiktok-headless on desktop PCs if needed).",
    )
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
    parser.add_argument(
        "--auto-creators",
        type=int,
        default=0,
        help="Auto-select up to K (1..5) curated F&B creators from author_unique_ids.txt + dim_creators.parquet.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume interrupted collection from collector_checkpoint.json inside --work-dir/batch.",
    )
    parser.add_argument(
        "--enrich-comments-only",
        action="store_true",
        help="Enrich comments onto existing videos_4m.jsonl in --work-dir/batch without re-running discovery, audio, or ASR.",
    )
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Run local readiness check (0 network calls, 0 snapshot writes) and print JSON report.",
    )
    parser.add_argument("--asr-model", type=str, default="small")
    parser.add_argument("--as-of", type=str, default=None)
    args = parser.parse_args()

    dotenv_file = Path(".env")
    load_dotenv_if_present(dotenv_file)

    as_of_dt = (
        datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if args.as_of
        else datetime.now(UTC)
    )
    if as_of_dt.tzinfo is None:
        as_of_dt = as_of_dt.replace(tzinfo=UTC)

    env_cookies = os.environ.get("TIKTOK_COOKIES_FILE", "").strip()
    cookies_path = args.cookies_file or (Path(env_cookies) if env_cookies else None)
    browser = args.tiktok_browser or os.environ.get("TIKTOK_BROWSER", "chromium").strip() or "chromium"
    if args.tiktok_headless is not None:
        headless = bool(args.tiktok_headless)
    else:
        headless = os.environ.get("TIKTOK_HEADLESS", "true").strip().lower() not in {"false", "0", "no"}

    cfg = M33PilotConfig(
        mode=args.mode,
        allow_live_network=args.allow_live_network,
        backend=cast(CollectorBackend, args.backend),
        cookies_file=cookies_path,
        tiktok_browser=browser,
        tiktok_headless=headless,
        base_corpus_dir=args.base_corpus,
        batch_dir=args.work_dir / "batch",
        output_gold_dir=args.output_gold,
        output_bm25_dir=args.output_bm25,
        receipt_path=args.receipt_path,
        inspection_sheet_path=args.inspection_sheet,
        fixture_path=args.fixture_path,
        creators=args.creator,
        auto_creators=args.auto_creators,
        resume=args.resume,
        enrich_comments_only=args.enrich_comments_only,
        as_of_utc=as_of_dt,
        asr_model_size=args.asr_model,
    )
    if args.preflight_only:
        report = run_m3_3_preflight(cfg, dotenv_path=dotenv_file)
        print(json.dumps(report.model_dump(), ensure_ascii=False, indent=2))
        return

    receipt = run_m3_3_pilot(cfg, dotenv_path=dotenv_file)
    print(json.dumps(receipt.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
