"""M5.2 video-disjoint ABSA evaluator, NFC span auditor, IAA, and blinded pool builder."""
from __future__ import annotations

import unicodedata
from collections import Counter
from collections.abc import Sequence
from typing import Any

import numpy as np
import pandas as pd

from packages.absa.spans import TextUnitInput, summarize_units_aspects
from packages.data_contracts.multimodal import (
    ASPECT_NAMES,
    AspectName,
    AspectSpanEvidence,
    TextUnitSourceKind,
)

VALID_ASPECT_STATES: tuple[str, ...] = (
    "absent_unknown",
    "negative",
    "neutral",
    "positive",
)
_VALID_STATE_SET: frozenset[str] = frozenset(VALID_ASPECT_STATES)
OBSERVED_SENTIMENT_STATES: tuple[str, ...] = ("positive", "neutral", "negative")


def _require_valid_aspect_state(val: object, field_name: str) -> str:
    if val is None or not isinstance(val, str):
        raise ValueError(
            f"{field_name} must be a non-null string in VALID_ASPECT_STATES, got {val!r}"
        )
    cleaned = val.strip()
    if cleaned not in _VALID_STATE_SET:
        raise ValueError(
            f"Invalid {field_name} {cleaned!r}; allowed: {VALID_ASPECT_STATES}"
        )
    return cleaned


def _require_aspect_state_map(mapping: object, field_name: str) -> dict[AspectName, str]:
    if not isinstance(mapping, dict):
        raise ValueError(f"{field_name} must be a dict keyed by {ASPECT_NAMES}, got {type(mapping).__name__}")
    out: dict[AspectName, str] = {}
    for aspect in ASPECT_NAMES:
        if aspect not in mapping:
            raise ValueError(f"Missing aspect {aspect!r} in {field_name}")
        out[aspect] = _require_valid_aspect_state(mapping[aspect], f"{field_name}[{aspect!r}]")
    return out


def predict_unit_aspects(
    unit: TextUnitInput,
    *,
    polarity_tau: float = 0.15,
) -> tuple[dict[AspectName, str], list[AspectSpanEvidence]]:
    """Predict 4-state aspect labels and NFC-exact spans for a single text unit."""
    summaries, spans, _ = summarize_units_aspects(
        [unit],
        min_support_units=1,
        polarity_tau=polarity_tau,
    )
    pred_map: dict[AspectName, str] = {}
    for aspect in ASPECT_NAMES:
        summary = summaries[aspect]
        if summary.presence_status == "absent_unknown":
            pred_map[aspect] = "absent_unknown"
        else:
            pred_map[aspect] = str(summary.polarity_label)
    return pred_map, spans


def split_units_by_video(
    rows: list[dict[str, Any]],
    *,
    video_id_col: str = "video_id",
    dev_ratio: float = 0.5,
    seed: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    """Partition text units strictly by video_id into disjoint dev and held_out splits."""
    if not (0.0 < dev_ratio < 1.0):
        raise ValueError(f"dev_ratio must satisfy 0.0 < dev_ratio < 1.0, got {dev_ratio!r}")

    vids_set: set[str] = set()
    for row in rows:
        raw_vid = row.get(video_id_col)
        if raw_vid is None or not str(raw_vid).strip():
            raise ValueError(f"Missing or blank {video_id_col} in unit row")
        vids_set.add(str(raw_vid).strip())

    unique_vids = sorted(vids_set)
    if len(unique_vids) < 2:
        raise ValueError(
            f"Need at least 2 distinct {video_id_col} values for video-disjoint split, got {len(unique_vids)}"
        )

    rng = np.random.default_rng(seed)
    shuffled = list(unique_vids)
    rng.shuffle(shuffled)

    n_dev = max(1, min(len(unique_vids) - 1, round(len(unique_vids) * dev_ratio)))
    dev_vids = set(shuffled[:n_dev])

    dev_rows: list[dict[str, Any]] = []
    held_rows: list[dict[str, Any]] = []
    for row in rows:
        vid = str(row[video_id_col]).strip()
        if vid in dev_vids:
            dev_rows.append(row)
        else:
            held_rows.append(row)

    return {"dev": dev_rows, "held_out": held_rows}


def audit_source_span_validity(
    units_by_id: dict[str, str],
    spans: Sequence[AspectSpanEvidence | dict[str, Any]],
) -> dict[str, Any]:
    """Verify every extracted or annotated span aligns 1-to-1 with NFC-normalized unit text."""
    nfc_map: dict[str, str] = {}
    for uid, text in units_by_id.items():
        if isinstance(uid, str) and isinstance(text, str):
            nfc_text = unicodedata.normalize("NFC", text)
            nfc_map[uid] = nfc_text
            stripped_uid = uid.strip()
            if stripped_uid and stripped_uid not in nfc_map:
                nfc_map[stripped_uid] = nfc_text

    total = len(spans)
    valid = 0
    invalid_examples: list[dict[str, Any]] = []

    for sp in spans:
        if isinstance(sp, AspectSpanEvidence):
            unit_id: object = sp.unit_id
            aspect: object = sp.aspect
            start_char: object = sp.start_char
            end_char: object = sp.end_char
            span_text: object = sp.span_text
        elif isinstance(sp, dict):
            unit_id = sp.get("unit_id")
            aspect = sp.get("aspect")
            start_char = sp.get("start_char")
            end_char = sp.get("end_char")
            span_text = sp.get("span_text")
        else:
            invalid_examples.append({"span": repr(sp), "reason": "invalid_span_record_type"})
            continue

        reason: str | None = None
        if not isinstance(unit_id, str) or unit_id not in nfc_map:
            reason = "missing_unit_id"
        elif type(start_char) is not int or type(end_char) is not int:
            reason = "non_int_offsets"
        elif not isinstance(span_text, str) or not bool(span_text.strip()):
            reason = "blank_or_non_str_span_text"
        else:
            target_nfc = nfc_map[unit_id]
            if not (0 <= start_char < end_char <= len(target_nfc)):
                reason = "offset_out_of_bounds"
            elif target_nfc[start_char:end_char] != span_text:
                reason = "slice_text_mismatch"

        if reason is None:
            valid += 1
        else:
            invalid_examples.append(
                {
                    "unit_id": unit_id,
                    "aspect": aspect,
                    "start_char": start_char,
                    "end_char": end_char,
                    "span_text": span_text,
                    "reason": reason,
                }
            )

    return {
        "total_spans": total,
        "valid_spans": valid,
        "invalid_spans": total - valid,
        "validity_rate": round(valid / total, 4) if total > 0 else 1.0,
        "meets_95pct_gate": (valid / total >= 0.95) if total > 0 else True,
        "invalid_examples": invalid_examples[:10],
    }


def _agreement_and_kappa(y_a: list[str], y_b: list[str]) -> tuple[float, float]:
    if not y_a:
        return 0.0, 0.0
    total = len(y_a)
    p_o = sum(1 for a, b in zip(y_a, y_b) if a == b) / total
    labels = sorted(set(y_a) | set(y_b))
    counts_a = Counter(y_a)
    counts_b = Counter(y_b)
    p_e = sum((counts_a[lbl] / total) * (counts_b[lbl] / total) for lbl in labels)
    if p_e >= 1.0:
        kappa = 1.0 if p_o == 1.0 else 0.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)
    return round(p_o, 4), round(float(kappa), 4)


def compute_m5_2_annotator_agreement(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute binary presence and 4-state IAA (raw agreement + Cohen's kappa) on K/N verified rows."""
    verified = [
        r
        for r in rows
        if r.get("review_assignment") == "double_review_N_K"
        and r.get("K_human_verified") is True
        and r.get("N_human_verified") is True
    ]

    if not verified:
        return {
            "double_verified_unit_count": 0,
            "aspect_pair_count": 0,
            "raw_agreement_presence": 0.0,
            "cohens_kappa_presence": 0.0,
            "raw_agreement_4state": 0.0,
            "cohens_kappa_4state": 0.0,
            "per_aspect_agreement": {
                aspect: {
                    "unit_count": 0,
                    "raw_agreement_presence": 0.0,
                    "cohens_kappa_presence": 0.0,
                    "raw_agreement_4state": 0.0,
                    "cohens_kappa_4state": 0.0,
                }
                for aspect in ASPECT_NAMES
            },
        }

    all_k_4: list[str] = []
    all_n_4: list[str] = []
    all_k_pres: list[str] = []
    all_n_pres: list[str] = []
    per_aspect_k: dict[AspectName, list[str]] = {aspect: [] for aspect in ASPECT_NAMES}
    per_aspect_n: dict[AspectName, list[str]] = {aspect: [] for aspect in ASPECT_NAMES}

    for row in verified:
        k_map = _require_aspect_state_map(row.get("K_aspects"), "K_aspects")
        n_map = _require_aspect_state_map(row.get("N_aspects"), "N_aspects")
        for aspect in ASPECT_NAMES:
            ks = k_map[aspect]
            ns = n_map[aspect]
            all_k_4.append(ks)
            all_n_4.append(ns)
            all_k_pres.append("absent_unknown" if ks == "absent_unknown" else "observed")
            all_n_pres.append("absent_unknown" if ns == "absent_unknown" else "observed")
            per_aspect_k[aspect].append(ks)
            per_aspect_n[aspect].append(ns)

    raw_pres, kappa_pres = _agreement_and_kappa(all_k_pres, all_n_pres)
    raw_4, kappa_4 = _agreement_and_kappa(all_k_4, all_n_4)

    per_aspect_agreement: dict[str, dict[str, float | int]] = {}
    for aspect in ASPECT_NAMES:
        ka = per_aspect_k[aspect]
        na = per_aspect_n[aspect]
        kp = ["absent_unknown" if x == "absent_unknown" else "observed" for x in ka]
        np_ = ["absent_unknown" if x == "absent_unknown" else "observed" for x in na]
        a_raw_pres, a_kappa_pres = _agreement_and_kappa(kp, np_)
        a_raw_4, a_kappa_4 = _agreement_and_kappa(ka, na)
        per_aspect_agreement[aspect] = {
            "unit_count": len(ka),
            "raw_agreement_presence": a_raw_pres,
            "cohens_kappa_presence": a_kappa_pres,
            "raw_agreement_4state": a_raw_4,
            "cohens_kappa_4state": a_kappa_4,
        }

    return {
        "double_verified_unit_count": len(verified),
        "aspect_pair_count": len(all_k_4),
        "raw_agreement_presence": raw_pres,
        "cohens_kappa_presence": kappa_pres,
        "raw_agreement_4state": raw_4,
        "cohens_kappa_4state": kappa_4,
        "per_aspect_agreement": per_aspect_agreement,
    }


def _compute_core_absa_metrics(
    validated_pairs: list[tuple[dict[AspectName, str], dict[AspectName, str]]],
) -> dict[str, Any]:
    n_units = len(validated_pairs)
    per_aspect: dict[str, dict[str, Any]] = {}
    det_precs: list[float] = []
    det_recs: list[float] = []
    det_f1s: list[float] = []

    for aspect in ASPECT_NAMES:
        tp = sum(
            1
            for pred, truth in validated_pairs
            if truth[aspect] != "absent_unknown" and pred[aspect] != "absent_unknown"
        )
        fp = sum(
            1
            for pred, truth in validated_pairs
            if truth[aspect] == "absent_unknown" and pred[aspect] != "absent_unknown"
        )
        fn = sum(
            1
            for pred, truth in validated_pairs
            if truth[aspect] != "absent_unknown" and pred[aspect] == "absent_unknown"
        )
        tn = sum(
            1
            for pred, truth in validated_pairs
            if truth[aspect] == "absent_unknown" and pred[aspect] == "absent_unknown"
        )
        gold_support = tp + fn
        pred_support = tp + fp
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2.0 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        gold_states = {
            st: sum(1 for _, truth in validated_pairs if truth[aspect] == st)
            for st in VALID_ASPECT_STATES
        }
        pred_states = {
            st: sum(1 for pred, _ in validated_pairs if pred[aspect] == st)
            for st in VALID_ASPECT_STATES
        }

        per_aspect[aspect] = {
            "gold_support": gold_support,
            "pred_support": pred_support,
            "gold_coverage": round(gold_support / n_units, 4) if n_units > 0 else 0.0,
            "pred_coverage": round(pred_support / n_units, 4) if n_units > 0 else 0.0,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "tn": tn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "gold_state_counts": gold_states,
            "pred_state_counts": pred_states,
        }
        if gold_support > 0:
            det_precs.append(prec)
            det_recs.append(rec)
            det_f1s.append(f1)

    det_macro_p = float(np.mean(det_precs)) if det_precs else 0.0
    det_macro_r = float(np.mean(det_recs)) if det_recs else 0.0
    det_macro_f1 = float(np.mean(det_f1s)) if det_f1s else 0.0

    # Strictly gold-observed (row, aspect) pairs: truth_state != "absent_unknown".
    # If pred_state == "absent_unknown" on a gold-observed pair, yp != pol counts it as a missed recall (FN).
    observed_pairs: list[tuple[str, str]] = []
    for pred, truth in validated_pairs:
        for aspect in ASPECT_NAMES:
            yt = truth[aspect]
            if yt != "absent_unknown":
                observed_pairs.append((yt, pred[aspect]))

    per_polarity: dict[str, dict[str, Any]] = {}
    sent_precs: list[float] = []
    sent_recs: list[float] = []
    sent_f1s: list[float] = []

    for pol in OBSERVED_SENTIMENT_STATES:
        tp = sum(1 for yt, yp in observed_pairs if yt == pol and yp == pol)
        fp = sum(1 for yt, yp in observed_pairs if yt != pol and yp == pol)
        fn = sum(1 for yt, yp in observed_pairs if yt == pol and yp != pol)
        support = tp + fn
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2.0 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        per_polarity[pol] = {
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
        }
        if support > 0:
            sent_precs.append(prec)
            sent_recs.append(rec)
            sent_f1s.append(f1)

    sent_macro_p = float(np.mean(sent_precs)) if sent_precs else 0.0
    sent_macro_r = float(np.mean(sent_recs)) if sent_recs else 0.0
    sent_macro_f1 = float(np.mean(sent_f1s)) if sent_f1s else 0.0

    return {
        "per_aspect_detection": per_aspect,
        "aspect_detection_macro_precision": round(det_macro_p, 4),
        "aspect_detection_macro_recall": round(det_macro_r, 4),
        "aspect_detection_macro_f1": round(det_macro_f1, 4),
        "gold_observed_aspect_pair_count": len(observed_pairs),
        "per_polarity_observed_sentiment": per_polarity,
        "observed_sentiment_macro_precision": round(sent_macro_p, 4),
        "observed_sentiment_macro_recall": round(sent_macro_r, 4),
        "observed_sentiment_macro_f1": round(sent_macro_f1, 4),
    }


def evaluate_m5_2_aspect_sentiment(
    rows: list[dict[str, Any]],
    *,
    spans: Sequence[AspectSpanEvidence | dict[str, Any]],
    units_by_id: dict[str, str] | None = None,
    pred_col: str = "pred_aspects",
    truth_col: str = "adjudicated_aspects",
    is_real_pilot_data: bool = False,
    human_signoff_complete: bool = False,
    total_annotated_units: int | None = None,
    total_unique_videos: int | None = None,
    n_boot: int = 300,
    seed: int = 42,
) -> dict[str, Any]:
    """Evaluate 4-aspect binary detection, 3-class gold-observed sentiment, span validity, and pilot gate."""
    if not rows:
        raise ValueError("rows must be non-empty for evaluate_m5_2_aspect_sentiment")

    validated_pairs: list[tuple[dict[AspectName, str], dict[AspectName, str]]] = []
    pairs_by_video: dict[str, list[tuple[dict[AspectName, str], dict[AspectName, str]]]] = {}
    inferred_units_map: dict[str, str] = {}

    for row in rows:
        raw_vid = row.get("video_id")
        if raw_vid is None or not str(raw_vid).strip():
            raise ValueError("Each evaluated row must contain a non-blank video_id")
        vid = str(raw_vid).strip()

        pred_map = _require_aspect_state_map(row.get(pred_col), pred_col)
        truth_map = _require_aspect_state_map(row.get(truth_col), truth_col)
        pair = (pred_map, truth_map)
        validated_pairs.append(pair)
        pairs_by_video.setdefault(vid, []).append(pair)

        raw_uid = row.get("unit_id")
        if isinstance(raw_uid, str) and raw_uid.strip():
            inferred_units_map[raw_uid] = str(row.get("text") or "")

    units_map = dict(units_by_id) if units_by_id is not None else inferred_units_map
    span_audit = audit_source_span_validity(units_map, spans)
    core = _compute_core_absa_metrics(validated_pairs)

    unique_vids = sorted(pairs_by_video.keys())
    det_f1_point = float(core["aspect_detection_macro_f1"])
    sent_f1_point = float(core["observed_sentiment_macro_f1"])

    if n_boot > 0 and len(unique_vids) >= 2:
        rng = np.random.default_rng(seed)
        boot_det_f1: list[float] = []
        boot_sent_f1: list[float] = []
        for _ in range(n_boot):
            sampled_indices = rng.integers(0, len(unique_vids), size=len(unique_vids))
            boot_pairs = [
                pair
                for idx in sampled_indices
                for pair in pairs_by_video[unique_vids[int(idx)]]
            ]
            b_core = _compute_core_absa_metrics(boot_pairs)
            boot_det_f1.append(float(b_core["aspect_detection_macro_f1"]))
            boot_sent_f1.append(float(b_core["observed_sentiment_macro_f1"]))
        det_ci_arr = np.percentile(boot_det_f1, [2.5, 97.5])
        sent_ci_arr = np.percentile(boot_sent_f1, [2.5, 97.5])
        det_ci95 = [round(float(det_ci_arr[0]), 4), round(float(det_ci_arr[1]), 4)]
        sent_ci95 = [round(float(sent_ci_arr[0]), 4), round(float(sent_ci_arr[1]), 4)]
    else:
        det_ci95 = [det_f1_point, det_f1_point]
        sent_ci95 = [sent_f1_point, sent_f1_point]

    eff_units = total_annotated_units if total_annotated_units is not None else len(rows)
    eff_videos = total_unique_videos if total_unique_videos is not None else len(unique_vids)

    gate_eligible = bool(
        is_real_pilot_data
        and human_signoff_complete
        and (120 <= eff_units <= 200)
        and (eff_videos >= 10)
        and (len(rows) >= 40)
        and (det_f1_point >= 0.65)
        and (sent_f1_point >= 0.60)
        and bool(span_audit["meets_95pct_gate"])
    )

    return {
        "evaluated_unit_count": len(rows),
        "evaluated_video_count": len(unique_vids),
        "effective_total_annotated_units": eff_units,
        "effective_total_unique_videos": eff_videos,
        "is_real_pilot_data": bool(is_real_pilot_data),
        "human_signoff_complete": bool(human_signoff_complete),
        **core,
        "aspect_detection_macro_f1_ci95": det_ci95,
        "observed_sentiment_macro_f1_ci95": sent_ci95,
        "span_audit": span_audit,
        "m5_2_pilot_gate_eligible": gate_eligible,
    }


def _non_blank_nfc(val: object) -> str | None:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return None
    s = unicodedata.normalize("NFC", str(val))
    return s if s.strip() else None


def build_m5_2_annotation_pool(
    videos_df: pd.DataFrame,
    voice_df: pd.DataFrame | None,
    comments_df: pd.DataFrame | None,
    *,
    max_units: int = 180,
    double_overlap: int = 50,
    seed: int = 42,
    include_predictions: bool = False,
) -> list[dict[str, Any]]:
    """Build a collision-free, video-balanced, blinded 120-200 unit pool across utterances, comments, and captions."""
    if not (1 <= max_units <= 200):
        raise ValueError(f"max_units must satisfy 1 <= max_units <= 200, got {max_units!r}")
    if double_overlap < 0:
        raise ValueError(f"double_overlap must be >= 0, got {double_overlap!r}")

    seen_unit_ids: set[str] = set()
    utts_by_vid: dict[str, list[tuple[str, TextUnitSourceKind, str]]] = {}
    cmts_by_vid: dict[str, list[tuple[str, TextUnitSourceKind, str]]] = {}
    caps_by_vid: dict[str, list[tuple[str, TextUnitSourceKind, str]]] = {}
    all_vids_set: set[str] = set()

    if not videos_df.empty and "video_id" in videos_df.columns:
        for row in videos_df.to_dict("records"):
            vid_raw = _non_blank_nfc(row.get("video_id"))
            if vid_raw is None:
                continue
            vid = vid_raw.strip()
            all_vids_set.add(vid)
            cap_txt = _non_blank_nfc(row.get("caption"))
            if cap_txt is None:
                cap_txt = _non_blank_nfc(row.get("description"))
            if cap_txt is not None:
                uid = f"{vid}::cap"
                if uid not in seen_unit_ids:
                    seen_unit_ids.add(uid)
                    caps_by_vid.setdefault(vid, []).append((uid, "creator_caption", cap_txt))

    if voice_df is not None and not voice_df.empty and "video_id" in voice_df.columns:
        for idx, row in enumerate(voice_df.to_dict("records")):
            vid_raw = _non_blank_nfc(row.get("video_id"))
            if vid_raw is None:
                continue
            vid = vid_raw.strip()
            all_vids_set.add(vid)
            seg_raw = _non_blank_nfc(row.get("segment_id"))
            seg_id = seg_raw.strip() if seg_raw is not None else f"{idx:03d}"
            txt = _non_blank_nfc(row.get("text"))
            if txt is None:
                continue
            uid = f"{vid}::utt::{seg_id}"
            if uid not in seen_unit_ids:
                seen_unit_ids.add(uid)
                utts_by_vid.setdefault(vid, []).append((uid, "creator_utterance", txt))

    if comments_df is not None and not comments_df.empty and "video_id" in comments_df.columns:
        for idx, row in enumerate(comments_df.to_dict("records")):
            vid_raw = _non_blank_nfc(row.get("video_id"))
            if vid_raw is None:
                continue
            vid = vid_raw.strip()
            all_vids_set.add(vid)
            cmt_raw = _non_blank_nfc(row.get("comment_id"))
            cmt_id = cmt_raw.strip() if cmt_raw is not None else f"{idx:03d}"
            # Prefer unstripped original_text when non-blank so NFC char offsets match stored comment bytes
            txt = _non_blank_nfc(row.get("original_text"))
            if txt is None:
                txt = _non_blank_nfc(row.get("text"))
            if txt is None:
                continue
            uid = f"{vid}::cmt::{cmt_id}"
            if uid not in seen_unit_ids:
                seen_unit_ids.add(uid)
                cmts_by_vid.setdefault(vid, []).append((uid, "viewer_comment", txt))

    unique_vids = sorted(all_vids_set)
    rng = np.random.default_rng(seed)
    shuffled_vids = list(unique_vids)
    rng.shuffle(shuffled_vids)

    # Interleave modalities per video (creator_utterance -> viewer_comment -> creator_caption) so round-robin
    # covers both speech and comments across every video before filling additional units.
    queues_by_vid: dict[str, list[tuple[str, TextUnitSourceKind, str]]] = {}
    for vid in shuffled_vids:
        u_list = sorted(utts_by_vid.get(vid, []), key=lambda x: x[0])
        c_list = sorted(cmts_by_vid.get(vid, []), key=lambda x: x[0])
        p_list = sorted(caps_by_vid.get(vid, []), key=lambda x: x[0])
        interleaved: list[tuple[str, TextUnitSourceKind, str]] = []
        max_len = max(len(u_list), len(c_list), len(p_list), 0)
        for pos in range(max_len):
            if pos < len(u_list):
                interleaved.append(u_list[pos])
            if pos < len(c_list):
                interleaved.append(c_list[pos])
            if pos < len(p_list):
                interleaved.append(p_list[pos])
        if interleaved:
            queues_by_vid[vid] = interleaved

    selected_rr: list[tuple[str, str, TextUnitSourceKind, str]] = []
    round_idx = 0
    while len(selected_rr) < max_units:
        added_in_round = False
        for vid in shuffled_vids:
            q = queues_by_vid.get(vid)
            if q is not None and round_idx < len(q):
                uid, skind, txt = q[round_idx]
                selected_rr.append((vid, uid, skind, txt))
                added_in_round = True
                if len(selected_rr) >= max_units:
                    break
        if not added_in_round:
            break
        round_idx += 1

    overlap = min(double_overlap, len(selected_rr))
    remaining = len(selected_rr) - overlap
    n_only_cutoff = overlap + (remaining // 2)

    assignment_by_uid: dict[str, str] = {}
    for idx, (_, uid, _, _) in enumerate(selected_rr):
        if idx < overlap:
            assignment_by_uid[uid] = "double_review_N_K"
        elif idx < n_only_cutoff:
            assignment_by_uid[uid] = "N_only"
        else:
            assignment_by_uid[uid] = "K_only"

    # Order contiguously by video_id (preserving shuffled video order, then caption -> utterance -> comment)
    vid_rank = {vid: pos for pos, vid in enumerate(shuffled_vids)}
    kind_rank: dict[TextUnitSourceKind, int] = {
        "creator_caption": 0,
        "creator_transcript": 1,
        "creator_utterance": 2,
        "viewer_comment": 3,
    }
    ordered = sorted(
        selected_rr,
        key=lambda item: (vid_rank[item[0]], kind_rank[item[2]], item[1]),
    )

    pool_out: list[dict[str, Any]] = []
    for i, (vid, uid, skind, txt) in enumerate(ordered):
        entry: dict[str, Any] = {
            "item_id": f"m5_2_{i + 1:03d}",
            "unit_id": uid,
            "video_id": vid,
            "source_kind": skind,
            "text": txt,
            "review_assignment": assignment_by_uid[uid],
            "K_aspects": None,
            "K_spans": [],
            "K_note": "",
            "K_human_verified": False,
            "N_aspects": None,
            "N_spans": [],
            "N_note": "",
            "N_human_verified": False,
            "adjudicated_aspects": None,
            "adjudicated_spans": [],
        }
        if include_predictions:
            pred_aspects, pred_spans = predict_unit_aspects(
                TextUnitInput(unit_id=uid, source_kind=skind, text=txt)
            )
            entry["pred_aspects"] = pred_aspects
            entry["pred_spans"] = [sp.model_dump() for sp in pred_spans]
        pool_out.append(entry)

    return pool_out


__all__ = [
    "OBSERVED_SENTIMENT_STATES",
    "VALID_ASPECT_STATES",
    "audit_source_span_validity",
    "build_m5_2_annotation_pool",
    "compute_m5_2_annotator_agreement",
    "evaluate_m5_2_aspect_sentiment",
    "predict_unit_aspects",
    "split_units_by_video",
]
