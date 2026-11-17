from __future__ import annotations

from pathlib import Path

import pandas as pd

from packages.common.settings import AppSettings

from packages.data_contracts.corpus import CorpusManifest
from packages.taxonomy import (
    classify_duration_bucket,
    extract_occasions,
    extract_price_tier,
    extract_script_anatomy,
    infer_video_format,
    map_food_category,
    resolve_location,
)
from pipelines.build_gold_corpus import compute_engagement_rate, compute_viral_multiplier


def test_poi_and_district_disambiguation_fixes_dish_name_hallucination() -> None:
    # Classic legacy bug: "Bún đậu Hà Nội ở Quận 7" had llm_city="hà nội", llm_district="quận 7"
    city, dist, region, source = resolve_location(
        poi_city=None,
        poi_address=None,
        llm_city="Hà Nội",
        llm_district="Quận 7",
    )
    assert city == "hồ chí minh"
    assert dist == "quận 7"
    assert region == "south"
    assert source == "district_resolved"

    # Official GPS POI always wins over noisy caption/LLM inference
    city2, dist2, region2, source2 = resolve_location(
        poi_city="Đà Nẵng",
        poi_address="123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng",
        llm_city="Hồ Chí Minh",
        llm_district=None,
    )
    assert city2 == "đà nẵng"
    assert region2 == "central"
    assert source2 == "poi_gps"


def test_taxonomy_extractors_and_zero_division_guards() -> None:
    assert compute_engagement_rate(0, 100, 10, 5, 5) == 0.0
    assert compute_engagement_rate(1000, 80, 10, 5, 5) == 0.1
    assert compute_viral_multiplier(0, 50_000) == 0.0
    assert compute_viral_multiplier(250_000, 50_000) == 5.0
    # Floor baseline of 1000 prevents division by zero for brand-new creators
    assert compute_viral_multiplier(5_000, 0) == 5.0

    assert classify_duration_bucket(15) == "ultra_short_lt20s"
    assert classify_duration_bucket(40) == "short_20_45s"
    assert classify_duration_bucket(75) == "medium_45_90s"
    assert classify_duration_bucket(120) == "long_gt90s"

    fmt = infer_video_format(
        legacy_cat=None,
        desc="Quán ốc sinh viên 35k núp hẻm Bình Thạnh ngon xỉu",
        transcript="Hôm nay dẫn mọi người đi ăn ốc 35 cành mở tới 2h sáng nha.",
        poi_name="Ốc Đêm Bình Thạnh",
        is_ec_video=False,
    )
    assert fmt == "Review quán ăn"
    assert extract_price_tier("ốc 35k sinh viên bình dân", fmt) == "budget_lt50k"
    assert "an_dem" in extract_occasions("mở tới 2h sáng cho cú đêm", fmt)
    assert map_food_category(["ốc"], "quán ốc sinh viên", None) == "Ăn vặt & Đường phố"

    hook, beats, cta = extract_script_anatomy(
        "Quán ốc 35k giữa lòng Bình Thạnh bạn đã thử chưa? Món đầu tiên là ốc hương xào bơ tỏi thơm lừng. "
        "Nước chấm sả tắc chua ngọt cực cuốn. Lưu ngay địa chỉ để cuối tuần rủ hội bạn đi ăn nha!",
    )
    assert "35k" in hook
    assert len(beats) >= 1
    assert "địa chỉ" in cta


def test_built_gold_corpus_snapshot_integrity() -> None:
    corpus_dir = AppSettings().corpus_dir
    manifest_path = corpus_dir / "manifest.json"
    assert manifest_path.is_file(), "Gold corpus manifest.json must exist"

    manifest = CorpusManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    assert manifest.total_creators == 264
    assert manifest.total_videos == 70996
    assert manifest.transcribed_videos >= 21500
    assert manifest.poi_tagged_videos == 23448
    assert manifest.ec_tagged_videos == 5798

    df_creators = pd.read_parquet(corpus_dir / "dim_creators.parquet")
    df_videos = pd.read_parquet(corpus_dir / "fact_videos.parquet", columns=[
        "video_id", "engagement_rate", "viral_multiplier", "video_format", "food_category", "has_transcript"
    ])
    assert len(df_creators) == 264
    assert len(df_videos) == 70996
    assert df_videos["video_id"].nunique() == 70996
    assert (df_videos["engagement_rate"] >= 0.0).all()
    assert (df_videos["viral_multiplier"] >= 0.0).all()
