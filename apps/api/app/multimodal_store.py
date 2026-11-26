"""Read-only verified multimodal Gold store (comments, voice segments, prosody, disclosure) for API & /demo/."""

from __future__ import annotations

import hashlib
import json
import math
import os
import statistics
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq

from packages.absa.disclosure import analyze_disclosure_and_promo
from packages.data_contracts.multimodal import RawCommentInput, RawWhisperSegment
from packages.prosody import (
    PROSODY_DESCRIPTIVE_NOTE,
    audit_temporal_invariants,
    normalize_timestamp_source,
)

REPO_ROOT = Path(__file__).resolve().parents[3]

_CANDIDATE_MULTIMODAL_SNAPSHOTS: tuple[str, ...] = (
    "data/corpus/m3_3_playwright_comments_20261125_v5",
    "data/corpus/m3_3_pilot_snapshot_v2",
    "data/corpus/m3_3_pilot_snapshot_v1",
)
_M4_1_RECEIPT_REL = Path("docs/reports/milestones/M4.1/evidence/m4_1_audio_pilot_receipt.json")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _clean_float(val: Any) -> float | None:
    if val is None:
        return None
    try:
        f = float(val)
    except (TypeError, ValueError):
        return None
    return round(f, 4) if math.isfinite(f) else None


def _clean_str_list(val: Any) -> list[str]:
    if isinstance(val, (list, tuple)):
        return [str(x).strip() for x in val if str(x).strip()]
    return []


@dataclass(frozen=True)
class MultimodalCorpusStore:
    """In-memory index over Gold fact_comments, fact_voice_segments, and M4.1 prosody receipts."""

    available: bool
    snapshot_id: str | None
    snapshot_dir: Path | None
    videos_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    comments_by_video: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    voice_segments_by_video: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    video_prosody_by_id: dict[str, dict[str, Any]] = field(default_factory=dict)
    total_comments: int = 0
    total_voice_segments: int = 0

    @property
    def videos_with_comments(self) -> int:
        return sum(1 for rows in self.comments_by_video.values() if rows)

    @property
    def videos_with_voice_segments(self) -> int:
        return sum(1 for rows in self.voice_segments_by_video.values() if rows)

    @property
    def videos_with_prosody_audio(self) -> int:
        return len(self.video_prosody_by_id)

    @classmethod
    def empty(cls) -> MultimodalCorpusStore:
        return cls(available=False, snapshot_id=None, snapshot_dir=None)

    @classmethod
    def from_repo_defaults(
        cls,
        *,
        primary_corpus_dir: Path | None = None,
        repo_root: Path | None = None,
    ) -> MultimodalCorpusStore:
        root = repo_root or REPO_ROOT
        env_override = os.environ.get("TIKTOK_RAG_MULTIMODAL_CORPUS_DIR", "").strip()
        candidates: list[Path] = []
        if env_override:
            p_env = Path(env_override)
            target_env = p_env if p_env.is_absolute() else (root / p_env)
            return cls.from_snapshot_dir(target_env, repo_root=root)

        data_corpus_root = (root / "data" / "corpus").resolve()
        if primary_corpus_dir is not None:
            p_prim = (
                primary_corpus_dir
                if primary_corpus_dir.is_absolute()
                else (root / primary_corpus_dir)
            )
            # If caller passed an isolated custom corpus outside data/corpus, honor it first.
            if p_prim.resolve().parent != data_corpus_root:
                candidates.append(p_prim)
        for rel in _CANDIDATE_MULTIMODAL_SNAPSHOTS:
            candidates.append(root / rel)
        if primary_corpus_dir is not None:
            p_prim = (
                primary_corpus_dir
                if primary_corpus_dir.is_absolute()
                else (root / primary_corpus_dir)
            )
            candidates.append(p_prim)

        seen: set[Path] = set()
        for cand in candidates:
            resolved = cand.resolve()
            if resolved in seen:
                continue
            seen.add(resolved)
            store = cls.from_snapshot_dir(cand, repo_root=root)
            if store.available and (store.total_comments > 0 or store.total_voice_segments > 0):
                return store
        return cls.empty()

    @classmethod
    def from_snapshot_dir(
        cls,
        snapshot_dir: Path,
        *,
        repo_root: Path | None = None,
    ) -> MultimodalCorpusStore:
        root = repo_root or REPO_ROOT
        manifest_path = snapshot_dir / "manifest.json"
        comments_path = snapshot_dir / "fact_comments.parquet"
        voice_path = snapshot_dir / "fact_voice_segments.parquet"
        videos_path = snapshot_dir / "fact_videos.parquet"
        if not (
            snapshot_dir.is_dir()
            and manifest_path.is_file()
            and comments_path.is_file()
            and voice_path.is_file()
            and videos_path.is_file()
        ):
            return cls.empty()

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        expected_hashes: dict[str, str] = {
            str(entry["filename"]): str(entry["sha256"])
            for entry in (manifest.get("files") or [])
            if isinstance(entry, dict) and "filename" in entry and "sha256" in entry
        }
        for fname, fpath in (
            ("fact_comments.parquet", comments_path),
            ("fact_voice_segments.parquet", voice_path),
        ):
            expected = expected_hashes.get(fname)
            if expected and _sha256_file(fpath) != expected:
                raise ValueError(f"SHA256 mismatch on multimodal table {fpath}")

        comment_rows = pq.read_table(comments_path).to_pylist()
        voice_rows = pq.read_table(voice_path).to_pylist()
        if not comment_rows and not voice_rows:
            return cls.empty()

        comments_by_video: dict[str, list[dict[str, Any]]] = {}
        for row in comment_rows:
            vid = str(row.get("video_id") or "").strip()
            cid = str(row.get("comment_id") or "").strip()
            txt = str(row.get("original_text") or row.get("text") or "").strip()
            if not vid or not cid or not txt:
                continue
            comments_by_video.setdefault(vid, []).append(
                {
                    "comment_id": cid,
                    "video_id": vid,
                    "author_handle": str(row.get("author_handle") or "viewer").strip(),
                    "text": txt,
                    "like_count": max(0, int(row.get("like_count") or 0)),
                    "reply_count": max(0, int(row.get("reply_count") or 0)),
                }
            )

        voice_by_video: dict[str, list[dict[str, Any]]] = {}
        for row in voice_rows:
            vid = str(row.get("video_id") or "").strip()
            sid = str(row.get("segment_id") or "").strip()
            txt = str(row.get("text") or "").strip()
            if not vid or not sid or not txt:
                continue
            raw_src = str(row.get("timestamp_source") or "audio_derived")
            norm_src = normalize_timestamp_source(raw_src)
            voice_by_video.setdefault(vid, []).append(
                {
                    "segment_id": sid,
                    "video_id": vid,
                    "seq_no": max(0, int(row.get("seq_no") or 0)),
                    "start_sec": max(0.0, float(row.get("start_sec") or 0.0)),
                    "end_sec": max(0.0, float(row.get("end_sec") or 0.0)),
                    "timestamp_source": norm_src,
                    "text": txt,
                    "words_per_sec": max(0.0, float(row.get("words_per_sec") or 0.0)),
                    "pitch_std": _clean_float(row.get("pitch_std")),
                    "energy_cv": _clean_float(row.get("energy_cv")),
                }
            )
        for segs in voice_by_video.values():
            segs.sort(key=lambda s: (int(s["seq_no"]), float(s["start_sec"])))

        video_prosody_by_id: dict[str, dict[str, Any]] = {}
        m4_1_path = root / _M4_1_RECEIPT_REL
        if m4_1_path.is_file():
            m4_1_data = json.loads(m4_1_path.read_text(encoding="utf-8"))
            for item in m4_1_data.get("per_video_prosody") or []:
                if isinstance(item, dict) and item.get("video_id"):
                    v_id = str(item["video_id"]).strip()
                    video_prosody_by_id[v_id] = {
                        "video_id": v_id,
                        "decoded_duration_sec": _clean_float(item.get("decoded_duration_sec")),
                        "pitch_std": _clean_float(item.get("pitch_std")),
                        "energy_cv": _clean_float(item.get("energy_cv")),
                        "voiced_frame_count": int(item.get("voiced_frame_count") or 0),
                        "active_frame_count": int(item.get("active_frame_count") or 0),
                        "audio_bytes": int(item.get("audio_bytes") or 0),
                    }

        absa_ids: set[str] = set()
        absa_path = snapshot_dir / "fact_absa_reviews.parquet"
        if absa_path.is_file():
            expected_absa = expected_hashes.get("fact_absa_reviews.parquet")
            if expected_absa and _sha256_file(absa_path) != expected_absa:
                raise ValueError(f"SHA256 mismatch on multimodal table {absa_path}")
            for row in pq.read_table(absa_path, columns=["video_id"]).to_pylist():
                v_absa = str(row.get("video_id") or "").strip()
                if v_absa:
                    absa_ids.add(v_absa)

        target_ids = sorted(
            set(comments_by_video) | set(voice_by_video) | set(video_prosody_by_id) | absa_ids
        )
        wanted_cols = [
            "video_id",
            "author_handle",
            "author_nickname",
            "caption",
            "transcript",
            "hashtags",
            "duration_sec",
            "play_count",
            "digg_count",
            "comment_count",
            "is_ad",
            "is_ec_video",
            "food_category",
            "video_format",
            "price_tier",
            "city_norm",
            "district_norm",
            "poi_name",
        ]
        schema_names = set(pq.read_schema(videos_path).names)
        read_cols = [c for c in wanted_cols if c in schema_names]
        vid_table = pq.read_table(
            videos_path,
            columns=read_cols,
            filters=[("video_id", "in", target_ids)],
        )
        videos_by_id: dict[str, dict[str, Any]] = {}
        for row in vid_table.to_pylist():
            vid = str(row.get("video_id") or "").strip()
            if not vid:
                continue
            handle = str(row.get("author_handle") or "creator").strip()
            caption = str(row.get("caption") or "").strip()
            raw_tr = str(row.get("transcript") or "").strip()
            segs = voice_by_video.get(vid, [])
            joined_segs = " ".join(str(s["text"]) for s in segs).strip()
            effective_tr = raw_tr or joined_segs or caption or f"Video TikTok F&B {vid}"
            if len(effective_tr) < 5:
                effective_tr = f"{effective_tr} ({vid})"
            videos_by_id[vid] = {
                "video_id": vid,
                "author_handle": handle,
                "author_nickname": str(row.get("author_nickname") or "").strip(),
                "tiktok_url": f"https://www.tiktok.com/@{handle}/video/{vid}",
                "caption": caption,
                "transcript": effective_tr,
                "has_spoken_transcript": bool(raw_tr or joined_segs),
                "hashtags": _clean_str_list(row.get("hashtags")),
                "duration_sec": max(0, int(row.get("duration_sec") or 0)),
                "play_count": max(0, int(row.get("play_count") or 0)),
                "digg_count": max(0, int(row.get("digg_count") or 0)),
                "platform_comment_count": max(0, int(row.get("comment_count") or 0)),
                "is_ad": bool(row.get("is_ad", False)),
                "is_ec_video": bool(row.get("is_ec_video", False)),
                "food_category": str(row.get("food_category") or "").strip() or None,
                "video_format": str(row.get("video_format") or "").strip() or None,
                "price_tier": str(row.get("price_tier") or "").strip() or None,
                "city_norm": str(row.get("city_norm") or "").strip() or None,
                "district_norm": str(row.get("district_norm") or "").strip() or None,
                "poi_name": str(row.get("poi_name") or "").strip() or None,
            }

        total_cmts = sum(len(v) for v in comments_by_video.values())
        total_segs = sum(len(v) for v in voice_by_video.values())
        return cls(
            available=True,
            snapshot_id=str(manifest.get("snapshot_id") or snapshot_dir.name),
            snapshot_dir=snapshot_dir,
            videos_by_id=videos_by_id,
            comments_by_video=comments_by_video,
            voice_segments_by_video=voice_by_video,
            video_prosody_by_id=video_prosody_by_id,
            total_comments=total_cmts,
            total_voice_segments=total_segs,
        )

    def list_videos(
        self,
        *,
        require_voice: bool = False,
        min_comments: int = 1,
        limit: int = 60,
    ) -> list[dict[str, Any]]:
        if not self.available:
            return []
        items: list[dict[str, Any]] = []
        for vid, meta in self.videos_by_id.items():
            cmts = self.comments_by_video.get(vid, [])
            segs = self.voice_segments_by_video.get(vid, [])
            v_pros = self.video_prosody_by_id.get(vid)
            if len(cmts) < max(0, min_comments):
                continue
            if require_voice and not segs and v_pros is None:
                continue
            provenance = (
                "audio_derived"
                if any(s["timestamp_source"] == "audio_derived" for s in segs) or v_pros is not None
                else "wps_estimated"
            )
            preview = (meta["caption"] or meta["transcript"])[:90]
            items.append(
                {
                    "video_id": vid,
                    "author_handle": meta["author_handle"],
                    "tiktok_url": meta["tiktok_url"],
                    "caption_preview": preview,
                    "food_category": meta["food_category"],
                    "city_norm": meta["city_norm"],
                    "duration_sec": meta["duration_sec"],
                    "play_count": meta["play_count"],
                    "is_ad": meta["is_ad"],
                    "is_ec_video": meta["is_ec_video"],
                    "comment_count": len(cmts),
                    "voice_segment_count": len(segs),
                    "has_prosody_audio": v_pros is not None,
                    "timestamp_provenance": provenance,
                }
            )
        items.sort(
            key=lambda x: (
                1 if x["voice_segment_count"] > 0 else 0,
                1 if x["has_prosody_audio"] else 0,
                int(x["comment_count"]),
                int(x["play_count"]),
                str(x["video_id"]),
            ),
            reverse=True,
        )
        return items[: max(1, min(limit, 200))]

    def get_video_bundle(self, video_id: str) -> dict[str, Any] | None:
        clean_id = (video_id or "").strip()
        if not self.available or not clean_id or clean_id not in self.videos_by_id:
            return None
        meta = dict(self.videos_by_id[clean_id])
        meta["snapshot_id"] = self.snapshot_id
        cmts = [dict(c) for c in self.comments_by_video.get(clean_id, [])]
        segs = [dict(s) for s in self.voice_segments_by_video.get(clean_id, [])]
        v_pros = self.video_prosody_by_id.get(clean_id)

        max_seg_end = max((float(s["end_sec"]) for s in segs), default=0.0)
        decoded_dur = float(v_pros["decoded_duration_sec"]) if (v_pros and v_pros.get("decoded_duration_sec")) else 0.0
        effective_media_dur = max(float(meta["duration_sec"]), decoded_dur, max_seg_end, 1.0)

        if segs:
            invariant_audit = audit_temporal_invariants(
                segs,
                media_duration_by_video={clean_id: effective_media_dur},
                known_video_ids=[clean_id],
            )
        else:
            invariant_audit = {
                "total_segments": 0,
                "valid_segments": 0,
                "invariant_violation_count": 0,
                "invariant_pass_rate": 1.0,
                "meets_100pct_invariant_gate": True,
                "timestamp_source_counts": {"audio_derived": 0, "wps_estimated": 0},
                "violations_sample": [],
            }

        wps_vals = [float(s["words_per_sec"]) for s in segs if float(s["words_per_sec"]) > 0.0]
        seg_pitch = [float(s["pitch_std"]) for s in segs if s.get("pitch_std") is not None]
        seg_energy = [float(s["energy_cv"]) for s in segs if s.get("energy_cv") is not None]
        mean_pitch = (
            round(statistics.mean(seg_pitch), 4)
            if seg_pitch
            else (v_pros.get("pitch_std") if v_pros else None)
        )
        mean_energy = (
            round(statistics.mean(seg_energy), 4)
            if seg_energy
            else (v_pros.get("energy_cv") if v_pros else None)
        )
        prosody_summary: dict[str, Any] = {
            "segment_count": len(segs),
            "audio_derived_segments": sum(
                1 for s in segs if s["timestamp_source"] == "audio_derived"
            ),
            "wps_estimated_segments": sum(
                1 for s in segs if s["timestamp_source"] == "wps_estimated"
            ),
            "decoded_audio_duration_sec": v_pros.get("decoded_duration_sec") if v_pros else None,
            "median_words_per_sec": round(statistics.median(wps_vals), 4) if wps_vals else None,
            "mean_pitch_std_hz": mean_pitch,
            "mean_energy_cv": mean_energy,
            "voiced_frame_count": v_pros.get("voiced_frame_count") if v_pros else None,
            "descriptive_note": PROSODY_DESCRIPTIVE_NOTE,
            "temporal_invariants": invariant_audit,
            "voice_segments": segs,
        }

        disc = analyze_disclosure_and_promo(
            caption=meta["caption"],
            transcript=meta["transcript"],
            is_ad=bool(meta["is_ad"]),
            is_ec_video=bool(meta["is_ec_video"]),
            hashtags=meta["hashtags"],
        )
        disclosure_summary: dict[str, Any] = {
            "disclosure_flag_status": disc.disclosure_flag_status,
            "matched_indicators": disc.matched_indicators,
            "matched_categories": disc.matched_categories,
            "lexical_promo_score": disc.lexical_promo_score,
            "sponsorship_ground_truth_status": disc.sponsorship_ground_truth_status,
            "disclosure_target_note": disc.disclosure_target_note,
        }

        raw_comment_models = [
            RawCommentInput(
                comment_id=c["comment_id"],
                author_handle=c["author_handle"],
                text=c["text"],
                like_count=c["like_count"],
                reply_count=c["reply_count"],
            )
            for c in cmts
        ]
        raw_utterances = [
            RawWhisperSegment(
                start_sec=float(s["start_sec"]),
                end_sec=max(float(s["start_sec"]), float(s["end_sec"])),
                text=str(s["text"]),
            )
            for s in segs
        ]

        return {
            "video": meta,
            "comments": cmts,
            "voice_segments": segs,
            "raw_comment_models": raw_comment_models,
            "raw_utterance_models": raw_utterances,
            "prosody_and_timing": prosody_summary,
            "disclosure_and_promo": disclosure_summary,
        }
