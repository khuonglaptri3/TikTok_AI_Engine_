from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

from packages.prosody.extractor import normalize_timestamp_source

TOKENIZATION_SPEC = (
    "Unicode NFC -> lowercase -> strip non-word punctuation -> "
    "WER splits on whitespace word tokens; CER iterates non-whitespace characters."
)

_NON_ALNUM_SPACE_RE = re.compile(r"[^\w\s]+", flags=re.UNICODE)
_WHITESPACE_RE = re.compile(r"\s+")


def _normalize_text(text: str) -> str:
    nfc = unicodedata.normalize("NFC", str(text or "")).lower().replace("_", " ")
    no_punct = _NON_ALNUM_SPACE_RE.sub(" ", nfc)
    return _WHITESPACE_RE.sub(" ", no_punct).strip()


def tokenize_vi_words(text: str) -> list[str]:
    """Normalize text under TOKENIZATION_SPEC and split into word tokens."""
    norm = _normalize_text(text)
    return norm.split() if norm else []


def tokenize_vi_chars(text: str) -> list[str]:
    """Normalize text under TOKENIZATION_SPEC and emit non-whitespace character tokens."""
    norm = _normalize_text(text).replace(" ", "")
    return list(norm)


def compute_levenshtein_distance(
    ref: Sequence[str],
    hyp: Sequence[str],
) -> tuple[int, int, int, int]:
    """Return exact (total_edits, substitutions, deletions, insertions) between ref and hyp sequences."""
    n = len(ref)
    m = len(hyp)
    # Track (cost, subs, dels, ins) cleanly via DP matrix of tuples
    dp: list[list[tuple[int, int, int, int]]] = [
        [(0, 0, 0, 0) for _ in range(m + 1)] for _ in range(n + 1)
    ]
    for i in range(1, n + 1):
        dp[i][0] = (i, 0, i, 0)
    for j in range(1, m + 1):
        dp[0][j] = (j, 0, 0, j)

    for i in range(1, n + 1):
        r_tok = ref[i - 1]
        for j in range(1, m + 1):
            h_tok = hyp[j - 1]
            sub_cost = 0 if r_tok == h_tok else 1
            c_sub = dp[i - 1][j - 1]
            cand_sub = (c_sub[0] + sub_cost, c_sub[1] + sub_cost, c_sub[2], c_sub[3])

            c_del = dp[i - 1][j]
            cand_del = (c_del[0] + 1, c_del[1], c_del[2] + 1, c_del[3])

            c_ins = dp[i][j - 1]
            cand_ins = (c_ins[0] + 1, c_ins[1], c_ins[2], c_ins[3] + 1)

            dp[i][j] = min(cand_sub, cand_del, cand_ins, key=lambda item: item[0])

    return dp[n][m]


def evaluate_m4_1_reference_set(
    rows: Sequence[Mapping[str, Any]],
    *,
    is_real_human_verified: bool,
    invariant_pass_rate: float,
    min_utterances: int = 50,
    max_sampled_audio_minutes: float = 20.0,
) -> dict[str, Any]:
    """Compute WER, CER, boundary error quantiles, and fail-closed precise_playback_allowed gate."""
    verified = [r for r in rows if r.get("human_verified") is True]
    total_word_edits = 0
    total_ref_words = 0
    total_char_edits = 0
    total_ref_chars = 0
    all_abs_errs: list[float] = []
    start_errs: list[float] = []
    end_errs: list[float] = []
    video_audio_sec: dict[str, float] = {}

    for r in verified:
        vid = str(r.get("video_id") or "").strip()
        dur_val = r.get("audio_duration_sec")
        if vid and dur_val is not None:
            video_audio_sec[vid] = max(video_audio_sec.get(vid, 0.0), float(dur_val))

        ref_text = str(r.get("ref_text") or "")
        pred_text = str(r.get("pred_text") or "")

        rw = tokenize_vi_words(ref_text)
        pw = tokenize_vi_words(pred_text)
        w_edits, _, _, _ = compute_levenshtein_distance(rw, pw)
        total_word_edits += w_edits
        total_ref_words += len(rw)

        rc = tokenize_vi_chars(ref_text)
        pc = tokenize_vi_chars(pred_text)
        c_edits, _, _, _ = compute_levenshtein_distance(rc, pc)
        total_char_edits += c_edits
        total_ref_chars += len(rc)

        ps = r.get("pred_start_sec")
        pe = r.get("pred_end_sec")
        rs = r.get("ref_start_sec")
        re_ = r.get("ref_end_sec")
        if ps is not None and pe is not None and rs is not None and re_ is not None:
            s_err = abs(float(ps) - float(rs))
            e_err = abs(float(pe) - float(re_))
            if math.isfinite(s_err) and math.isfinite(e_err):
                start_errs.append(s_err)
                end_errs.append(e_err)
                all_abs_errs.extend([s_err, e_err])

    sampled_min = round(sum(video_audio_sec.values()) / 60.0, 3) if video_audio_sec else 0.0
    wer = round(total_word_edits / total_ref_words, 4) if total_ref_words > 0 else None
    cer = round(total_char_edits / total_ref_chars, 4) if total_ref_chars > 0 else None

    if all_abs_errs:
        arr = np.asarray(all_abs_errs, dtype=np.float64)
        median_err = round(float(np.median(arr)), 4)
        p95_err = round(float(np.percentile(arr, 95)), 4)
    else:
        median_err = None
        p95_err = None

    meets_count = len(verified) >= min_utterances
    meets_audio_cap = sampled_min <= max_sampled_audio_minutes + 1e-9
    meets_inv = invariant_pass_rate >= 1.0 - 1e-9
    meets_med = median_err is not None and median_err <= 1.0
    meets_p95 = p95_err is not None and p95_err <= 3.0

    precise_allowed = bool(
        is_real_human_verified
        and meets_count
        and meets_audio_cap
        and meets_inv
        and meets_med
        and meets_p95
    )

    return {
        "tokenization_spec": TOKENIZATION_SPEC,
        "is_real_human_verified": bool(is_real_human_verified),
        "evaluated_utterance_count": len(verified),
        "min_utterances_required": min_utterances,
        "unique_video_count": len(video_audio_sec),
        "total_sampled_audio_minutes": sampled_min,
        "max_sampled_audio_minutes_cap": max_sampled_audio_minutes,
        "total_ref_words": total_ref_words,
        "total_ref_chars": total_ref_chars,
        "wer": wer,
        "cer": cer,
        "boundary_sample_count": len(all_abs_errs),
        "boundary_median_abs_err_sec": median_err,
        "boundary_p95_abs_err_sec": p95_err,
        "meets_median_1s_gate": meets_med,
        "meets_p95_3s_gate": meets_p95,
        "meets_100pct_invariant_gate": meets_inv,
        "precise_playback_allowed": precise_allowed,
        "abstain_precise_playback": not precise_allowed,
    }


def build_m4_1_reference_pool(
    segments: Sequence[Mapping[str, Any]],
    *,
    media_duration_by_video: Mapping[str, float],
    target_utterances: int = 60,
    overlap_utterances: int = 16,
    max_pilot_audio_minutes: float = 60.0,
    max_sampled_audio_minutes: float = 20.0,
    seed: int = 42,
) -> list[dict[str, Any]]:
    """Sample >=50 utterances strictly within <=20 audio minutes for blinded K & N reference review."""
    total_pilot_min = sum(float(v) for v in media_duration_by_video.values()) / 60.0
    if total_pilot_min > max_pilot_audio_minutes + 1e-9:
        raise ValueError(
            f"Total pilot audio ({total_pilot_min:.2f} min) exceeds {max_pilot_audio_minutes:.1f}-minute ceiling"
        )
    if target_utterances < 50:
        raise ValueError(f"target_utterances must be >= 50, got {target_utterances!r}")

    by_vid: dict[str, list[dict[str, Any]]] = {}
    for seg in segments:
        vid = str(seg.get("video_id") or "").strip()
        if not vid or vid not in media_duration_by_video:
            continue
        prov = normalize_timestamp_source(str(seg.get("timestamp_source") or ""))
        if prov != "audio_derived":
            continue
        by_vid.setdefault(vid, []).append(dict(seg))

    if not by_vid:
        raise ValueError("No audio_derived segments with known media durations available for pool")

    # Select videos in sorted deterministic order while respecting <= max_sampled_audio_minutes
    selected_vids: list[str] = []
    acc_sec = 0.0
    for vid in sorted(by_vid):
        dur = float(media_duration_by_video[vid])
        if (acc_sec + dur) / 60.0 <= max_sampled_audio_minutes + 1e-9:
            selected_vids.append(vid)
            acc_sec += dur

    if not selected_vids:
        raise ValueError("No pilot videos fit inside max_sampled_audio_minutes cap")

    # Sort each video's utterances by seq_no/start_sec and pick round-robin to keep coverage even
    for vid in selected_vids:
        by_vid[vid].sort(key=lambda r: (int(r.get("seq_no") or 0), float(r.get("start_sec") or 0.0)))

    picked: list[dict[str, Any]] = []
    idx = 0
    while len(picked) < target_utterances:
        progressed = False
        for vid in selected_vids:
            v_list = by_vid[vid]
            if idx < len(v_list):
                picked.append(v_list[idx])
                progressed = True
                if len(picked) >= target_utterances:
                    break
        if not progressed:
            break
        idx += 1

    if len(picked) < 50:
        raise ValueError(f"Only {len(picked)} audio_derived utterances fit within {max_sampled_audio_minutes}m cap (< 50)")

    # Preserve video contiguity in output while assigning double-review overlap deterministically
    rng = np.random.default_rng(seed)
    n_overlap = min(max(0, overlap_utterances), len(picked))
    perm = list(range(len(picked)))
    rng.shuffle(perm)
    overlap_idx = set(perm[:n_overlap])
    singles = perm[n_overlap:]
    n_half = len(singles) // 2
    n_only_idx = set(singles[:n_half])

    vid_order = {vid: i for i, vid in enumerate(selected_vids)}
    enriched: list[tuple[int, int, dict[str, Any]]] = []
    for pos, seg in enumerate(picked):
        vid = str(seg["video_id"]).strip()
        if pos in overlap_idx:
            assignment = "double_review_N_K"
        elif pos in n_only_idx:
            assignment = "N_only"
        else:
            assignment = "K_only"
        seq_num = int(seg.get("seq_no") or 0)
        row: dict[str, Any] = {
            "segment_id": str(seg["segment_id"]),
            "video_id": vid,
            "seq_no": seq_num,
            "audio_duration_sec": round(float(media_duration_by_video[vid]), 4),
            "timestamp_provenance": "audio_derived",
            "pred_start_sec": round(float(seg["start_sec"]), 4),
            "pred_end_sec": round(float(seg["end_sec"]), 4),
            "pred_text": str(seg["text"]),
            "review_assignment": assignment,
            "human_verified": False,
            "ref_start_sec": None,
            "ref_end_sec": None,
            "ref_text": "",
            "reviewer_notes": "",
        }
        enriched.append((vid_order[vid], seq_num, row))

    enriched.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in enriched]
