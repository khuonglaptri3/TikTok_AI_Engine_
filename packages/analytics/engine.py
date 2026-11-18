from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow.parquet as pq

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

    names = [entry.filename for entry in manifest.files]
    required = {"dim_creators.parquet", "fact_videos.parquet"}
    if not required.issubset(names) or len(names) != len(set(names)):
        raise CorpusNotReadyError("Manifest must cover each required corpus table exactly once")
    if any(Path(name).name != name or "\\" in name or "/" in name for name in names):
        raise CorpusNotReadyError("Manifest table names must be local filenames")
    for f_entry in manifest.files:
        file_path = corpus_dir / f_entry.filename
        if not file_path.is_file():
            raise CorpusNotReadyError(f"Corpus file missing: {file_path}")
        actual_sha = _sha256_file(file_path)
        if actual_sha != f_entry.sha256:
            raise CorpusNotReadyError(
                f"Checksum mismatch for {f_entry.filename}: expected {f_entry.sha256[:12]}, got {actual_sha[:12]}"
            )
        if f_entry.filename.endswith(".parquet"):
            try:
                meta = pq.read_metadata(file_path)
            except Exception as exc:
                raise CorpusNotReadyError(f"Unreadable Parquet file {f_entry.filename}: {exc}") from exc
            if meta.num_rows != f_entry.rows or meta.num_columns != f_entry.columns:
                raise CorpusNotReadyError(
                    f"Parquet shape mismatch for {f_entry.filename}: manifest=({f_entry.rows}, {f_entry.columns}), "
                    f"actual=({meta.num_rows}, {meta.num_columns})"
                )

    df_creators = pd.read_parquet(corpus_dir / "dim_creators.parquet")
    df_videos = pd.read_parquet(corpus_dir / "fact_videos.parquet")
    return manifest, df_creators, df_videos


def _derive_observation_snapshot(manifest: CorpusManifest) -> str:
    joined_caveats = " ".join(manifest.caveats).lower()
    if "mar-apr 2025" in joined_caveats or "march–april 2025" in joined_caveats:
        return f"2025-03/04 single-snapshot capture (manifest {manifest.created_at[:10]})"
    return f"manifest_{manifest.created_at[:10]}" if manifest.created_at else "unknown"


class NicheAnalyticsEngine:
    """In-process columnar analytics engine computing descriptive niche micro-benchmarks."""

    def __init__(
        self,
        manifest: CorpusManifest,
        df_creators: pd.DataFrame,
        df_videos: pd.DataFrame,
        min_slice_support: int = 5,
    ) -> None:
        self.manifest = manifest
        self.df_creators = df_creators
        self.df_videos = df_videos
        self._min_slice_support = max(1, min_slice_support)
        self._observation_snapshot = _derive_observation_snapshot(manifest)
        self._n_rows = len(df_videos)

        if self._n_rows > 0:
            self._plays = df_videos["play_count"].to_numpy(dtype=np.float64)
            self._er = df_videos["engagement_rate"].to_numpy(dtype=np.float64)
            self._durs = df_videos["duration_sec"].to_numpy(dtype=np.float64)
            self._h_counts = df_videos["hashtag_count"].to_numpy(dtype=np.float64)
            self._has_tr = df_videos["has_transcript"].to_numpy(dtype=bool)
            self._wps = df_videos["word_per_second"].to_numpy(dtype=np.float64)
            self._valid_wps_mask = self._has_tr & (self._wps > 0.2)
            self._hours = df_videos["create_hour"].fillna(0).to_numpy(dtype=np.int64)
            self._has_poi = df_videos["poi_name"].notna().to_numpy(dtype=bool)
            self._city_missing = (
                df_videos["city_norm"].isna().to_numpy(dtype=bool)
                if "city_norm" in df_videos.columns
                else np.ones(self._n_rows, dtype=bool)
            )
            self._price_unspec = (
                (df_videos["price_tier"].fillna("unspecified").astype(str).str.lower() == "unspecified").to_numpy()
                if "price_tier" in df_videos.columns
                else np.ones(self._n_rows, dtype=bool)
            )
            wps_global = self._wps[self._has_tr & (self._wps > 0.0)]
            self._global_median_wps = float(np.median(wps_global)) if len(wps_global) > 0 else 3.4
        else:
            self._plays = np.empty(0, dtype=np.float64)
            self._er = np.empty(0, dtype=np.float64)
            self._durs = np.empty(0, dtype=np.float64)
            self._h_counts = np.empty(0, dtype=np.float64)
            self._has_tr = np.empty(0, dtype=bool)
            self._wps = np.empty(0, dtype=np.float64)
            self._valid_wps_mask = np.empty(0, dtype=bool)
            self._hours = np.empty(0, dtype=np.int64)
            self._has_poi = np.empty(0, dtype=bool)
            self._city_missing = np.empty(0, dtype=bool)
            self._price_unspec = np.empty(0, dtype=bool)
            self._global_median_wps = 0.0

        # Pre-index normalized filter vectors for sub-250ms CPU aggregation
        self._col_lower: dict[str, np.ndarray] = {}
        for col in ("city_norm", "region", "price_tier", "duration_bucket"):
            if col in df_videos.columns and self._n_rows > 0:
                self._col_lower[col] = df_videos[col].fillna("").astype(str).str.lower().to_numpy()
            else:
                self._col_lower[col] = np.empty(0, dtype=object)

        self._col_exact: dict[str, np.ndarray] = {}
        for col in ("video_format", "food_category"):
            if col in df_videos.columns and self._n_rows > 0:
                self._col_exact[col] = df_videos[col].fillna("").astype(str).to_numpy()
            else:
                self._col_exact[col] = np.empty(0, dtype=object)

        self._occasion_masks: dict[str, np.ndarray] = {}
        if "occasions" in df_videos.columns and self._n_rows > 0:
            occ_positions: dict[str, list[int]] = {}
            for pos, arr in enumerate(df_videos["occasions"]):
                if arr is None:
                    continue
                for item in arr:
                    key = str(item).strip().lower()
                    if key:
                        occ_positions.setdefault(key, []).append(pos)
            for key, pos_list in occ_positions.items():
                mask = np.zeros(self._n_rows, dtype=bool)
                mask[pos_list] = True
                self._occasion_masks[key] = mask

        # Pre-index POI codes and flat hashtag postings for O(nnz) bincount aggregation
        if self._n_rows > 0 and "poi_name" in df_videos.columns:
            poi_codes_raw, poi_uniques = pd.factorize(df_videos["poi_name"], sort=False)
            self._poi_codes = poi_codes_raw.astype(np.int64)
            self._poi_names = [str(x) for x in poi_uniques]
        else:
            self._poi_codes = np.empty(0, dtype=np.int64)
            self._poi_names = []

        tag_vocab: dict[str, int] = {}
        tag_list: list[str] = []
        tag_is_generic: list[bool] = []
        tag_row_ids: list[int] = []
        tag_code_ids: list[int] = []
        if self._n_rows > 0 and "hashtags" in df_videos.columns:
            for row_idx, tag_arr in enumerate(df_videos["hashtags"]):
                if tag_arr is None:
                    continue
                for raw_t in tag_arr:
                    t = str(raw_t).strip().lower()
                    if not t:
                        continue
                    code = tag_vocab.get(t)
                    if code is None:
                        code = len(tag_list)
                        tag_vocab[t] = code
                        tag_list.append(t)
                        tag_is_generic.append(t in GENERIC_HASHTAGS)
                    tag_row_ids.append(row_idx)
                    tag_code_ids.append(code)
        self._tag_names = tag_list
        self._tag_is_generic = np.array(tag_is_generic, dtype=bool)
        self._tag_row_idx = np.array(tag_row_ids, dtype=np.int64)
        self._tag_code_idx = np.array(tag_code_ids, dtype=np.int64)

    @classmethod
    def from_corpus_dir(cls, corpus_dir: Path) -> NicheAnalyticsEngine:
        manifest, df_creators, df_videos = load_verified_corpus(corpus_dir)
        return cls(manifest=manifest, df_creators=df_creators, df_videos=df_videos)

    def _subset_mask(self, items: list[tuple[str, str]]) -> np.ndarray:
        mask = np.ones(self._n_rows, dtype=bool)
        if self._n_rows == 0:
            return mask
        for k, v in items:
            if k == "occasion":
                occ_mask = self._occasion_masks.get(v.lower())
                if occ_mask is None:
                    return np.zeros(self._n_rows, dtype=bool)
                mask &= occ_mask
            elif k in self._col_lower:
                mask &= self._col_lower[k] == v.lower()
            elif k in self._col_exact:
                mask &= self._col_exact[k] == v
        return mask

    def _apply_filters_mask(self, filters: NicheQueryFilter) -> tuple[np.ndarray, dict[str, str]]:
        if self._n_rows == 0:
            return np.zeros(0, dtype=bool), {}

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
            return np.ones(self._n_rows, dtype=bool), {}

        matched_mask = self._subset_mask(active)
        applied = {k: v for k, v in active}
        if bool(matched_mask.any()):
            return matched_mask, applied

        relax_order = [
            "duration_bucket",
            "occasion",
            "price_tier",
            "city_norm",
            "region",
            "food_category",
            "video_format",
        ]
        remaining = list(active)
        relaxed: list[str] = []
        for drop_key in relax_order:
            before_len = len(remaining)
            remaining = [(k, v) for k, v in remaining if k != drop_key]
            if len(remaining) < before_len:
                relaxed.append(drop_key)
                cand_mask = self._subset_mask(remaining)
                if bool(cand_mask.any()):
                    out_applied = {k: v for k, v in remaining}
                    out_applied["relaxed_filters"] = ",".join(relaxed)
                    return cand_mask, out_applied

        return np.ones(self._n_rows, dtype=bool), {"relaxed_filters": ",".join(relaxed)}

    def _top_hashtags(self, mask: np.ndarray) -> list[str]:
        if len(self._tag_row_idx) == 0:
            return []
        active_postings = mask[self._tag_row_idx]
        if not bool(active_postings.any()):
            return []
        counts = np.bincount(self._tag_code_idx[active_postings], minlength=len(self._tag_names))
        domain_counts = np.where(self._tag_is_generic, 0, counts)
        domain_nz = np.flatnonzero(domain_counts > 0)
        if len(domain_nz) > 0:
            top_d_idx = domain_nz[np.argsort(-domain_counts[domain_nz], kind="stable")[:8]]
            top_tags = [self._tag_names[int(i)] for i in top_d_idx]
        else:
            top_tags = []

        if len(top_tags) < 5:
            fallback_counts = np.where(self._tag_is_generic, counts, 0)
            fb_nz = np.flatnonzero(fallback_counts > 0)
            if len(fb_nz) > 0:
                top_f_idx = fb_nz[np.argsort(-fallback_counts[fb_nz], kind="stable")[: 5 - len(top_tags)]]
                top_tags.extend(self._tag_names[int(i)] for i in top_f_idx)
        return top_tags

    def _top_posting_hours(self, mask: np.ndarray, n_total: int) -> list[PostingHourStat]:
        min_hour_support = max(2, min(15, n_total // 40))
        sub_hours = self._hours[mask]
        sub_plays = self._plays[mask]
        sub_er = self._er[mask]
        hour_counts = np.bincount(np.clip(sub_hours, 0, 23), minlength=24)

        viable: list[tuple[int, int, float, float]] = []
        fallback_all: list[tuple[int, int, float, float]] = []
        for h in np.flatnonzero(hour_counts > 0):
            cnt = int(hour_counts[h])
            h_mask = sub_hours == h
            med_p = float(np.median(sub_plays[h_mask]))
            med_e = float(np.median(sub_er[h_mask]))
            entry = (int(h), cnt, med_p, med_e)
            fallback_all.append(entry)
            if cnt >= min_hour_support:
                viable.append(entry)

        chosen = viable if viable else fallback_all
        chosen.sort(key=lambda item: (item[2], item[1]), reverse=True)
        return [
            PostingHourStat(
                hour=h,
                video_count=cnt,
                median_plays=round(med_p, 1),
                median_engagement_rate=round(med_e, 5),
            )
            for h, cnt, med_p, med_e in chosen[:4]
        ]

    def _top_poi_venues(self, mask: np.ndarray) -> list[str]:
        if len(self._poi_names) == 0:
            return []
        active_poi = mask & (self._poi_codes >= 0)
        if not bool(active_poi.any()):
            return []
        sub_codes = self._poi_codes[active_poi]
        sub_plays = self._plays[active_poi]
        counts = np.bincount(sub_codes, minlength=len(self._poi_names))
        nz_codes = np.flatnonzero(counts > 0)
        if len(nz_codes) == 0:
            return []
        sorted_by_cnt = nz_codes[np.argsort(-counts[nz_codes], kind="stable")]
        kth_idx = min(5, len(sorted_by_cnt) - 1)
        min_cnt_for_top6 = int(counts[sorted_by_cnt[kth_idx]])
        candidates = sorted_by_cnt[counts[sorted_by_cnt] >= min_cnt_for_top6]
        ranked = [
            (int(counts[c]), float(np.median(sub_plays[sub_codes == c])), self._poi_names[int(c)])
            for c in candidates
        ]
        ranked.sort(key=lambda item: (item[0], item[1]), reverse=True)
        return [name for _, _, name in ranked[:6]]

    def compute_benchmark(self, filters: NicheQueryFilter | None = None) -> NicheBenchmarkSummary:
        timer = StageTimer()
        q_filters = filters or NicheQueryFilter()

        with timer.measure("filter_ms"):
            mask, applied_map = self._apply_filters_mask(q_filters)

        with timer.measure("aggregate_ms"):
            n_total = int(mask.sum())
            if n_total == 0:
                return NicheBenchmarkSummary(
                    matched_videos=0,
                    transcribed_videos=0,
                    poi_tagged_videos=0,
                    median_plays=0.0,
                    p75_plays=0.0,
                    median_engagement_rate=0.0,
                    duration_q25_sec=0.0,
                    duration_median_sec=0.0,
                    duration_q75_sec=0.0,
                    median_word_per_second=0.0,
                    hashtag_q25=0,
                    hashtag_q75=0,
                    top_hashtags=[],
                    top_posting_hours=[],
                    top_poi_venues=[],
                    applied_filters=applied_map,
                    timings_ms=timer.finalize(),
                    cohort_window_start=self.manifest.date_window_start,
                    cohort_window_end=self.manifest.date_window_end,
                    observation_snapshot=self._observation_snapshot,
                    sparse_slice_abstained=True,
                    missingness={},
                )

            n_transcribed = int(self._has_tr[mask].sum())
            n_poi = int(self._has_poi[mask].sum())
            n_city_missing = int(self._city_missing[mask].sum())
            n_price_unspec = int(self._price_unspec[mask].sum())
            missingness = {
                "transcript_missing_pct": round((n_total - n_transcribed) / n_total * 100.0, 2),
                "poi_missing_pct": round((n_total - n_poi) / n_total * 100.0, 2),
                "city_missing_pct": round(n_city_missing / n_total * 100.0, 2),
                "price_unspecified_pct": round(n_price_unspec / n_total * 100.0, 2),
            }

            plays = self._plays[mask]
            er = self._er[mask]
            durs = self._durs[mask]
            h_counts = self._h_counts[mask]

            wps_vals = self._wps[mask & self._valid_wps_mask]
            median_wps = float(np.median(wps_vals)) if len(wps_vals) >= 3 else self._global_median_wps

            top_tags = self._top_hashtags(mask)
            abstained = n_total < self._min_slice_support
            top_hours = [] if abstained else self._top_posting_hours(mask, n_total)
            top_pois = [] if abstained else self._top_poi_venues(mask)

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
            cohort_window_start=self.manifest.date_window_start,
            cohort_window_end=self.manifest.date_window_end,
            observation_snapshot=self._observation_snapshot,
            sparse_slice_abstained=abstained,
            missingness=missingness,
        )
