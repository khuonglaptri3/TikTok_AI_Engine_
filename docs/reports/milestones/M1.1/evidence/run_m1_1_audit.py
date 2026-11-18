#!/usr/bin/env python3
"""Reproducible M1.1 field lineage, coverage, anomaly, and 120-record stratified sample generator."""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[5]
CORPUS_DIR = ROOT / "data" / "corpus" / "20261117_recovered_v1"
OUT_DIR = Path(__file__).resolve().parent

VIDEO_FIELD_LINEAGE: dict[str, str] = {
    "video_id": "cleaned_video_info.parquet (video.id)",
    "author_id": "cleaned_video_info.parquet (author.id)",
    "author_handle": "cleaned_video_info.parquet (author.uniqueId)",
    "author_nickname": "cleaned_video_info.parquet (author.nickname)",
    "tiktok_url": "derived from author_handle + video_id",
    "follower_count": "cleaned_video_info.parquet (authorStats.followerCount)",
    "follower_tier": "derived via classify_follower_tier(follower_count) / dim_creators",
    "create_time": "cleaned_video_info.parquet (createTime)",
    "create_hour": "derived from create_time.hour",
    "year_week": "cleaned_video_info.parquet (year_week)",
    "play_count": "cleaned_video_info.parquet (statsV2.playCount)",
    "digg_count": "cleaned_video_info.parquet (statsV2.diggCount)",
    "comment_count": "cleaned_video_info.parquet (statsV2.commentCount)",
    "share_count": "cleaned_video_info.parquet (statsV2.shareCount)",
    "collect_count": "cleaned_video_info.parquet (statsV2.collectCount)",
    "engagement_rate": "derived via compute_engagement_rate (0.0 when play_count==0)",
    "viral_multiplier": "derived via compute_viral_multiplier (floor baseline 1000.0)",
    "is_ad": "cleaned_video_info.parquet (isAd; platform disclosure flag)",
    "is_ec_video": "final_raw_videos.csv (isECVideo; platform TikTok Shop flag)",
    "playlist_id": "final_raw_videos.csv (playlistId; '0' normalized to None)",
    "duration_sec": "cleaned_video_info.parquet (video.duration)",
    "duration_bucket": "derived via classify_duration_bucket(duration_sec)",
    "caption": "cleaned_video_info.parquet (desc)",
    "hashtags": "cleaned_video_info.parquet (hashtags)",
    "hashtag_count": "derived len(hashtags)",
    "has_transcript": "derived bool(transcript) after refusal/length filter",
    "transcript": "data/transcripts/*.json -> fallback content_analysis/final_location_food_data",
    "word_count": "derived len(transcript.split()) when has_transcript",
    "word_per_second": "derived word_count / duration_sec (0.0 when duration_sec==0)",
    "has_cta": "transcript JSON / content_analysis / final_location_food_data",
    "has_curiosity_gap": "transcript JSON / final_location_food_data",
    "poi_id": "final_raw_videos.csv (poi.id)",
    "poi_name": "final_raw_videos.csv (poi.name)",
    "poi_address": "final_raw_videos.csv (poi.address)",
    "poi_city": "final_raw_videos.csv (poi.city)",
    "poi_category_tiny": "final_raw_videos.csv (poi.ttTypeNameTiny)",
    "city_norm": "derived via resolve_location(poi_city, poi_address, llm_city, llm_district)",
    "district_norm": "derived via resolve_location(poi_city, poi_address, llm_city, llm_district)",
    "region": "derived via CITY_TO_REGION[city_norm] or district fallback",
    "location_source": "derived provenance tag (poi_gps | district_resolved | llm_inferred | unknown)",
    "video_format": "content_analysis.categories -> fallback infer_video_format",
    "food_category": "derived via map_food_category(dishes, combined_text, poi_category_tiny)",
    "dishes": "final_location_food_data.foods + extract_dishes_from_text(combined_text)",
    "price_tier": "derived via extract_price_tier(combined_text, video_format)",
    "occasions": "derived via extract_occasions(combined_text, video_format)",
    "hook_text": "content_analysis.hook_content -> fallback extract_script_anatomy",
    "body_beats": "content_analysis.body_analysis / takeaways -> fallback extract_script_anatomy",
    "cta_text": "content_analysis.cta_content -> fallback extract_script_anatomy",
    "rag_document": "derived formatted string when has_transcript else ''",
}

CREATOR_FIELD_LINEAGE: dict[str, str] = {
    "author_id": "cleaned_user_info.parquet (user.id)",
    "unique_id": "cleaned_user_info.parquet (user.uniqueId)",
    "nickname": "cleaned_user_info.parquet (user.nickname)",
    "verified": "cleaned_user_info.parquet (user.verified)",
    "commerce_user": "cleaned_user_info.parquet (user.commerceUserInfo.commerceUser)",
    "tt_seller": "cleaned_user_info.parquet (user.ttSeller)",
    "follower_count": "cleaned_user_info.parquet (stats.followerCount)",
    "follower_tier": "derived via classify_follower_tier(follower_count)",
    "heart_count": "cleaned_user_info.parquet (stats.heartCount)",
    "lifetime_video_count": "cleaned_user_info.parquet (stats.videoCount)",
    "sample_video_count": "aggregated count from cleaned_video_info.parquet",
    "median_play_count": "aggregated median playCount from cleaned_video_info.parquet",
    "median_engagement_rate": "aggregated median engagement_rate from cleaned_video_info.parquet",
    "median_duration_sec": "aggregated median duration_sec from cleaned_video_info.parquet",
    "avg_videos_per_week": "cleaned_user_info.parquet (avg_videos_per_week)",
}


def _series_coverage(series: pd.Series, total: int) -> dict[str, Any]:
    non_null = int(series.notna().sum())
    non_empty = 0
    unknown_count = 0
    for val in series:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            unknown_count += 1
            continue
        if isinstance(val, (list, tuple, np.ndarray)):
            if len(val) > 0:
                non_empty += 1
            else:
                unknown_count += 1
        elif isinstance(val, str):
            s = val.strip()
            if s:
                non_empty += 1
            if not s or s.lower() in {"unknown", "unspecified"}:
                unknown_count += 1
        else:
            non_empty += 1

    return {
        "non_null_count": non_null,
        "non_null_pct": round(non_null / total * 100, 2),
        "non_empty_count": non_empty,
        "non_empty_pct": round(non_empty / total * 100, 2),
        "unknown_or_empty_count": unknown_count,
        "unknown_or_empty_pct": round(unknown_count / total * 100, 2),
    }


def main() -> None:
    df_c = pd.read_parquet(CORPUS_DIR / "dim_creators.parquet")
    df_v = pd.read_parquet(CORPUS_DIR / "fact_videos.parquet")
    n_videos = len(df_v)
    n_creators = len(df_c)

    # 1. Per-field lineage & coverage
    video_rows: list[dict[str, Any]] = []
    for col in df_v.columns:
        cov = _series_coverage(df_v[col], n_videos)
        video_rows.append(
            {
                "table": "fact_videos",
                "column": col,
                "dtype": str(df_v[col].dtype),
                "source_lineage": VIDEO_FIELD_LINEAGE.get(col, "unmapped"),
                **cov,
            }
        )

    creator_rows: list[dict[str, Any]] = []
    for col in df_c.columns:
        cov = _series_coverage(df_c[col], n_creators)
        creator_rows.append(
            {
                "table": "dim_creators",
                "column": col,
                "dtype": str(df_c[col].dtype),
                "source_lineage": CREATOR_FIELD_LINEAGE.get(col, "unmapped"),
                **cov,
            }
        )

    pd.DataFrame([*video_rows, *creator_rows]).to_csv(OUT_DIR / "field_coverage.csv", index=False)

    # 2. Audit metrics & anomalies
    has_oc = df_v[df_v["dishes"].apply(lambda a: "ốc" in a if a is not None else False)]
    real_oc = int(
        has_oc.apply(
            lambda r: bool(
                re.search(
                    r"(?<!\w)ốc(?!\w)",
                    f"{r['caption']} {' '.join(r['hashtags']) if r['hashtags'] is not None else ''} {r['poi_name'] or ''} {str(r['transcript'])[:800]}",
                    flags=re.IGNORECASE,
                )
            ),
            axis=1,
        ).sum()
    )

    unmapped_region_cities = (
        df_v.loc[df_v["city_norm"].notna() & (df_v["region"] == "unknown"), "city_norm"]
        .value_counts()
        .head(20)
        .to_dict()
    )
    poi_without_city = int((df_v["poi_name"].notna() & df_v["city_norm"].isna()).sum())

    occ_counter = Counter(o for arr in df_v["occasions"] if arr is not None for o in arr)
    dish_counter = Counter(d for arr in df_v["dishes"] if arr is not None for d in arr)

    summary = {
        "snapshot_id": "20261117_recovered_v1",
        "total_creators": n_creators,
        "total_videos": n_videos,
        "distributions": {
            "location_source": {str(k): int(v) for k, v in df_v["location_source"].value_counts(dropna=False).items()},
            "region": {str(k): int(v) for k, v in df_v["region"].value_counts(dropna=False).items()},
            "video_format": {str(k): int(v) for k, v in df_v["video_format"].value_counts(dropna=False).items()},
            "food_category": {str(k): int(v) for k, v in df_v["food_category"].value_counts(dropna=False).items()},
            "price_tier": {str(k): int(v) for k, v in df_v["price_tier"].value_counts(dropna=False).items()},
            "duration_bucket": {str(k): int(v) for k, v in df_v["duration_bucket"].value_counts(dropna=False).items()},
            "occasions_counts": dict(occ_counter.most_common()),
            "top_15_dishes": dict(dish_counter.most_common(15)),
        },
        "safe_ratios_and_numeric_invariants": {
            "duration_sec_zero": int((df_v["duration_sec"] == 0).sum()),
            "play_count_zero": int((df_v["play_count"] == 0).sum()),
            "er_nonzero_when_plays_zero": int(((df_v["play_count"] == 0) & (df_v["engagement_rate"] != 0)).sum()),
            "wps_nonzero_when_duration_zero": int(((df_v["duration_sec"] == 0) & (df_v["word_per_second"] != 0)).sum()),
            "wps_gt_10_outliers": int((df_v["word_per_second"] > 10.0).sum()),
            "nan_counts": {
                "engagement_rate": int(df_v["engagement_rate"].isna().sum()),
                "viral_multiplier": int(df_v["viral_multiplier"].isna().sum()),
                "word_per_second": int(df_v["word_per_second"].isna().sum()),
            },
        },
        "discovered_taxonomy_bugs_in_20261117_recovered_v1": {
            "poi_name_present_but_city_norm_null": poi_without_city,
            "city_norm_present_but_region_unknown": int((df_v["city_norm"].notna() & (df_v["region"] == "unknown")).sum()),
            "top_unmapped_region_city_norm": {str(k): int(v) for k, v in unmapped_region_cities.items()},
            "dish_oc_total_tagged": int(len(has_oc)),
            "dish_oc_word_boundary_true": real_oc,
            "dish_oc_false_substring_matches": int(len(has_oc) - real_oc),
            "occasions_an_vat_xe_chieu_count": int(occ_counter.get("an_vat_xe_chieu", 0)),
        },
        "video_fields": video_rows,
        "creator_fields": creator_rows,
    }
    (OUT_DIR / "field_lineage_and_coverage.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    # 3. Deterministic stratified 120-record sample across city_bucket x food_category x has_transcript
    def _city_bucket(val: Any) -> str:
        if val is None or (isinstance(val, float) and math.isnan(val)):
            return "unknown"
        s = str(val).strip().lower()
        if s == "hồ chí minh":
            return "hcm"
        if s == "hà nội":
            return "hanoi"
        return "other_city"

    work = df_v.copy()
    work["city_bucket"] = work["city_norm"].apply(_city_bucket)
    work["stratum"] = work["city_bucket"] + "|" + work["food_category"].astype(str) + "|" + work["has_transcript"].astype(str)

    rng = np.random.default_rng(20261118)
    strata_counts = work["stratum"].value_counts()
    total = len(work)
    raw_alloc = (strata_counts / total) * 120.0
    alloc = raw_alloc.astype(int)
    # Ensure non-empty major strata get representation and sum == 120
    rem = 120 - int(alloc.sum())
    remainders = (raw_alloc - alloc).sort_values(ascending=False)
    for key in remainders.index[:rem]:
        alloc[key] += 1

    sampled_parts: list[pd.DataFrame] = []
    for stratum_key, n_take in alloc.items():
        if n_take <= 0:
            continue
        pool = work[work["stratum"] == stratum_key]
        chosen_idx = rng.choice(pool.index.to_numpy(), size=min(int(n_take), len(pool)), replace=False)
        sampled_parts.append(pool.loc[chosen_idx])

    sample_df = pd.concat(sampled_parts, ignore_index=True)
    # Shuffle deterministically and split 30 shared (K+N) + 90 N_primary
    perm = rng.permutation(len(sample_df))
    sample_df = sample_df.iloc[perm].reset_index(drop=True)
    sample_df["sample_no"] = range(1, len(sample_df) + 1)
    sample_df["annotator_split"] = ["shared_K_N" if i < 30 else "N_primary" for i in range(len(sample_df))]

    export_cols = [
        "sample_no",
        "annotator_split",
        "city_bucket",
        "stratum",
        "video_id",
        "author_handle",
        "tiktok_url",
        "duration_sec",
        "has_transcript",
        "poi_name",
        "poi_address",
        "poi_city",
        "caption",
        "transcript",
        "city_norm",
        "district_norm",
        "region",
        "location_source",
        "video_format",
        "food_category",
        "dishes",
        "price_tier",
        "occasions",
        "hook_text",
        "cta_text",
    ]
    out_sample = sample_df[export_cols].copy()
    out_sample["transcript_excerpt"] = out_sample["transcript"].fillna("").str.slice(0, 400)
    out_sample = out_sample.drop(columns=["transcript"])
    for list_col in ("dishes",):
        out_sample[list_col] = out_sample[list_col].apply(
            lambda x: "|".join(str(i) for i in x) if x is not None else ""
        )
    out_sample["occasions"] = sample_df["occasions"].apply(
        lambda x: "|".join(str(i) for i in x) if x is not None else ""
    )

    # Blank annotation columns for human review (never fabricated)
    for col in (
        "N_city_correct",
        "N_city_expected",
        "N_format_correct",
        "N_category_correct",
        "N_dishes_false_positive",
        "N_price_correct",
        "N_occasion_correct",
        "N_anatomy_usable",
        "N_notes",
        "K_city_correct",
        "K_format_correct",
        "K_category_correct",
        "K_dishes_false_positive",
        "K_notes",
    ):
        out_sample[col] = ""

    out_sample.to_csv(OUT_DIR / "audit_sample_120.csv", index=False)
    print(f"Generated field_coverage.csv, field_lineage_and_coverage.json, and audit_sample_120.csv ({len(out_sample)} rows)")


if __name__ == "__main__":
    main()
