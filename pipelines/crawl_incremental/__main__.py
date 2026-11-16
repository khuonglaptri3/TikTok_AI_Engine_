from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from packages.data_contracts.multimodal import (
    RawCommentInput,
    RawIncrementalVideoRecord,
    RawWhisperSegment,
)
from pipelines.crawl_incremental.crawler_service import compute_cutoff_utc, write_incremental_batch


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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Crawl fresh 4-month TikTok F&B videos (never re-crawls historical 1.50 GB corpus)."
    )
    parser.add_argument("--base-corpus", type=Path, default=Path("data/corpus/20261116_v1"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/raw_incremental/batch_latest"))
    parser.add_argument("--window-days", type=int, default=120, help="Rolling window in days (default: 120 = 4 months).")
    parser.add_argument(
        "--seed-demo-batch",
        action="store_true",
        help="Write a deterministic 4-month multimodal sample batch for offline verification.",
    )
    args = parser.parse_args()

    cutoff = compute_cutoff_utc(window_days=args.window_days)
    existing_ids: set[str] = set()
    fact_path = args.base_corpus / "fact_videos.parquet"
    if fact_path.is_file():
        existing_ids = set(pd.read_parquet(fact_path, columns=["video_id"])["video_id"].astype(str).tolist())

    if args.seed_demo_batch:
        records = [
            r for r in _build_seed_demo_records(datetime.now(timezone.utc)) if r.video_id not in existing_ids
        ]
        out_file = write_incremental_batch(records, args.output_dir)
        print(
            json.dumps(
                {
                    "status": "seeded_demo_batch",
                    "cutoff_utc": cutoff.isoformat(),
                    "historical_skipped_pool": len(existing_ids),
                    "written_records": len(records),
                    "output_jsonl": str(out_file),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return

    print(
        json.dumps(
            {
                "status": "ready_for_live_crawl",
                "cutoff_utc": cutoff.isoformat(),
                "historical_protected_videos": len(existing_ids),
                "note": "Configure MS_TOKEN in .env and invoke TikTokApi + yt-dlp worker on host network, or pass --seed-demo-batch for offline pipeline testing.",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
