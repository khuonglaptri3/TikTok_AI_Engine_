from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from packages.absa import analyze_koc_vs_viewer_absa
from packages.analytics import load_verified_corpus
from packages.common.snapshots import snapshot_workspace
from packages.data_contracts.corpus import CorpusFileChecksum, CorpusManifest
from packages.data_contracts.multimodal import (
    RawCommentInput,
    RawIncrementalVideoRecord,
    VoiceSegmentRecord,
)
from packages.seeding import detect_seeding_comments
from packages.taxonomy import (
    classify_duration_bucket,
    extract_dishes_from_text,
    extract_occasions,
    extract_price_tier,
    extract_script_anatomy,
    infer_video_format,
    map_food_category,
    resolve_location,
    resolve_location_from_caption,
)
from pipelines.build_gold_corpus.builder import (
    classify_follower_tier,
    compute_engagement_rate,
    compute_viral_multiplier,
)

SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+|\n+")

_VOICE_SEGMENTS_SCHEMA = pa.schema(
    [
        ("segment_id", pa.string()),
        ("video_id", pa.string()),
        ("seq_no", pa.int64()),
        ("start_sec", pa.float64()),
        ("end_sec", pa.float64()),
        ("timestamp_source", pa.string()),
        ("text", pa.string()),
        ("words_per_sec", pa.float64()),
        ("pitch_std", pa.float64()),
        ("energy_cv", pa.float64()),
    ]
)

_COMMENTS_SCHEMA = pa.schema(
    [
        ("comment_id", pa.string()),
        ("video_id", pa.string()),
        ("author_handle", pa.string()),
        ("text", pa.string()),
        ("like_count", pa.int64()),
        ("reply_count", pa.int64()),
        ("is_seeding", pa.bool_()),
        ("seeding_reason", pa.string()),
        ("similarity_score", pa.float64()),
        ("cluster_id", pa.int64()),
    ]
)

_ABSA_REVIEWS_SCHEMA = pa.schema(
    [
        ("video_id", pa.string()),
        ("koc_taste", pa.float64()),
        ("koc_price", pa.float64()),
        ("koc_hygiene", pa.float64()),
        ("koc_service", pa.float64()),
        ("viewer_taste", pa.float64()),
        ("viewer_price", pa.float64()),
        ("viewer_hygiene", pa.float64()),
        ("viewer_service", pa.float64()),
        ("pr_hype_gap", pa.float64()),
        ("undisclosed_pr_risk", pa.float64()),
        ("viewer_pain_points", pa.list_(pa.string())),
        ("clean_comment_count", pa.int64()),
        ("seeding_comment_count", pa.int64()),
    ]
)

_NON_OPTIONAL_STRING_DEFAULTS: dict[str, str] = {
    "author_nickname": "",
    "caption": "",
}
_NON_OPTIONAL_INT_DEFAULTS: dict[str, int] = {
    "follower_count": 0,
    "duration_sec": 0,
    "play_count": 0,
    "digg_count": 0,
    "comment_count": 0,
    "share_count": 0,
    "collect_count": 0,
}
_NON_OPTIONAL_BOOL_DEFAULTS: dict[str, bool] = {
    "is_ad": False,
    "is_ec_video": False,
}


def _normalize_scalar(value: Any) -> Any:
    if value is None or value is pd.NA:
        return None
    if isinstance(value, (float, np.floating)) and np.isnan(value):
        return None
    if isinstance(value, np.generic):
        return value.item()
    return value


def _normalize_preserved_row(old_row: dict[str, Any], excluded: set[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key in RawIncrementalVideoRecord.model_fields:
        if key in excluded or key not in old_row:
            continue
        raw_val = old_row[key]
        if key == "hashtags":
            if isinstance(raw_val, np.ndarray):
                out[key] = [str(x) for x in raw_val.tolist()]
            elif isinstance(raw_val, (list, tuple)):
                out[key] = [str(x) for x in raw_val]
            else:
                out[key] = []
            continue
        val = _normalize_scalar(raw_val)
        if val is None:
            if key in _NON_OPTIONAL_STRING_DEFAULTS:
                val = _NON_OPTIONAL_STRING_DEFAULTS[key]
            elif key in _NON_OPTIONAL_INT_DEFAULTS:
                val = _NON_OPTIONAL_INT_DEFAULTS[key]
            elif key in _NON_OPTIONAL_BOOL_DEFAULTS:
                val = _NON_OPTIONAL_BOOL_DEFAULTS[key]
        out[key] = val
    return out


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def _merge_comments(previous: list[RawCommentInput], incoming: list[RawCommentInput]) -> list[RawCommentInput]:
    merged: dict[str, RawCommentInput] = {}
    for comment in [*previous, *incoming]:
        old = merged.get(comment.comment_id)
        merged[comment.comment_id] = (
            old.model_copy(update=comment.model_dump(exclude_unset=True)) if old is not None else comment
        )
    return list(merged.values())


def _build_voice_segments(rec: RawIncrementalVideoRecord, wps: float) -> list[VoiceSegmentRecord]:
    if rec.whisper_segments:
        out: list[VoiceSegmentRecord] = []
        for idx, seg in enumerate(rec.whisper_segments):
            dur = max(0.5, seg.end_sec - seg.start_sec)
            wc = len(seg.text.split())
            out.append(
                VoiceSegmentRecord(
                    segment_id=f"{rec.video_id}_s{idx:03d}",
                    video_id=rec.video_id,
                    seq_no=idx,
                    start_sec=round(seg.start_sec, 2),
                    end_sec=round(seg.end_sec, 2),
                    timestamp_source="whisper_exact",
                    text=seg.text.strip(),
                    words_per_sec=round(wc / dur, 2),
                    pitch_std=rec.pitch_std,
                    energy_cv=rec.energy_cv,
                )
            )
        return out

    clean_tr = rec.transcript.strip()
    if not clean_tr:
        return []
    eff_wps = max(2.0, wps or 3.3)
    cursor = 0.0
    fallback_out: list[VoiceSegmentRecord] = []
    for idx, sent in enumerate([s.strip() for s in SENTENCE_RE.split(clean_tr) if s.strip()]):
        wc = len(sent.split())
        dur = max(1.5, wc / eff_wps)
        fallback_out.append(
            VoiceSegmentRecord(
                segment_id=f"{rec.video_id}_s{idx:03d}",
                video_id=rec.video_id,
                seq_no=idx,
                start_sec=round(cursor, 2),
                end_sec=round(cursor + dur, 2),
                timestamp_source="wps_estimated",
                text=sent,
                words_per_sec=round(wc / dur, 2),
                pitch_std=rec.pitch_std,
                energy_cv=rec.energy_cv,
            )
        )
        cursor += dur
    return fallback_out


def ingest_incremental_batch_to_gold(
    base_corpus_dir: Path,
    incremental_jsonl: Path,
    output_corpus_dir: Path,
    *,
    update_existing: bool = False,
) -> CorpusManifest:
    with snapshot_workspace(output_corpus_dir) as staging_dir:
        manifest = _ingest_incremental_batch_to_gold(
            base_corpus_dir, incremental_jsonl, staging_dir,
            snapshot_id=output_corpus_dir.name, update_existing=update_existing,
        )
        load_verified_corpus(staging_dir)
        for fname in ("fact_voice_segments.parquet", "fact_comments.parquet", "fact_absa_reviews.parquet"):
            pq.read_table(staging_dir / fname)
    return manifest


def _ingest_incremental_batch_to_gold(
    base_corpus_dir: Path,
    incremental_jsonl: Path,
    output_corpus_dir: Path,
    *,
    snapshot_id: str,
    update_existing: bool,
) -> CorpusManifest:
    """Dual-Sink Converter:
    1) Appends normalized 49-column rows to fact_videos.parquet (+ dim_creators.parquet) for RAG/Benchmarks.
    2) Populates fact_voice_segments.parquet, fact_comments.parquet, and fact_absa_reviews.parquet for 4M modules.
    """
    base_manifest, df_creators, df_videos = load_verified_corpus(base_corpus_dir)
    parent_manifest_sha256 = _sha256_file(base_corpus_dir / "manifest.json")

    # Coalesce repeated video records before either sink is computed. Later
    # supplied fields win; omitted values and distinct comments are retained.
    raw_records: dict[str, RawIncrementalVideoRecord] = {}
    for line in incremental_jsonl.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = RawIncrementalVideoRecord.model_validate_json(line)
        previous = raw_records.get(rec.video_id)
        values = previous.model_dump(exclude_unset=True) if previous is not None else {}
        values.update(rec.model_dump(exclude_unset=True, exclude={"comments"}))
        values["comments"] = [comment.model_dump(exclude_unset=True) for comment in _merge_comments(
            previous.comments if previous is not None else [], rec.comments,
        )]
        raw_records[rec.video_id] = RawIncrementalVideoRecord.model_validate(values)

    existing_vids = set(df_videos["video_id"].astype(str).tolist())
    base_videos = {str(row["video_id"]): row for row in df_videos.to_dict(orient="records")}
    base_multimodal: dict[str, pd.DataFrame] = {}
    declared = {entry.filename for entry in base_manifest.files}
    for name in ("fact_voice_segments.parquet", "fact_comments.parquet", "fact_absa_reviews.parquet"):
        # Only load tables covered by the verified base manifest.
        if name in declared:
            base_multimodal[name] = pd.read_parquet(base_corpus_dir / name)
    creator_medians: dict[str, float] = dict(
        zip(df_creators["author_id"].astype(str), df_creators["median_play_count"].astype(float))
    )
    existing_aids = set(df_creators["author_id"].astype(str).tolist())

    new_video_rows: list[dict[str, Any]] = []
    new_creator_rows: list[dict[str, Any]] = []
    voice_rows: list[dict[str, Any]] = []
    comment_rows: list[dict[str, Any]] = []
    absa_rows: list[dict[str, Any]] = []
    replaced_voice_ids: set[str] = set()
    observed_dates: list[str] = []

    for rec in raw_records.values():
        is_existing = rec.video_id in existing_vids
        if is_existing and not update_existing:
            continue
        old_row = base_videos.get(rec.video_id)
        transcript_changed = bool(rec.transcript.strip()) and (
            old_row is None or rec.transcript != old_row.get("transcript")
        )
        replace_voice = old_row is None or bool(rec.whisper_segments) or (
            bool(rec.transcript.strip()) and rec.transcript != old_row.get("transcript")
        )
        if old_row is not None:
            # Enrichment preserves the observed metadata/counters; it cannot replace
            # historical observations with the defaults of a sparse ASR/comment record.
            excluded_fields = {
                "transcript", "pitch_std", "energy_cv", "comments", "whisper_segments", "audio_path",
            }
            preserved = _normalize_preserved_row(old_row, excluded_fields)
            rec = rec.model_copy(update=preserved)
            if not rec.transcript.strip():
                rec = rec.model_copy(update={"transcript": str(_normalize_scalar(old_row.get("transcript")) or "")})
            old_comments = base_multimodal.get("fact_comments.parquet")
            prior_comments: list[RawCommentInput] = []
            if old_comments is not None:
                for item in old_comments[old_comments["video_id"] == rec.video_id].to_dict(orient="records"):
                    cleaned_item = {k: _normalize_scalar(v) for k, v in item.items()}
                    prior_comments.append(RawCommentInput.model_validate(cleaned_item))
            rec = rec.model_copy(update={"comments": _merge_comments(prior_comments, rec.comments)})
        existing_vids.add(rec.video_id)

        tier = classify_follower_tier(rec.follower_count)
        c_median = creator_medians.get(rec.author_id, float(max(rec.play_count, 1000)))
        er = compute_engagement_rate(
            rec.play_count, rec.digg_count, rec.comment_count, rec.share_count, rec.collect_count
        )
        v_mult = compute_viral_multiplier(rec.play_count, c_median)

        dt = datetime.fromisoformat(rec.create_time.replace("Z", "+00:00"))
        observed_dates.append(dt.strftime("%Y-%m-%d"))
        iso_year, iso_week, _ = dt.isocalendar()
        year_week = f"Y{iso_year}_W{iso_week:02d}"

        has_tr = bool(rec.transcript.strip())
        wc = len(rec.transcript.split()) if has_tr else 0
        wps = round(wc / rec.duration_sec, 3) if (has_tr and rec.duration_sec > 0) else 0.0

        city_norm, district_norm, region, loc_source = resolve_location(
            poi_city=rec.poi_city,
            poi_address=rec.poi_address,
            llm_city=None,
            llm_district=None,
            poi_name=rec.poi_name,
        )
        if city_norm is None and rec.caption.strip():
            cap_city, cap_dist, cap_reg = resolve_location_from_caption(rec.caption)
            if cap_city:
                city_norm = cap_city
                district_norm = district_norm or cap_dist
                region = cap_reg if cap_reg != "unknown" else region
                loc_source = "caption_inferred"
        hashtags = [h.lstrip("#").lower() for h in rec.hashtags if h.strip()]
        combined_text = f"{rec.caption} {' '.join(hashtags)} {rec.poi_name or ''} {rec.transcript[:800]}"
        video_format = infer_video_format(
            legacy_cat=None,
            desc=rec.caption,
            transcript=rec.transcript,
            poi_name=rec.poi_name,
            is_ec_video=rec.is_ec_video,
        )
        dishes = extract_dishes_from_text(combined_text)
        food_cat = map_food_category(dishes=dishes, text=combined_text, poi_cat=rec.poi_category_tiny)
        price_tier = extract_price_tier(text=combined_text, video_format=video_format)
        occasions = extract_occasions(text=combined_text, video_format=video_format)
        hook_text, body_beats, cta_text = extract_script_anatomy(transcript=rec.transcript)

        rag_doc = ""
        if has_tr:
            loc_label = " - ".join(filter(None, [rec.poi_name, district_norm, city_norm])) or "Việt Nam"
            dish_label = ", ".join(dishes) if dishes else food_cat
            rag_doc = (
                f"[{video_format} | {food_cat} | {price_tier}] "
                f"Món: {dish_label}. Địa điểm: {loc_label}. "
                f"Hook: {hook_text} Caption: {rec.caption} Transcript: {rec.transcript}"
            ).strip()

        # Sink 1: exact 49-column canonical row for fact_videos.parquet
        new_video_rows.append(
            {
                "video_id": rec.video_id,
                "author_id": rec.author_id,
                "author_handle": rec.author_handle,
                "author_nickname": rec.author_nickname,
                "tiktok_url": f"https://www.tiktok.com/@{rec.author_handle}/video/{rec.video_id}",
                "follower_count": rec.follower_count,
                "follower_tier": tier,
                "create_time": dt.isoformat(),
                "create_hour": dt.hour,
                "year_week": year_week,
                "play_count": rec.play_count,
                "digg_count": rec.digg_count,
                "comment_count": rec.comment_count,
                "share_count": rec.share_count,
                "collect_count": rec.collect_count,
                "engagement_rate": er,
                "viral_multiplier": v_mult,
                "is_ad": rec.is_ad,
                "is_ec_video": rec.is_ec_video,
                "playlist_id": rec.playlist_id,
                "duration_sec": rec.duration_sec,
                "duration_bucket": classify_duration_bucket(rec.duration_sec),
                "caption": rec.caption,
                "hashtags": hashtags,
                "hashtag_count": len(hashtags),
                "has_transcript": has_tr,
                "transcript": rec.transcript,
                "word_count": wc,
                "word_per_second": wps,
                "has_cta": bool(cta_text),
                "has_curiosity_gap": "?" in hook_text,
                "poi_id": rec.poi_id,
                "poi_name": rec.poi_name,
                "poi_address": rec.poi_address,
                "poi_city": rec.poi_city,
                "poi_category_tiny": rec.poi_category_tiny,
                "city_norm": city_norm,
                "district_norm": district_norm,
                "region": region,
                "location_source": loc_source,
                "video_format": video_format,
                "food_category": food_cat,
                "dishes": dishes,
                "price_tier": price_tier,
                "occasions": occasions,
                "hook_text": hook_text,
                "body_beats": body_beats,
                "cta_text": cta_text,
                "rag_document": rag_doc,
            }
        )
        if old_row is not None:
            # Only text-derived columns are replaced during explicit enrichment.
            derived = {"has_transcript", "transcript", "word_count", "word_per_second", "has_cta",
                       "has_curiosity_gap", "hook_text", "body_beats", "cta_text", "rag_document"}
            updated = dict(old_row)
            if transcript_changed:
                updated.update({key: new_video_rows[-1][key] for key in derived})
            new_video_rows[-1] = updated

        if rec.author_id not in existing_aids:
            existing_aids.add(rec.author_id)
            new_creator_rows.append(
                {
                    "author_id": rec.author_id,
                    "unique_id": rec.author_handle,
                    "nickname": rec.author_nickname,
                    "verified": False,
                    "commerce_user": rec.is_ec_video,
                    "tt_seller": False,
                    "follower_count": rec.follower_count,
                    "follower_tier": tier,
                    "heart_count": rec.digg_count,
                    "lifetime_video_count": 1,
                    "sample_video_count": 1,
                    "median_play_count": float(rec.play_count),
                    "median_engagement_rate": er,
                    "median_duration_sec": float(rec.duration_sec),
                    "avg_videos_per_week": 1.0,
                }
            )

        # Sink 2: Multimodal tables (Voice Segments + Seeding Comments + KOC-vs-Viewer ABSA)
        if replace_voice:
            replaced_voice_ids.add(rec.video_id)
            for seg in _build_voice_segments(rec, wps):
                voice_rows.append(seg.model_dump())

        cleansed_comments = detect_seeding_comments(rec.video_id, rec.comments)
        comment_schema_cols = set(_COMMENTS_SCHEMA.names)
        for c_rec in cleansed_comments:
            comment_rows.append(c_rec.model_dump(include=comment_schema_cols))

        absa_comp = analyze_koc_vs_viewer_absa(
            video_id=rec.video_id,
            caption=rec.caption,
            transcript=rec.transcript,
            comments=cleansed_comments,
            is_ad=rec.is_ad,
            is_ec_video=rec.is_ec_video,
            hashtags=rec.hashtags,
        )
        absa_rows.append(
            {
                "video_id": absa_comp.video_id,
                "koc_taste": absa_comp.koc_scores.taste,
                "koc_price": absa_comp.koc_scores.price,
                "koc_hygiene": absa_comp.koc_scores.hygiene,
                "koc_service": absa_comp.koc_scores.service,
                "viewer_taste": absa_comp.viewer_clean_scores.taste,
                "viewer_price": absa_comp.viewer_clean_scores.price,
                "viewer_hygiene": absa_comp.viewer_clean_scores.hygiene,
                "viewer_service": absa_comp.viewer_clean_scores.service,
                "pr_hype_gap": absa_comp.pr_hype_gap,
                "undisclosed_pr_risk": absa_comp.undisclosed_pr_risk,
                "viewer_pain_points": absa_comp.viewer_pain_points,
                "clean_comment_count": absa_comp.clean_comment_count,
                "seeding_comment_count": absa_comp.seeding_comment_count,
            }
        )

    df_out_creators = (
        pd.concat([df_creators, pd.DataFrame(new_creator_rows)], ignore_index=True)
        if new_creator_rows
        else df_creators
    )
    updated_video_ids = {str(row["video_id"]) for row in new_video_rows}
    df_out_videos = pd.concat([
        df_videos[~df_videos["video_id"].isin(updated_video_ids)],
        pd.DataFrame(new_video_rows).reindex(columns=df_videos.columns),
    ], ignore_index=True) if new_video_rows else df_videos

    df_voice = pd.DataFrame(voice_rows) if voice_rows else pd.DataFrame(columns=_VOICE_SEGMENTS_SCHEMA.names)
    df_comments = pd.DataFrame(comment_rows) if comment_rows else pd.DataFrame(columns=_COMMENTS_SCHEMA.names)
    df_absa = pd.DataFrame(absa_rows) if absa_rows else pd.DataFrame(columns=_ABSA_REVIEWS_SCHEMA.names)

    def _carry_forward(name: str, fresh: pd.DataFrame, replace_ids: set[str]) -> pd.DataFrame:
        old = base_multimodal.get(name)
        if old is None:
            return fresh
        retained = old[~old["video_id"].isin(replace_ids)]
        return pd.concat([retained, fresh], ignore_index=True) if len(fresh) else retained.copy()

    df_voice = _carry_forward("fact_voice_segments.parquet", df_voice, replaced_voice_ids)
    df_comments = _carry_forward("fact_comments.parquet", df_comments, updated_video_ids)
    df_absa = _carry_forward("fact_absa_reviews.parquet", df_absa, updated_video_ids)

    tables: list[tuple[str, pd.DataFrame, pa.Schema | None]] = [
        ("dim_creators.parquet", df_out_creators, None),
        ("fact_videos.parquet", df_out_videos, None),
        ("fact_voice_segments.parquet", df_voice, _VOICE_SEGMENTS_SCHEMA),
        ("fact_comments.parquet", df_comments, _COMMENTS_SCHEMA),
        ("fact_absa_reviews.parquet", df_absa, _ABSA_REVIEWS_SCHEMA),
    ]

    checksums: list[CorpusFileChecksum] = []
    for fname, df_tbl, arrow_schema in tables:
        out_p = output_corpus_dir / fname
        pa_table = pa.Table.from_pandas(df_tbl, schema=arrow_schema, preserve_index=False)
        pq.write_table(pa_table, out_p, compression="snappy")
        checksums.append(
            CorpusFileChecksum(
                filename=fname,
                rows=len(df_tbl),
                columns=int(pa_table.num_columns),
                sha256=_sha256_file(out_p),
                size_bytes=out_p.stat().st_size,
            )
        )

    effective_window_end = (
        max([base_manifest.date_window_end, *observed_dates])
        if observed_dates
        else base_manifest.date_window_end
    )
    manifest = CorpusManifest(
        snapshot_id=snapshot_id,
        parent_snapshot_id=base_manifest.snapshot_id,
        parent_manifest_sha256=parent_manifest_sha256,
        created_at=datetime.now(UTC).isoformat(),
        date_window_start=base_manifest.date_window_start,
        date_window_end=effective_window_end,
        total_creators=len(df_out_creators),
        total_videos=len(df_out_videos),
        transcribed_videos=int(df_out_videos["has_transcript"].sum()),
        poi_tagged_videos=int(df_out_videos["poi_name"].notna().sum()),
        ec_tagged_videos=int(df_out_videos["is_ec_video"].sum()),
        files=checksums,
        caveats=[
            *base_manifest.caveats,
            f"Applied {len(new_video_rows)} incremental video records; explicit enrichment={update_existing}. Parent snapshot={base_manifest.snapshot_id}.",
        ],
    )
    (output_corpus_dir / "manifest.json").write_text(
        json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
