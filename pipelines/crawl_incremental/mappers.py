"""Unified schema mappers adapting 21KHDL-TikTok-Analytics itemStruct and yt-dlp payloads."""
from __future__ import annotations

import math
import re
from datetime import UTC, datetime
from typing import Any

_CLEAN_NULL_TOKENS = frozenset({"", "none", "null", "nan", "others"})
_CAPTION_HASHTAG_RE = re.compile(r"#([^\s#]+)", flags=re.UNICODE)


def _clean_opt_str(val: Any) -> str | None:
    if val is None or isinstance(val, bool):
        return None
    if isinstance(val, float) and math.isnan(val):
        return None
    s = str(val).strip()
    if s.lower() in _CLEAN_NULL_TOKENS:
        return None
    return s


def _as_dict(val: Any) -> dict[str, Any]:
    return val if isinstance(val, dict) else {}


def _safe_nonneg_int(val: Any, default: int = 0) -> int:
    if val is None or isinstance(val, bool):
        return default
    try:
        f = float(val)
        if not math.isfinite(f):
            return default
        return max(0, int(round(f)))
    except (ValueError, TypeError, OverflowError):
        return default


def _to_bool_flag(val: Any) -> bool:
    if isinstance(val, bool):
        return val
    if val is None:
        return False
    if isinstance(val, int | float):
        return bool(val == 1)
    return str(val).strip().lower() in {"true", "1", "1.0", "yes"}


def parse_timestamp_to_iso_utc(raw_ts: Any, fallback: str = "") -> str:
    if raw_ts is None or isinstance(raw_ts, bool):
        return fallback
    try:
        if isinstance(raw_ts, int | float):
            fval = float(raw_ts)
            if not math.isfinite(fval):
                return fallback
            return datetime.fromtimestamp(fval, tz=UTC).isoformat()
        text = str(raw_ts).strip()
        if not text:
            return fallback
        if text.isdigit():
            return datetime.fromtimestamp(float(text), tz=UTC).isoformat()
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.isoformat()
    except (ValueError, OSError, OverflowError):
        return fallback


def _extract_hashtags_from_item_struct(raw: dict[str, Any], caption: str) -> list[str]:
    tags: list[str] = []
    seen: set[str] = set()

    def _add_tag(candidate_tag: Any) -> None:
        cleaned = _clean_opt_str(candidate_tag)
        if not cleaned:
            return
        norm = cleaned.lstrip("#").strip()
        if not norm:
            return
        low = norm.lower()
        if low not in seen:
            seen.add(low)
            tags.append(norm)

    for ch in raw.get("challenges") or []:
        if isinstance(ch, dict):
            _add_tag(ch.get("title") or ch.get("hashtagName"))
        else:
            _add_tag(ch)

    for te in raw.get("textExtra") or []:
        if isinstance(te, dict):
            _add_tag(te.get("hashtagName"))

    for content_item in raw.get("contents") or []:
        if isinstance(content_item, dict):
            for te in content_item.get("textExtra") or []:
                if isinstance(te, dict):
                    _add_tag(te.get("hashtagName"))

    if not tags and caption:
        for match in _CAPTION_HASHTAG_RE.finditer(caption):
            _add_tag(match.group(1))

    return tags


def map_tiktok_item_struct_to_detail(
    raw: dict[str, Any],
    *,
    fallback_vid: str = "",
    fallback_handle: str = "",
    collected_at_utc: str | None = None,
) -> dict[str, Any]:
    """Map native TikTokApi itemStruct (21KHDL-TikTok-Analytics schema) to RawIncrementalVideoRecord dict."""
    canonical_vid = str(raw.get("id") or raw.get("video_id") or fallback_vid).strip()

    author_obj = _as_dict(raw.get("author"))
    author_stats = _as_dict(raw.get("authorStats"))
    video_obj = _as_dict(raw.get("video"))
    stats_v2 = _as_dict(raw.get("statsV2"))
    stats_v1 = _as_dict(raw.get("stats"))
    poi_obj = _as_dict(raw.get("poi"))

    handle = (
        _clean_opt_str(author_obj.get("uniqueId") or author_obj.get("unique_id"))
        or _clean_opt_str(raw.get("author_handle"))
        or fallback_handle.lstrip("@").strip()
        or "unknown"
    )
    author_id = (
        _clean_opt_str(author_obj.get("id") or author_obj.get("uid"))
        or _clean_opt_str(raw.get("author_id"))
        or f"author_{canonical_vid or 'unknown'}"
    )
    nickname = _clean_opt_str(author_obj.get("nickname")) or handle
    follower_count = _safe_nonneg_int(
        author_stats.get("followerCount")
        if "followerCount" in author_stats
        else author_obj.get("followerCount")
    )

    iso_ct = parse_timestamp_to_iso_utc(
        raw.get("createTime") if "createTime" in raw else raw.get("create_time")
    )
    caption = str(raw.get("desc") if raw.get("desc") is not None else (raw.get("caption") or ""))
    hashtags = _extract_hashtags_from_item_struct(raw, caption)
    duration_sec = _safe_nonneg_int(
        video_obj.get("duration") if "duration" in video_obj else raw.get("duration_sec")
    )

    def _stat_val(key_camel: str) -> int:
        if key_camel in stats_v2 and stats_v2[key_camel] is not None:
            return _safe_nonneg_int(stats_v2[key_camel])
        return _safe_nonneg_int(stats_v1.get(key_camel))

    play_count = _stat_val("playCount")
    digg_count = _stat_val("diggCount")
    comment_count = _stat_val("commentCount")
    share_count = _stat_val("shareCount")
    collect_count = _stat_val("collectCount")

    is_ad = _to_bool_flag(raw.get("isAd")) or _to_bool_flag(author_obj.get("isADVirtual"))
    is_ec_video = _to_bool_flag(raw.get("isECVideo"))
    is_pinned = _to_bool_flag(raw.get("isPinnedItem"))
    playlist_id = _clean_opt_str(raw.get("playlistId"))

    poi_id = _clean_opt_str(poi_obj.get("id") or raw.get("poi.id"))
    poi_name = _clean_opt_str(poi_obj.get("name") or raw.get("poi.name"))
    poi_address = _clean_opt_str(poi_obj.get("address") or raw.get("poi.address"))
    poi_city = _clean_opt_str(poi_obj.get("city") or raw.get("poi.city"))
    poi_cat_tiny = _clean_opt_str(
        poi_obj.get("ttTypeNameTiny")
        or poi_obj.get("category")
        or raw.get("poi.ttTypeNameTiny")
    )

    now_utc_iso = collected_at_utc or datetime.now(UTC).isoformat()
    raw_snapshot = dict(raw)
    raw_snapshot.setdefault("collectTime", int(datetime.now(UTC).timestamp()))

    return {
        "video_id": canonical_vid,
        "author_id": author_id,
        "author_handle": handle,
        "author_nickname": nickname,
        "follower_count": follower_count,
        "create_time": iso_ct,
        "caption": caption,
        "hashtags": hashtags,
        "duration_sec": duration_sec,
        "play_count": play_count,
        "digg_count": digg_count,
        "comment_count": comment_count,
        "share_count": share_count,
        "collect_count": collect_count,
        "is_ad": is_ad,
        "is_ec_video": is_ec_video,
        "is_pinned_item": is_pinned,
        "playlist_id": playlist_id,
        "poi_id": poi_id,
        "poi_name": poi_name,
        "poi_address": poi_address,
        "poi_city": poi_city,
        "poi_category_tiny": poi_cat_tiny,
        "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{canonical_vid}",
        "transcript": "",
        "collected_at_utc": now_utc_iso,
        "_raw_provider_payload": raw_snapshot,
    }


def map_tiktok_comment_to_input(
    raw: dict[str, Any],
    *,
    canonical_vid: str,
    idx: int,
) -> dict[str, Any] | None:
    """Normalize TikTokApi or yt-dlp comment dict while preserving unstripped text for M5.2 NFC offsets."""
    if not isinstance(raw, dict):
        return None
    raw_text = raw.get("text")
    if not isinstance(raw_text, str) or not raw_text.strip():
        return None

    cid = _clean_opt_str(raw.get("cid") or raw.get("id") or raw.get("comment_id")) or f"{canonical_vid}_c{idx}"
    user_obj = _as_dict(raw.get("user"))
    author_handle = (
        _clean_opt_str(
            user_obj.get("unique_id")
            or user_obj.get("uniqueId")
            or raw.get("author_handle")
            or raw.get("author")
        )
        or ""
    ).lstrip("@")

    likes = _safe_nonneg_int(
        raw.get("digg_count") if "digg_count" in raw else raw.get("like_count")
    )
    replies = _safe_nonneg_int(
        raw.get("reply_comment_total")
        if "reply_comment_total" in raw
        else raw.get("reply_count")
    )
    return {
        "comment_id": cid,
        "author_handle": author_handle,
        "text": raw_text,
        "like_count": likes,
        "reply_count": replies,
    }


def map_ytdlp_json_to_detail(
    raw: dict[str, Any],
    *,
    candidate: dict[str, Any],
    collected_at_utc: str | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Normalize yt-dlp video info-dict & flat comments into canonical detail + mapped comments."""
    cand_vid = str(candidate.get("video_id") or "").strip()
    cand_handle = str(candidate.get("author_handle") or "").lstrip("@").strip()
    canonical_vid = str(raw.get("id") or cand_vid).strip()
    handle = _clean_opt_str(raw.get("uploader") or raw.get("creator")) or cand_handle or "unknown"
    url = str(
        candidate.get("tiktok_url")
        or raw.get("webpage_url")
        or f"https://www.tiktok.com/@{handle}/video/{canonical_vid}"
    )
    iso_ct = parse_timestamp_to_iso_utc(
        raw.get("timestamp"),
        fallback=parse_timestamp_to_iso_utc(candidate.get("create_time")),
    )

    raw_comments = raw.get("comments") or []
    child_reply_counts: dict[str, int] = {}
    for c in raw_comments:
        if not isinstance(c, dict):
            continue
        parent = _clean_opt_str(c.get("parent"))
        if parent and parent.lower() != "root":
            child_reply_counts[parent] = child_reply_counts.get(parent, 0) + 1

    mapped_comments: list[dict[str, Any]] = []
    for idx, c in enumerate(raw_comments):
        if not isinstance(c, dict):
            continue
        norm_c = map_tiktok_comment_to_input(c, canonical_vid=canonical_vid, idx=idx)
        if norm_c is None:
            continue
        cid = norm_c["comment_id"]
        if cid in child_reply_counts and norm_c["reply_count"] == 0:
            norm_c["reply_count"] = child_reply_counts[cid]
        mapped_comments.append(norm_c)

    caption = str(raw.get("description") if raw.get("description") is not None else (raw.get("title") or ""))
    tags: list[str] = []
    seen_tags: set[str] = set()
    for t in raw.get("tags") or []:
        clean_t = _clean_opt_str(t)
        if clean_t:
            nt = clean_t.lstrip("#").strip()
            if nt and nt.lower() not in seen_tags:
                seen_tags.add(nt.lower())
                tags.append(nt)
    if not tags and caption:
        for m in _CAPTION_HASHTAG_RE.finditer(caption):
            nt = m.group(1).strip()
            if nt and nt.lower() not in seen_tags:
                seen_tags.add(nt.lower())
                tags.append(nt)

    poi_obj = _as_dict(raw.get("poi"))
    now_utc_iso = collected_at_utc or datetime.now(UTC).isoformat()
    raw_snapshot = {k: v for k, v in raw.items() if k != "formats"}
    raw_snapshot.setdefault("collectTime", int(datetime.now(UTC).timestamp()))

    detail = {
        "video_id": canonical_vid,
        "author_id": _clean_opt_str(raw.get("uploader_id") or raw.get("channel_id"))
        or f"author_{canonical_vid}",
        "author_handle": handle,
        "author_nickname": _clean_opt_str(raw.get("creator") or raw.get("channel") or raw.get("uploader"))
        or handle,
        "follower_count": _safe_nonneg_int(raw.get("channel_follower_count")),
        "create_time": iso_ct,
        "caption": caption,
        "hashtags": tags,
        "duration_sec": _safe_nonneg_int(raw.get("duration")),
        "play_count": _safe_nonneg_int(raw.get("view_count")),
        "digg_count": _safe_nonneg_int(raw.get("like_count")),
        "comment_count": max(_safe_nonneg_int(raw.get("comment_count")), len(mapped_comments)),
        "share_count": _safe_nonneg_int(
            raw.get("repost_count") if raw.get("repost_count") is not None else raw.get("share_count")
        ),
        "collect_count": _safe_nonneg_int(
            raw.get("collect_count") if raw.get("collect_count") is not None else raw.get("save_count")
        ),
        "is_ad": _to_bool_flag(raw.get("is_ad") or raw.get("isAd")),
        "is_ec_video": _to_bool_flag(raw.get("is_ec_video") or raw.get("isECVideo")),
        "is_pinned_item": _to_bool_flag(raw.get("is_pinned") or raw.get("isPinnedItem")),
        "playlist_id": _clean_opt_str(raw.get("playlist_id") or raw.get("playlistId")),
        "poi_id": _clean_opt_str(poi_obj.get("id") or raw.get("poi_id")),
        "poi_name": _clean_opt_str(poi_obj.get("name") or raw.get("poi_name") or raw.get("location")),
        "poi_address": _clean_opt_str(poi_obj.get("address") or raw.get("poi_address")),
        "poi_city": _clean_opt_str(poi_obj.get("city") or raw.get("poi_city")),
        "poi_category_tiny": _clean_opt_str(poi_obj.get("ttTypeNameTiny") or raw.get("poi_category_tiny")),
        "tiktok_url": url,
        "transcript": "",
        "collected_at_utc": now_utc_iso,
        "_raw_provider_payload": raw_snapshot,
    }
    return detail, mapped_comments
