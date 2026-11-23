from __future__ import annotations

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import cast

import pandas as pd

from packages.data_contracts.multimodal import (
    RawCommentInput,
    RawIncrementalVideoRecord,
    RawWhisperSegment,
)
from pipelines.crawl_incremental.crawler_service import (
    compute_cutoff_utc,
    load_dotenv_if_present,
    select_curated_fnb_creators,
    write_incremental_batch,
)
from pipelines.crawl_incremental.models import (
    CollectorBackend,
    CollectorBounds,
    CollectorItemReceipt,
    CrawlManifest,
)
from pipelines.crawl_incremental.providers import (
    LiveNetworkDisabledError,
    OfflineFixtureAudioConverter,
    OfflineFixtureCollectorProvider,
    YtDlpAudioConverter64k,
    build_live_collector_provider,
)
from pipelines.crawl_incremental.worker import BoundedIncrementalCollector, _atomic_write_json


def _build_seed_demo_records(now_utc: datetime) -> list[RawIncrementalVideoRecord]:
    recent_ts = (now_utc - timedelta(days=12)).isoformat()
    return [
        RawIncrementalVideoRecord(
            video_id="7600000000000000001",
            author_id="7009454289408099355",
            author_handle="ansapsaigon_demo",
            author_nickname="Ăn Sập Sài Gòn Demo",
            follower_count=450000,
            create_time=recent_ts,
            caption="Review quán lẩu bò mắm ruốc mới mở Quận 10 giá 169k siêu đông #ancungtiktok #laubo",
            hashtags=["ancungtiktok", "laubo", "quan10"],
            duration_sec=42,
            play_count=620000,
            digg_count=24500,
            comment_count=410,
            share_count=1200,
            collect_count=5300,
            is_ad=False,
            is_ec_video=False,
            poi_id="poi_q10_laubo_01",
            poi_name="Lẩu Bò Mắm Ruốc Cô Ba Quận 10",
            poi_address="215 Sư Vạn Hạnh, Quận 10, TP. Hồ Chí Minh",
            poi_city="Ho Chi Minh City",
            poi_category_tiny="Hotpot Restaurant",
            transcript=(
                "Tặng ngay voucher giảm giá khai trương cho anh em ghé Lẩu Bò Mắm Ruốc Cô Ba Quận 10 nha. "
                "Nước dùng lẩu bò thơm đậm đà mùi sả và mắm ruốc, thịt bò tươi mềm đầy đặn giá chỉ 169k cực kỳ hợp lý. "
                "Không gian quán rộng rãi sạch sẽ nhân viên nhiệt tình dễ thương, nhớ ghé trải nghiệm liền nhé!"
            ),
            whisper_segments=[
                RawWhisperSegment(
                    start_sec=0.0,
                    end_sec=9.5,
                    text="Tặng ngay voucher giảm giá khai trương cho anh em ghé Lẩu Bò Mắm Ruốc Cô Ba Quận 10 nha.",
                ),
                RawWhisperSegment(
                    start_sec=9.5,
                    end_sec=26.0,
                    text="Nước dùng lẩu bò thơm đậm đà mùi sả và mắm ruốc, thịt bò tươi mềm đầy đặn giá chỉ 169k cực kỳ hợp lý.",
                ),
                RawWhisperSegment(
                    start_sec=26.0,
                    end_sec=42.0,
                    text="Không gian quán rộng rãi sạch sẽ nhân viên nhiệt tình dễ thương, nhớ ghé trải nghiệm liền nhé!",
                ),
            ],
            comments=[
                RawCommentInput(
                    comment_id="c1",
                    author_handle="bot_seed_01",
                    text="Quán ruột của mình mỗi tuần đều ghé ăn lẩu bò xuất sắc luôn",
                    like_count=2,
                ),
                RawCommentInput(
                    comment_id="c2",
                    author_handle="bot_seed_02",
                    text="Quán ruột của mình mỗi tuần đều ghé ăn lẩu bò xuất sắc nha",
                    like_count=1,
                ),
                RawCommentInput(
                    comment_id="c3",
                    author_handle="khach_that_1",
                    text="Mới đi tối qua thất vọng thực sự, nước lẩu mặn chát mà bàn ghế bẩn đầy khói, nhân viên phục vụ quá chậm chờ 45 phút.",
                    like_count=86,
                ),
                RawCommentInput(
                    comment_id="c4",
                    author_handle="khach_that_2",
                    text="Thịt bò ít chứ không đầy đặn như clip quảng cáo lố đâu, giá tính thêm rau bún vô đắt nha.",
                    like_count=54,
                ),
            ],
        )
    ]


def _load_protected_corpus_ids(base_corpus_dir: Path) -> tuple[set[str], str]:
    snapshot_id = base_corpus_dir.name
    manifest_file = base_corpus_dir / "manifest.json"
    if manifest_file.is_file():
        data = json.loads(manifest_file.read_text(encoding="utf-8"))
        snapshot_id = str(data.get("snapshot_id") or snapshot_id)
    fact_path = base_corpus_dir / "fact_videos.parquet"
    if not fact_path.is_file():
        return set(), snapshot_id
    ids = set(pd.read_parquet(fact_path, columns=["video_id"])["video_id"].astype(str).tolist())
    return ids, snapshot_id


def _merge_creators(
    explicit_creators: list[str] | None,
    auto_creators: int,
    base_corpus_dir: Path,
    max_creators: int,
) -> list[str] | None:
    merged: list[str] = []
    seen: set[str] = set()
    for raw_c in explicit_creators or []:
        c = raw_c.lstrip("@").strip()
        if c and c.lower() not in seen:
            seen.add(c.lower())
            merged.append(c)
    if auto_creators > 0:
        for auto_c in select_curated_fnb_creators(base_corpus_dir, top_k=max(auto_creators, max_creators)):
            if auto_c.lower() not in seen:
                seen.add(auto_c.lower())
                merged.append(auto_c)
                if len(merged) >= max_creators:
                    break
    return merged[:max_creators] if merged else None


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Bounded 120-day incremental collector worker (never re-crawls historical Gold corpus)."
    )
    parser.add_argument(
        "--base-corpus",
        type=Path,
        default=Path("data/corpus/20261118_taxonomy_fix_v1"),
    )
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw_incremental/batch_latest"))
    parser.add_argument(
        "--window-days",
        type=int,
        default=120,
        help="Rolling operational window in days (default: 120 = 4 months).",
    )
    parser.add_argument(
        "--source",
        choices=("offline_fixture", "live_provider"),
        default=None,
        help="Explicit acquisition source: offline_fixture (synthetic/0 network) or live_provider.",
    )
    parser.add_argument(
        "--backend",
        choices=("auto", "tiktokapi", "ytdlp"),
        default="auto",
        help="Live provider backend when --source live_provider: auto (TikTokApi -> ytdlp fallback), tiktokapi, or ytdlp.",
    )
    parser.add_argument("--cookies-file", type=Path, default=None, help="Optional Netscape cookies.txt file for yt-dlp.")
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
    parser.add_argument("--fixture-path", type=Path, default=None, help="JSON/JSONL fixture file for --source offline_fixture.")
    parser.add_argument("--as-of", type=str, default=None, help="ISO-8601 reference timestamp for 120-day cutoff.")
    parser.add_argument("--creator", action="append", default=None, help="Creator handle(s) to discover (repeatable).")
    parser.add_argument(
        "--auto-creators",
        type=int,
        default=0,
        help="Auto-select up to K curated F&B creators from author_unique_ids.txt + dim_creators.parquet.",
    )
    parser.add_argument("--resume", action="store_true", help="Resume from collector_checkpoint.json in --output-dir.")
    parser.add_argument(
        "--allow-live-network",
        action="store_true",
        help="Explicit opt-in required for --source live_provider after Gate G2.",
    )
    parser.add_argument("--max-creators", type=int, default=5)
    parser.add_argument("--max-candidates", type=int, default=50)
    parser.add_argument("--max-succeeded", type=int, default=30)
    parser.add_argument("--max-audio-minutes", type=float, default=60.0)
    parser.add_argument("--max-comments-total", type=int, default=1000)
    parser.add_argument("--max-retries", type=int, default=2)
    parser.add_argument(
        "--seed-demo-batch",
        action="store_true",
        help="Write a deterministic 4-month synthetic sample batch for offline verification.",
    )
    args = parser.parse_args()

    load_dotenv_if_present()

    as_of_utc = (
        datetime.fromisoformat(args.as_of.replace("Z", "+00:00"))
        if args.as_of
        else datetime.now(UTC)
    )
    if as_of_utc.tzinfo is None:
        as_of_utc = as_of_utc.replace(tzinfo=UTC)

    cutoff = compute_cutoff_utc(reference_now=as_of_utc, window_days=args.window_days)
    existing_ids, snapshot_id = _load_protected_corpus_ids(args.base_corpus)

    bounds = CollectorBounds(
        window_days=args.window_days,
        max_creators=args.max_creators,
        max_candidate_videos=args.max_candidates,
        max_succeeded_videos=args.max_succeeded,
        max_audio_minutes=args.max_audio_minutes,
        max_comments_total=args.max_comments_total,
        max_retries=args.max_retries,
    )
    resolved_creators = _merge_creators(
        args.creator,
        args.auto_creators,
        args.base_corpus,
        bounds.max_creators,
    )

    if args.seed_demo_batch:
        seed_all = _build_seed_demo_records(as_of_utc)
        accepted = [r for r in seed_all if r.video_id not in existing_ids]
        out_file = write_incremental_batch(accepted, args.output_dir)
        seed_items = [
            CollectorItemReceipt(
                video_id=r.video_id,
                author_handle=r.author_handle,
                create_time=r.create_time,
                status="succeeded" if r.video_id not in existing_ids else "skipped",
                attempts=1 if r.video_id not in existing_ids else 0,
                reason="ok" if r.video_id not in existing_ids else "historical_protected_id",
                comment_count=len(r.comments),
            )
            for r in seed_all
        ]
        seed_manifest = CrawlManifest(
            source_mode="offline_fixture",
            is_synthetic_fixture=True,
            collector_backend_requested="offline_fixture",
            collector_backends_used=["offline_fixture"],
            as_of_utc=as_of_utc.isoformat(),
            cutoff_utc=cutoff.isoformat(),
            base_corpus_snapshot_id=snapshot_id,
            historical_protected_count=len(existing_ids),
            bounds=bounds,
            requested_count=len(seed_all),
            succeeded_count=len(accepted),
            failed_count=0,
            skipped_count=len(seed_all) - len(accepted),
            collected_comments_count=sum(len(r.comments) for r in accepted),
            output_jsonl=out_file.name,
            items=seed_items,
            timings_ms={"total_ms": 0.0},
        )
        _atomic_write_json(args.output_dir / "crawl_manifest.json", seed_manifest.model_dump())
        print(
            json.dumps(
                {
                    "status": "seeded_demo_batch",
                    "is_synthetic_fixture": True,
                    "cutoff_utc": cutoff.isoformat(),
                    "historical_skipped_pool": len(existing_ids),
                    "written_records": len(accepted),
                    "output_jsonl": str(out_file),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    if args.source == "offline_fixture":
        if args.fixture_path is None:
            raise ValueError("--fixture-path is required when --source offline_fixture is selected.")
        collector = BoundedIncrementalCollector(
            provider=OfflineFixtureCollectorProvider(args.fixture_path),
            audio_converter=OfflineFixtureAudioConverter(),
            bounds=bounds,
            sleep_fn=lambda _: None,
        )
        manifest = collector.run(
            output_dir=args.output_dir,
            as_of_utc=as_of_utc,
            historical_video_ids=existing_ids,
            base_corpus_snapshot_id=snapshot_id,
            creators=resolved_creators,
            resume=args.resume,
        )
        print(json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2))
        return

    if args.source == "live_provider":
        if not existing_ids:
            raise LiveNetworkDisabledError(
                f"Refusing live_provider execution without a populated historical --base-corpus protection set at {args.base_corpus}."
            )
        ms_tok = os.environ.get("MS_TOKEN", "")
        env_cookies = os.environ.get("TIKTOK_COOKIES_FILE", "").strip()
        cookies_path = args.cookies_file or (Path(env_cookies) if env_cookies else None)
        browser = args.tiktok_browser or os.environ.get("TIKTOK_BROWSER", "chromium").strip() or "chromium"
        if args.tiktok_headless is not None:
            headless = bool(args.tiktok_headless)
        else:
            headless = os.environ.get("TIKTOK_HEADLESS", "true").strip().lower() not in {"false", "0", "no"}

        live_provider = build_live_collector_provider(
            backend=cast(CollectorBackend, args.backend),
            allow_live_network=args.allow_live_network,
            ms_token=ms_tok,
            cookies_file=cookies_path,
            browser=browser,
            headless=headless,
            cutoff_utc=cutoff,
        )
        live_audio = YtDlpAudioConverter64k(
            allow_live_network=args.allow_live_network,
            ms_token=ms_tok,
            cookies_file=cookies_path,
        )
        collector = BoundedIncrementalCollector(
            provider=live_provider,
            audio_converter=live_audio,
            bounds=bounds,
        )
        manifest = collector.run(
            output_dir=args.output_dir,
            as_of_utc=as_of_utc,
            historical_video_ids=existing_ids,
            base_corpus_snapshot_id=snapshot_id,
            creators=resolved_creators,
            resume=args.resume,
        )
        print(json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2))
        return

    print(
        json.dumps(
            {
                "status": "idle_no_source_selected",
                "cutoff_utc": cutoff.isoformat(),
                "historical_protected_videos": len(existing_ids),
                "note": "Pass --source offline_fixture --fixture-path <file> for offline bounded worker verification, or --source live_provider --allow-live-network after Gate G2.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
