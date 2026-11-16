from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from packages.absa import analyze_koc_vs_viewer_absa
from packages.analytics import load_verified_corpus
from packages.data_contracts.corpus import CorpusFileChecksum, CorpusManifest
from packages.data_contracts.multimodal import RawIncrementalVideoRecord, VoiceSegmentRecord
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
)
from pipelines.build_gold_corpus.builder import (
    classify_follower_tier,
    compute_engagement_rate,
    compute_viral_multiplier,
)

SENTENCE_RE = re.compile(r"(?<=[.!?…])\s+|\n+")


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


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
) -> CorpusManifest:
    """Dual-Sink Converter:
    1) Appends normalized 49-column rows to fact_videos.parquet (+ dim_creators.parquet) for RAG/Benchmarks.
    2) Populates fact_voice_segments.parquet, fact_comments.parquet, and fact_absa_reviews.parquet for 4M modules.
    """
    base_manifest, df_creators, df_videos = load_verified_corpus(base_corpus_dir)
    output_corpus_dir.mkdir(parents=True, exist_ok=True)

    raw_records = [
        RawIncrementalVideoRecord.model_validate_json(line)
        for line in incremental_jsonl.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    existing_vids = set(df_videos["video_id"].astype(str).tolist())
    creator_medians: dict[str, float] = dict(
        zip(df_creators["author_id"].astype(str), df_creators["median_play_count"].astype(float))
    )
    existing_aids = set(df_creators["author_id"].astype(str).tolist())

    new_video_rows: list[dict[str, Any]] = []
    new_creator_rows: list[dict[str, Any]] = []
    voice_rows: list[dict[str, Any]] = []
    comment_rows: list[dict[str, Any]] = []
    absa_rows: list[dict[str, Any]] = []

    for rec in raw_records:
        if rec.video_id in existing_vids:
            continue
        existing_vids.add(rec.video_id)

        tier = classify_follower_tier(rec.follower_count)
        c_median = creator_medians.get(rec.author_id, float(max(rec.play_count, 1000)))
        er = compute_engagement_rate(
            rec.play_count, rec.digg_count, rec.comment_count, rec.share_count, rec.collect_count
        )
        v_mult = compute_viral_multiplier(rec.play_count, c_median)

        try:
            dt = datetime.fromisoformat(rec.create_time.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.now(timezone.utc)
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
        )
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
        for seg in _build_voice_segments(rec, wps):
            voice_rows.append(seg.model_dump())

        cleansed_comments = detect_seeding_comments(rec.video_id, rec.comments)
        for c_rec in cleansed_comments:
            comment_rows.append(c_rec.model_dump())

        absa_comp = analyze_koc_vs_viewer_absa(
            video_id=rec.video_id,
            caption=rec.caption,
            transcript=rec.transcript,
            comments=cleansed_comments,
            is_ad=rec.is_ad,
            is_ec_video=rec.is_ec_video,
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
    df_out_videos = (
        pd.concat([df_videos, pd.DataFrame(new_video_rows)[df_videos.columns]], ignore_index=True)
        if new_video_rows
        else df_videos
    )

    df_voice = pd.DataFrame(voice_rows) if voice_rows else pd.DataFrame(
        columns=["segment_id", "video_id", "seq_no", "start_sec", "end_sec", "timestamp_source", "text", "words_per_sec", "pitch_std", "energy_cv"]
    )
    df_comments = pd.DataFrame(comment_rows) if comment_rows else pd.DataFrame(
        columns=["comment_id", "video_id", "author_handle", "text", "like_count", "reply_count", "is_seeding", "seeding_reason", "similarity_score", "cluster_id"]
    )
    df_absa = pd.DataFrame(absa_rows) if absa_rows else pd.DataFrame(
        columns=["video_id", "koc_taste", "koc_price", "koc_hygiene", "koc_service", "viewer_taste", "viewer_price", "viewer_hygiene", "viewer_service", "pr_hype_gap", "undisclosed_pr_risk", "viewer_pain_points", "clean_comment_count", "seeding_comment_count"]
    )

    tables = [
        ("dim_creators.parquet", df_out_creators),
        ("fact_videos.parquet", df_out_videos),
        ("fact_voice_segments.parquet", df_voice),
        ("fact_comments.parquet", df_comments),
        ("fact_absa_reviews.parquet", df_absa),
    ]

    checksums: list[CorpusFileChecksum] = []
    for fname, df_tbl in tables:
        out_p = output_corpus_dir / fname
        pq.write_table(pa.Table.from_pandas(df_tbl, preserve_index=False), out_p, compression="snappy")
        checksums.append(
            CorpusFileChecksum(
                filename=fname,
                rows=len(df_tbl),
                columns=len(df_tbl.columns),
                sha256=_sha256_file(out_p),
                size_bytes=out_p.stat().st_size,
            )
        )

    manifest = CorpusManifest(
        snapshot_id=output_corpus_dir.name,
        created_at=datetime.now(timezone.utc).isoformat(),
        date_window_start=base_manifest.date_window_start,
        date_window_end=datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        total_creators=len(df_out_creators),
        total_videos=len(df_out_videos),
        transcribed_videos=int(df_out_videos["has_transcript"].sum()),
        poi_tagged_videos=int(df_out_videos["poi_name"].notna().sum()),
        ec_tagged_videos=int(df_out_videos["is_ec_video"].sum()),
        files=checksums,
        caveats=[
            *base_manifest.caveats,
            f"Includes {len(new_video_rows)} fresh 4-month incremental multimodal videos converted via Dual-Sink pipeline.",
        ],
    )
    (output_corpus_dir / "manifest.json").write_text(
        json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return manifest
