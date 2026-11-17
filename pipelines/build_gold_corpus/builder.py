from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from packages.data_contracts.corpus import CorpusFileChecksum, CorpusManifest
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

INVALID_TRANSCRIPT_PREFIXES: tuple[str, ...] = (
    "none",
    "null",
    "nan",
    "i am sorry",
    "i'm sorry",
    "i am unable to process",
    "i cannot provide",
    "không có lời thoại",
)

FALLBACK_TRANSCRIPT_RE = re.compile(
    r'"transcript"\s*:\s*"(.*?)"\s*,\s*"takeaways"',
    flags=re.DOTALL,
)


def compute_engagement_rate(
    play_count: int | float,
    digg_count: int | float,
    comment_count: int | float,
    share_count: int | float,
    collect_count: int | float,
) -> float:
    plays = float(play_count or 0.0)
    if plays <= 0.0:
        return 0.0
    interactions = (
        max(0.0, float(digg_count or 0.0))
        + max(0.0, float(comment_count or 0.0))
        + max(0.0, float(share_count or 0.0))
        + max(0.0, float(collect_count or 0.0))
    )
    return round(interactions / plays, 6)


def compute_viral_multiplier(play_count: int | float, creator_median_plays: int | float) -> float:
    plays = float(play_count or 0.0)
    if plays <= 0.0:
        return 0.0
    baseline = max(float(creator_median_plays or 0.0), 1000.0)
    return round(plays / baseline, 4)


def classify_follower_tier(followers: int | float) -> str:
    f = float(followers or 0.0)
    if f < 100_000:
        return "micro"
    if f < 500_000:
        return "mid"
    if f < 1_000_000:
        return "macro"
    return "mega"


def _to_clean_str_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, (list, tuple, np.ndarray)):
        out: list[str] = []
        for item in val:
            if item is None:
                continue
            s = str(item).strip()
            if s and s.lower() not in {"none", "nan", "null"}:
                out.append(s)
        return out
    if isinstance(val, str):
        s = val.strip()
        if s and s.lower() not in {"none", "nan", "null", "[]"}:
            return [s]
    return []


def _clean_optional_str(val: Any) -> str | None:
    if val is None:
        return None
    if isinstance(val, float) and np.isnan(val):
        return None
    s = str(val).strip()
    if not s or s.lower() in {"none", "nan", "null", "others"}:
        return None
    return s


def _to_bool(val: Any) -> bool:
    if isinstance(val, (bool, np.bool_)):
        return bool(val)
    if val is None:
        return False
    return str(val).strip().lower() in {"true", "1", "1.0", "yes"}


def _is_valid_transcript(text: str) -> bool:
    clean = text.strip()
    if len(clean) < 8:
        return False
    lower = clean.lower()
    return not any(lower.startswith(prefix) for prefix in INVALID_TRANSCRIPT_PREFIXES)


def _load_transcripts_dir(transcripts_dir: Path) -> dict[str, dict[str, Any]]:
    records: dict[str, dict[str, Any]] = {}
    if not transcripts_dir.is_dir():
        return records

    for path in sorted(transcripts_dir.glob("*.json")):
        vid = path.stem.strip()
        raw_txt = path.read_text(encoding="utf-8", errors="replace").strip()
        if not raw_txt:
            continue
        if raw_txt.startswith("```"):
            raw_txt = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_txt, flags=re.DOTALL).strip()

        parsed: dict[str, Any] | None = None
        try:
            candidate = json.loads(raw_txt, strict=False)
            if isinstance(candidate, dict):
                parsed = candidate
        except json.JSONDecodeError:
            m_obj = re.search(r"\{.*\}", raw_txt, flags=re.DOTALL)
            if m_obj:
                try:
                    candidate = json.loads(m_obj.group(0), strict=False)
                    if isinstance(candidate, dict):
                        parsed = candidate
                except json.JSONDecodeError:
                    m_tr = FALLBACK_TRANSCRIPT_RE.search(raw_txt)
                    if m_tr:
                        parsed = {
                            "transcript": m_tr.group(1).replace('\\"', '"'),
                            "takeaways": [],
                            "has_call_to_action": False,
                            "has_curiosity_gap": False,
                        }

        if not parsed:
            continue

        tr_text = str(parsed.get("transcript") or "").strip()
        if not _is_valid_transcript(tr_text):
            continue

        records[vid] = {
            "transcript": tr_text,
            "takeaways": _to_clean_str_list(parsed.get("takeaways")),
            "has_cta": _to_bool(parsed.get("has_call_to_action")),
            "has_curiosity_gap": _to_bool(parsed.get("has_curiosity_gap")),
        }
    return records


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def build_gold_corpus(root_dir: Path, output_dir: Path, snapshot_id: str | None = None) -> CorpusManifest:
    from packages.common.snapshots import snapshot_workspace

    with snapshot_workspace(output_dir) as staging_dir:
        manifest = _build_gold_corpus(root_dir, staging_dir, snapshot_id or output_dir.name)
        from packages.analytics import load_verified_corpus

        load_verified_corpus(staging_dir)
    return manifest


def _build_gold_corpus(root_dir: Path, output_dir: Path, snapshot_id: str) -> CorpusManifest:
    """Build immutable Gold Parquet corpus from read-only upstream datasets."""
    snap_id = snapshot_id

    user_parquet = root_dir / "data/processed/cleaned_user_info.parquet"
    video_parquet = root_dir / "data/processed/cleaned_video_info.parquet"
    raw_csv = root_dir / "data/interim/final_raw_videos.csv"
    transcripts_dir = root_dir / "data/transcripts"
    loc_food_parquet = root_dir / "data/legacy_app_data/trend_analysis/final_location_food_data.parquet"
    content_parquet = root_dir / "data/content_analysis/content_analysis_data.parquet"

    # 1. Load cleaned videos & users
    df_users = pd.read_parquet(user_parquet)
    df_videos = pd.read_parquet(video_parquet)

    # 2. Load official GPS POI + EC + Playlist metadata from raw CSV
    raw_cols = [
        "video.id",
        "poi.id",
        "poi.name",
        "poi.address",
        "poi.city",
        "poi.ttTypeNameTiny",
        "isECVideo",
        "playlistId",
    ]
    df_raw_poi = pd.read_csv(raw_csv, usecols=raw_cols, dtype=str)
    df_raw_poi["video_id_key"] = df_raw_poi["video.id"].str.replace(r"\.0$", "", regex=True).str.strip()
    df_raw_poi = df_raw_poi.dropna(subset=["video_id_key"]).drop_duplicates(subset=["video_id_key"], keep="first")
    poi_map: dict[str, dict[str, Any]] = df_raw_poi.set_index("video_id_key").to_dict(orient="index")

    # 3. Load legacy location/food annotations (14,252 rows)
    loc_map: dict[str, dict[str, Any]] = {}
    if loc_food_parquet.is_file():
        df_loc = pd.read_parquet(
            loc_food_parquet,
            columns=[
                "video.id",
                "foods",
                "city",
                "district",
                "city_std",
                "district_std",
                "transcript",
                "takeaway_1",
                "takeaway_2",
                "takeaway_3",
                "transcript_call_to_action",
                "transcript_curiosity_gap",
            ],
        )
        df_loc = df_loc.drop_duplicates(subset=["video.id"], keep="first")
        loc_map = df_loc.set_index("video.id").to_dict(orient="index")

    # 4. Load content_analysis annotations (3,004 rows)
    content_map: dict[str, dict[str, Any]] = {}
    if content_parquet.is_file():
        df_ca = pd.read_parquet(
            content_parquet,
            columns=[
                "video.id",
                "categories",
                "hook_content",
                "cta_content",
                "body_analysis",
                "takeaways",
                "has_cta",
                "transcript",
            ],
        )
        df_ca = df_ca.drop_duplicates(subset=["video.id"], keep="first")
        content_map = df_ca.set_index("video.id").to_dict(orient="index")

    # 5. Load all 23,122 JSON transcripts
    transcript_map = _load_transcripts_dir(transcripts_dir)

    # 6. Pre-compute per-creator empirical medians from cleaned_video_info
    df_videos["_plays"] = df_videos["statsV2.playCount"].fillna(0.0).clip(lower=0.0)
    df_videos["_diggs"] = df_videos["statsV2.diggCount"].fillna(0.0).clip(lower=0.0)
    df_videos["_comments"] = df_videos["statsV2.commentCount"].fillna(0.0).clip(lower=0.0)
    df_videos["_shares"] = df_videos["statsV2.shareCount"].fillna(0.0).clip(lower=0.0)
    df_videos["_collects"] = df_videos["statsV2.collectCount"].fillna(0.0).clip(lower=0.0)
    df_videos["_dur"] = df_videos["video.duration"].fillna(0.0).clip(lower=0.0)
    df_videos["_er"] = np.where(
        df_videos["_plays"] > 0,
        (df_videos["_diggs"] + df_videos["_comments"] + df_videos["_shares"] + df_videos["_collects"])
        / df_videos["_plays"],
        0.0,
    )

    creator_stats = (
        df_videos.groupby("author.id", dropna=False)
        .agg(
            sample_video_count=("video.id", "count"),
            median_play_count=("_plays", "median"),
            median_engagement_rate=("_er", "median"),
            median_duration_sec=("_dur", "median"),
        )
        .to_dict(orient="index")
    )

    # 7. Build dim_creators.parquet (264 rows)
    creator_rows: list[dict[str, Any]] = []
    creator_tier_lookup: dict[str, str] = {}
    for u in df_users.to_dict(orient="records"):
        aid = str(u.get("user.id") or "").strip()
        followers = int(u.get("stats.followerCount") or 0)
        tier = classify_follower_tier(followers)
        creator_tier_lookup[aid] = tier
        c_stat = creator_stats.get(aid, {})
        creator_rows.append(
            {
                "author_id": aid,
                "unique_id": str(u.get("user.uniqueId") or "").strip(),
                "nickname": str(u.get("user.nickname") or "").strip(),
                "verified": _to_bool(u.get("user.verified")),
                "commerce_user": _to_bool(u.get("user.commerceUserInfo.commerceUser")),
                "tt_seller": _to_bool(u.get("user.ttSeller")),
                "follower_count": followers,
                "follower_tier": tier,
                "heart_count": int(u.get("stats.heartCount") or 0),
                "lifetime_video_count": int(u.get("stats.videoCount") or 0),
                "sample_video_count": int(c_stat.get("sample_video_count") or 0),
                "median_play_count": round(float(c_stat.get("median_play_count") or 0.0), 2),
                "median_engagement_rate": round(float(c_stat.get("median_engagement_rate") or 0.0), 6),
                "median_duration_sec": round(float(c_stat.get("median_duration_sec") or 0.0), 2),
                "avg_videos_per_week": round(float(u.get("avg_videos_per_week") or 0.0), 3),
            }
        )

    df_dim_creators = pd.DataFrame(creator_rows)
    dim_creators_path = output_dir / "dim_creators.parquet"
    pq.write_table(pa.Table.from_pandas(df_dim_creators, preserve_index=False), dim_creators_path, compression="snappy")

    # 8. Build fact_videos.parquet (70,996 rows)
    video_rows: list[dict[str, Any]] = []
    transcribed_count = 0
    poi_tagged_count = 0
    ec_tagged_count = 0

    for row in df_videos.to_dict(orient="records"):
        vid = str(row["video.id"]).strip()
        aid = str(row.get("author.id") or "").strip()
        handle = str(row.get("author.uniqueId") or "").strip()
        nickname = str(row.get("author.nickname") or "").strip()
        followers = int(float(row.get("authorStats.followerCount") or 0.0))
        tier = creator_tier_lookup.get(aid) or classify_follower_tier(followers)

        plays = int(row["_plays"])
        diggs = int(row["_diggs"])
        comments = int(row["_comments"])
        shares = int(row["_shares"])
        collects = int(row["_collects"])
        dur_sec = int(round(float(row["_dur"])))
        dur_bucket = classify_duration_bucket(dur_sec)

        c_median_plays = float(creator_stats.get(aid, {}).get("median_play_count") or 0.0)
        er = compute_engagement_rate(plays, diggs, comments, shares, collects)
        v_mult = compute_viral_multiplier(plays, c_median_plays)

        create_ts: pd.Timestamp = row["createTime"]
        create_iso = create_ts.isoformat() if pd.notna(create_ts) else ""
        create_hour = int(create_ts.hour) if pd.notna(create_ts) else 0
        year_week = str(row.get("year_week") or "")

        caption = str(row.get("desc") or "").strip()
        hashtags = [h.lower() for h in _to_clean_str_list(row.get("hashtags"))]

        # Merge raw POI / EC / Playlist
        raw_info = poi_map.get(vid, {})
        poi_id = _clean_optional_str(raw_info.get("poi.id"))
        poi_name = _clean_optional_str(raw_info.get("poi.name"))
        poi_addr = _clean_optional_str(raw_info.get("poi.address"))
        poi_city = _clean_optional_str(raw_info.get("poi.city"))
        poi_cat_tiny = _clean_optional_str(raw_info.get("poi.ttTypeNameTiny"))
        is_ec = _to_bool(raw_info.get("isECVideo"))
        playlist_id = _clean_optional_str(raw_info.get("playlistId"))
        if playlist_id == "0" or playlist_id == "0.0":
            playlist_id = None
        is_ad = _to_bool(row.get("isAd"))

        if poi_name:
            poi_tagged_count += 1
        if is_ec:
            ec_tagged_count += 1

        # Merge transcript + legacy annotations
        tr_entry = transcript_map.get(vid)
        loc_entry = loc_map.get(vid, {})
        ca_entry = content_map.get(vid, {})

        transcript_str = ""
        takeaways: list[str] = []
        has_cta = False
        has_curiosity = False

        if tr_entry:
            transcript_str = tr_entry["transcript"]
            takeaways = tr_entry["takeaways"]
            has_cta = tr_entry["has_cta"]
            has_curiosity = tr_entry["has_curiosity_gap"]
        else:
            fallback_tr = _clean_optional_str(ca_entry.get("transcript")) or _clean_optional_str(
                loc_entry.get("transcript")
            )
            if fallback_tr and _is_valid_transcript(fallback_tr):
                transcript_str = fallback_tr
                takeaways = _to_clean_str_list(ca_entry.get("takeaways")) or [
                    t
                    for t in (
                        _clean_optional_str(loc_entry.get("takeaway_1")),
                        _clean_optional_str(loc_entry.get("takeaway_2")),
                        _clean_optional_str(loc_entry.get("takeaway_3")),
                    )
                    if t
                ]
                has_cta = _to_bool(ca_entry.get("has_cta")) or _to_bool(loc_entry.get("transcript_call_to_action"))
                has_curiosity = _to_bool(loc_entry.get("transcript_curiosity_gap"))

        has_transcript = bool(transcript_str)
        if has_transcript:
            transcribed_count += 1

        word_count = len(transcript_str.split()) if has_transcript else 0
        wps = round(word_count / dur_sec, 3) if (has_transcript and dur_sec > 0) else 0.0

        # Resolve geography with GPS POI priority
        llm_city = loc_entry.get("city_std") or loc_entry.get("city")
        llm_dist = loc_entry.get("district_std") or loc_entry.get("district")
        city_norm, district_norm, region, loc_source = resolve_location(
            poi_city=poi_city,
            poi_address=poi_addr,
            llm_city=llm_city,
            llm_district=llm_dist,
        )

        # Resolve taxonomy & context
        combined_text = f"{caption} {' '.join(hashtags)} {poi_name or ''} {transcript_str[:800]}"
        video_format = infer_video_format(
            legacy_cat=ca_entry.get("categories"),
            desc=caption,
            transcript=transcript_str,
            poi_name=poi_name,
            is_ec_video=is_ec,
        )

        legacy_dishes = [d.lower() for d in _to_clean_str_list(loc_entry.get("foods"))]
        regex_dishes = extract_dishes_from_text(combined_text)
        dishes = list(dict.fromkeys([*legacy_dishes, *regex_dishes]))[:10]
        food_category = map_food_category(dishes=dishes, text=combined_text, poi_cat=poi_cat_tiny)
        price_tier = extract_price_tier(text=combined_text, video_format=video_format)
        occasions = extract_occasions(text=combined_text, video_format=video_format)

        # Script anatomy
        llm_cta_list = _to_clean_str_list(ca_entry.get("cta_content"))
        llm_cta = llm_cta_list[0] if llm_cta_list else None
        ca_body_beats: list[str] = []
        raw_ba = ca_entry.get("body_analysis")
        if isinstance(raw_ba, (list, tuple, np.ndarray)):
            for b in raw_ba:
                if isinstance(b, dict) and b.get("desc"):
                    ca_body_beats.append(str(b["desc"]).strip())

        hook_text, body_beats, cta_text = extract_script_anatomy(
            transcript=transcript_str,
            llm_hook=ca_entry.get("hook_content"),
            llm_cta=llm_cta,
            takeaways=ca_body_beats or takeaways,
        )

        # Structured RAG document for transcribed videos
        rag_doc = ""
        if has_transcript:
            loc_label = " - ".join(filter(None, [poi_name, district_norm, city_norm])) or "Việt Nam"
            dish_label = ", ".join(dishes) if dishes else food_category
            rag_doc = (
                f"[{video_format} | {food_category} | {price_tier}] "
                f"Món: {dish_label}. Địa điểm: {loc_label}. "
                f"Hook: {hook_text} "
                f"Caption: {caption} "
                f"Transcript: {transcript_str}"
            ).strip()

        video_rows.append(
            {
                "video_id": vid,
                "author_id": aid,
                "author_handle": handle,
                "author_nickname": nickname,
                "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{vid}",
                "follower_count": followers,
                "follower_tier": tier,
                "create_time": create_iso,
                "create_hour": create_hour,
                "year_week": year_week,
                "play_count": plays,
                "digg_count": diggs,
                "comment_count": comments,
                "share_count": shares,
                "collect_count": collects,
                "engagement_rate": er,
                "viral_multiplier": v_mult,
                "is_ad": is_ad,
                "is_ec_video": is_ec,
                "playlist_id": playlist_id,
                "duration_sec": dur_sec,
                "duration_bucket": dur_bucket,
                "caption": caption,
                "hashtags": hashtags,
                "hashtag_count": len(hashtags),
                "has_transcript": has_transcript,
                "transcript": transcript_str,
                "word_count": word_count,
                "word_per_second": wps,
                "has_cta": has_cta,
                "has_curiosity_gap": has_curiosity,
                "poi_id": poi_id,
                "poi_name": poi_name,
                "poi_address": poi_addr,
                "poi_city": poi_city,
                "poi_category_tiny": poi_cat_tiny,
                "city_norm": city_norm,
                "district_norm": district_norm,
                "region": region,
                "location_source": loc_source,
                "video_format": video_format,
                "food_category": food_category,
                "dishes": dishes,
                "price_tier": price_tier,
                "occasions": occasions,
                "hook_text": hook_text,
                "body_beats": body_beats,
                "cta_text": cta_text,
                "rag_document": rag_doc,
            }
        )

    df_fact_videos = pd.DataFrame(video_rows)
    fact_videos_path = output_dir / "fact_videos.parquet"
    pq.write_table(pa.Table.from_pandas(df_fact_videos, preserve_index=False), fact_videos_path, compression="snappy")

    min_ts = df_videos["createTime"].min()
    max_ts = df_videos["createTime"].max()

    manifest = CorpusManifest(
        snapshot_id=snap_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        date_window_start=min_ts.strftime("%Y-%m-%d") if pd.notna(min_ts) else "",
        date_window_end=max_ts.strftime("%Y-%m-%d") if pd.notna(max_ts) else "",
        total_creators=len(df_dim_creators),
        total_videos=len(df_fact_videos),
        transcribed_videos=transcribed_count,
        poi_tagged_videos=poi_tagged_count,
        ec_tagged_videos=ec_tagged_count,
        files=[
            CorpusFileChecksum(
                filename="dim_creators.parquet",
                rows=len(df_dim_creators),
                columns=len(df_dim_creators.columns),
                sha256=_sha256_file(dim_creators_path),
                size_bytes=dim_creators_path.stat().st_size,
            ),
            CorpusFileChecksum(
                filename="fact_videos.parquet",
                rows=len(df_fact_videos),
                columns=len(df_fact_videos.columns),
                sha256=_sha256_file(fact_videos_path),
                size_bytes=fact_videos_path.stat().st_size,
            ),
        ],
        caveats=[
            "Creator-centric cohort (264 Vietnamese F&B creators, Nov 2023 - Apr 2025), not a uniform random sample of all TikTok Vietnam uploads.",
            "Engagement metrics are single-snapshot observations captured in Mar-Apr 2025; viral_multiplier normalizes plays against each creator's own empirical median.",
            "Spoken transcripts cover top weekly viral and enriched subsets (~22.6K videos), while metadata and POI benchmarks cover all 70,996 videos.",
        ],
    )

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest
