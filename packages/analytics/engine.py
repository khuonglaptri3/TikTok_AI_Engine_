from __future__ import annotations

import hashlib
from collections import Counter
from pathlib import Path

import numpy as np
import pandas as pd

from packages.common.exceptions import CorpusNotReadyError
from packages.common.logging import StageTimer
from packages.data_contracts.analytics import NicheBenchmarkSummary, PostingHourStat
from packages.data_contracts.corpus import CorpusManifest
from packages.data_contracts.query import NicheQueryFilter

GENERIC_HASHTAGS: frozenset[str] = frozenset(
    {
        "fyp",
        "fypシ",
        "foryou",
        "foryoupage",
        "foru",
        "xuhuong",
        "xuhuongtiktok",
        "viral",
        "viraltiktok",
        "trending",
        "tiktok",
        "tiktokvn",
        "xh",
    }
)


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def load_verified_corpus(corpus_dir: Path) -> tuple[CorpusManifest, pd.DataFrame, pd.DataFrame]:
    """Verify manifest.json SHA256 checksums before loading Parquet tables (fail-closed)."""
    manifest_path = corpus_dir / "manifest.json"
    if not manifest_path.is_file():
        raise CorpusNotReadyError(f"Corpus manifest missing at {manifest_path}")

    try:
        manifest = CorpusManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CorpusNotReadyError(f"Invalid corpus manifest at {manifest_path}: {exc}") from exc

    for f_entry in manifest.files:
        file_path = corpus_dir / f_entry.filename
        if not file_path.is_file():
            raise CorpusNotReadyError(f"Corpus file missing: {file_path}")
        actual_sha = _sha256_file(file_path)
        if actual_sha != f_entry.sha256:
            raise CorpusNotReadyError(
                f"Checksum mismatch for {f_entry.filename}: expected {f_entry.sha256[:12]}, got {actual_sha[:12]}"
            )

    df_creators = pd.read_parquet(corpus_dir / "dim_creators.parquet")
    df_videos = pd.read_parquet(corpus_dir / "fact_videos.parquet")
    return manifest, df_creators, df_videos


class NicheAnalyticsEngine:
    """In-process columnar analytics engine computing empirical niche micro-benchmarks."""

    def __init__(self, manifest: CorpusManifest, df_creators: pd.DataFrame, df_videos: pd.DataFrame) -> None:
        self.manifest = manifest
        self.df_creators = df_creators
        self.df_videos = df_videos
        wps_series = df_videos.loc[df_videos["has_transcript"] & (df_videos["word_per_second"] > 0), "word_per_second"]
        self._global_median_wps = float(wps_series.median()) if len(wps_series) > 0 else 3.4

    @classmethod
    def from_corpus_dir(cls, corpus_dir: Path) -> NicheAnalyticsEngine:
        manifest, df_creators, df_videos = load_verified_corpus(corpus_dir)
        return cls(manifest=manifest, df_creators=df_creators, df_videos=df_videos)

    def _apply_filters(self, df: pd.DataFrame, filters: NicheQueryFilter) -> tuple[pd.DataFrame, dict[str, str]]:
        active: list[tuple[str, str]] = []
        for field in (
            "video_format",
            "food_category",
            "city_norm",
            "region",
            "price_tier",
            "occasion",
            "duration_bucket",
        ):
            val = getattr(filters, field)
            if val:
                active.append((field, str(val).strip()))

        if not active:
            return df, {}

        def _subset(items: list[tuple[str, str]]) -> pd.DataFrame:
            mask = pd.Series(True, index=df.index)
            for k, v in items:
                if k == "occasion":
                    v_low = v.lower()
                    mask &= df["occasions"].apply(
                        lambda arr: v_low in [str(x).lower() for x in arr] if arr is not None else False
                    )
                elif k in ("city_norm", "region", "price_tier", "duration_bucket"):
                    mask &= df[k].fillna("").str.lower() == v.lower()
                else:
                    mask &= df[k].fillna("") == v
            return df.loc[mask]

        matched = _subset(active)
        applied = {k: v for k, v in active}
        if len(matched) > 0:
            return matched, applied

        # Progressive relaxation from least structural to core format/category
        relax_order = ["duration_bucket", "occasion", "price_tier", "city_norm", "region", "food_category", "video_format"]
        remaining = list(active)
        relaxed: list[str] = []
        for drop_key in relax_order:
            before_len = len(remaining)
            remaining = [(k, v) for k, v in remaining if k != drop_key]
            if len(remaining) < before_len:
                relaxed.append(drop_key)
                candidate = _subset(remaining)
                if len(candidate) > 0:
                    out_applied = {k: v for k, v in remaining}
                    out_applied["relaxed_filters"] = ",".join(relaxed)
                    return candidate, out_applied

        return df, {"relaxed_filters": ",".join(relaxed)}

    def compute_benchmark(self, filters: NicheQueryFilter | None = None) -> NicheBenchmarkSummary:
        timer = StageTimer()
        q_filters = filters or NicheQueryFilter()

        with timer.measure("filter_ms"):
            sub, applied_map = self._apply_filters(self.df_videos, q_filters)

        with timer.measure("aggregate_ms"):
            n_total = len(sub)
            if n_total == 0:
                return NicheBenchmarkSummary(
                    matched_videos=0,
                    transcribed_videos=0,
                    poi_tagged_videos=0,
                    median_plays=0.0,
                    p75_plays=0.0,
                    median_engagement_rate=0.0,
                    duration_q25_sec=25.0,
                    duration_median_sec=45.0,
                    duration_q75_sec=75.0,
                    median_word_per_second=round(self._global_median_wps, 2),
                    hashtag_q25=3,
                    hashtag_q75=7,
                    top_hashtags=[],
                    top_posting_hours=[],
                    top_poi_venues=[],
                    applied_filters=applied_map,
                    timings_ms=timer.finalize(),
                )

            n_transcribed = int(sub["has_transcript"].sum())
            n_poi = int(sub["poi_name"].notna().sum())

            plays = sub["play_count"].to_numpy(dtype=np.float64)
            er = sub["engagement_rate"].to_numpy(dtype=np.float64)
            durs = sub["duration_sec"].to_numpy(dtype=np.float64)
            h_counts = sub["hashtag_count"].to_numpy(dtype=np.float64)

            wps_sub = sub.loc[sub["has_transcript"] & (sub["word_per_second"] > 0.2), "word_per_second"]
            median_wps = float(wps_sub.median()) if len(wps_sub) >= 3 else self._global_median_wps

            # Top domain hashtags
            domain_tags: Counter[str] = Counter()
            fallback_tags: Counter[str] = Counter()
            for tag_arr in sub["hashtags"]:
                if tag_arr is None:
                    continue
                for raw_t in tag_arr:
                    t = str(raw_t).strip().lower()
                    if not t:
                        continue
                    if t in GENERIC_HASHTAGS:
                        fallback_tags[t] += 1
                    else:
                        domain_tags[t] += 1
            top_tags = [t for t, _ in domain_tags.most_common(8)]
            if len(top_tags) < 5:
                top_tags.extend([t for t, _ in fallback_tags.most_common(5 - len(top_tags))])

            # Top posting hours sorted by median plays (with minimum support)
            min_hour_support = max(2, min(15, n_total // 40))
            hour_grp = (
                sub.groupby("create_hour", dropna=False)
                .agg(
                    video_count=("video_id", "count"),
                    median_plays=("play_count", "median"),
                    median_er=("engagement_rate", "median"),
                )
                .reset_index()
            )
            viable_hours = hour_grp[hour_grp["video_count"] >= min_hour_support]
            if len(viable_hours) == 0:
                viable_hours = hour_grp
            viable_hours = viable_hours.sort_values(by=["median_plays", "video_count"], ascending=[False, False]).head(4)

            top_hours = [
                PostingHourStat(
                    hour=int(r["create_hour"]),
                    video_count=int(r["video_count"]),
                    median_plays=round(float(r["median_plays"]), 1),
                    median_engagement_rate=round(float(r["median_er"]), 5),
                )
                for r in viable_hours.to_dict(orient="records")
            ]

            # Top POI venues in slice
            poi_sub = sub.dropna(subset=["poi_name"])
            top_pois: list[str] = []
            if len(poi_sub) > 0:
                poi_grp = (
                    poi_sub.groupby("poi_name")
                    .agg(cnt=("video_id", "count"), med_plays=("play_count", "median"))
                    .sort_values(by=["cnt", "med_plays"], ascending=[False, False])
                    .head(6)
                )
                top_pois = [str(idx) for idx in poi_grp.index]

        timings = timer.finalize()
        return NicheBenchmarkSummary(
            matched_videos=n_total,
            transcribed_videos=n_transcribed,
            poi_tagged_videos=n_poi,
            median_plays=round(float(np.median(plays)), 1),
            p75_plays=round(float(np.percentile(plays, 75)), 1),
            median_engagement_rate=round(float(np.median(er)), 5),
            duration_q25_sec=round(float(np.percentile(durs, 25)), 1),
            duration_median_sec=round(float(np.median(durs)), 1),
            duration_q75_sec=round(float(np.percentile(durs, 75)), 1),
            median_word_per_second=round(median_wps, 2),
            hashtag_q25=int(round(float(np.percentile(h_counts, 25)))),
            hashtag_q75=int(round(float(np.percentile(h_counts, 75)))),
            top_hashtags=top_tags,
            top_posting_hours=top_hours,
            top_poi_venues=top_pois,
            applied_filters=applied_map,
            timings_ms=timings,
        )
