"""M5.1 video-disjoint splitting, agreement, P/R/F1 uncertainty, and filter sensitivity."""
from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

from packages.absa.analyzer import analyze_koc_vs_viewer_absa, score_text_aspects
from packages.data_contracts.multimodal import (
    ASPECT_NAMES,
    CommentRecord,
    RawCommentInput,
    RawWhisperSegment,
)
from packages.seeding.detector import detect_seeding_comments

OBSERVABLE_COMMENT_CLASSES: tuple[str, ...] = (
    "observable_duplicate",
    "contact_or_link",
    "noise_or_empty",
    "template_phrase_match",
    "no_indicator_observed",
    "unknown_ambiguous",
)
_VALID_CLASS_SET: frozenset[str] = frozenset(OBSERVABLE_COMMENT_CLASSES)

POSITIVE_INDICATOR_CLASSES: tuple[str, ...] = (
    "observable_duplicate",
    "contact_or_link",
    "noise_or_empty",
    "template_phrase_match",
)

CORE_POSITIVE_INDICATOR_CLASSES: tuple[str, ...] = (
    "observable_duplicate",
    "contact_or_link",
    "noise_or_empty",
)

SEEDING_REASON_TO_OBSERVABLE_LABEL: dict[str, str] = {
    "contact_or_link_spam": "contact_or_link",
    "emoji_or_empty_noise": "noise_or_empty",
    "duplicate_seeding_cluster": "observable_duplicate",
    "canned_praise_template": "template_phrase_match",
}


def _require_valid_label(val: object, field_name: str) -> str:
    if val is None or not isinstance(val, str):
        raise ValueError(f"{field_name} must be a non-null string in OBSERVABLE_COMMENT_CLASSES, got {val!r}")
    cleaned: str = val.strip()
    if cleaned not in _VALID_CLASS_SET:
        raise ValueError(f"Invalid {field_name} {cleaned!r}; allowed: {OBSERVABLE_COMMENT_CLASSES}")
    return cleaned


def split_comments_by_video(
    rows: list[dict[str, Any]],
    *,
    video_id_col: str = "video_id",
    seed: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    """Partition comments strictly by video/thread ID into 3 disjoint thirds."""
    vids_set: set[str] = set()
    for r in rows:
        raw_vid = r.get(video_id_col)
        if raw_vid is None or not str(raw_vid).strip():
            raise ValueError(f"Missing or blank {video_id_col} in comment row")
        vids_set.add(str(raw_vid).strip())

    vids = sorted(vids_set)
    if len(vids) < 3:
        raise ValueError(f"Need at least 3 distinct {video_id_col} values for 3-way disjoint split")

    rng = np.random.default_rng(seed)
    shuffled = list(vids)
    rng.shuffle(shuffled)

    buckets: dict[str, set[str]] = {
        "dev": set(),
        "calibration": set(),
        "held_out_third": set(),
    }
    names = ("dev", "calibration", "held_out_third")
    for idx, vid in enumerate(shuffled):
        buckets[names[idx % 3]].add(vid)

    out: dict[str, list[dict[str, Any]]] = {name: [] for name in names}
    for row in rows:
        vid = str(row[video_id_col]).strip()
        for name in names:
            if vid in buckets[name]:
                out[name].append(row)
                break
    return out


def compute_inter_annotator_agreement(
    labels_n: list[str],
    labels_k: list[str],
) -> dict[str, Any]:
    """Compute raw agreement, multi-class Cohen's kappa, and retained unknown count."""
    if len(labels_n) != len(labels_k) or not labels_n:
        raise ValueError("Paired annotation lists must be equal-length and non-empty")

    clean_n = [_require_valid_label(x, "labels_n") for x in labels_n]
    clean_k = [_require_valid_label(x, "labels_k") for x in labels_k]

    total = len(clean_n)
    agree = sum(1 for a, b in zip(clean_n, clean_k) if a == b)
    raw_agreement = agree / total

    all_labels = sorted(set(clean_n) | set(clean_k))
    counts_a = Counter(clean_n)
    counts_b = Counter(clean_k)
    p_expected = sum((counts_a[lbl] / total) * (counts_b[lbl] / total) for lbl in all_labels)
    kappa = (raw_agreement - p_expected) / (1.0 - p_expected) if p_expected < 1.0 else 1.0

    unknown_count = sum(
        1 for a, b in zip(clean_n, clean_k) if a == "unknown_ambiguous" or b == "unknown_ambiguous"
    )
    pos_set = frozenset(POSITIVE_INDICATOR_CLASSES)
    bin_n = [a in pos_set for a in clean_n]
    bin_k = [b in pos_set for b in clean_k]
    pos_raw_agr = sum(1 for a, b in zip(bin_n, bin_k) if a == b) / total
    p_pos_n = sum(1 for a in bin_n if a) / total
    p_pos_k = sum(1 for b in bin_k if b) / total
    p_pos_exp = p_pos_n * p_pos_k + (1.0 - p_pos_n) * (1.0 - p_pos_k)
    pos_kappa = (pos_raw_agr - p_pos_exp) / (1.0 - p_pos_exp) if p_pos_exp < 1.0 else 1.0

    pair_counts = Counter(f"{a} -> {b}" for a, b in zip(clean_n, clean_k))
    return {
        "total_double_annotated": total,
        "raw_agreement": round(raw_agreement, 4),
        "cohens_kappa": round(float(kappa), 4),
        "positive_indicator_raw_agreement": round(pos_raw_agr, 4),
        "positive_indicator_cohens_kappa": round(float(pos_kappa), 4),
        "unknown_ambiguous_count": unknown_count,
        "class_pair_counts": dict(sorted(pair_counts.items())),
    }


def _compute_class_prf(
    y_true: list[str], y_pred: list[str]
) -> tuple[dict[str, dict[str, float | int]], float, float, float]:
    per_class: dict[str, dict[str, float | int]] = {}
    active_p: list[float] = []
    active_r: list[float] = []
    active_f1: list[float] = []

    for cls in POSITIVE_INDICATOR_CLASSES:
        tp = sum(1 for yt, yp in zip(y_true, y_pred) if yt == cls and yp == cls)
        fp = sum(1 for yt, yp in zip(y_true, y_pred) if yt != cls and yp == cls)
        fn = sum(1 for yt, yp in zip(y_true, y_pred) if yt == cls and yp != cls)
        support = sum(1 for yt in y_true if yt == cls)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        per_class[cls] = {
            "support": support,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
        }
        if support > 0 or (tp + fp) > 0:
            active_p.append(prec)
        if support > 0:
            active_r.append(rec)
        if support > 0 or (tp + fp) > 0:
            active_f1.append(f1)

    macro_p = float(sum(active_p) / len(active_p)) if active_p else 0.0
    macro_r = float(sum(active_r) / len(active_r)) if active_r else 0.0
    macro_f1 = float(sum(active_f1) / len(active_f1)) if active_f1 else 0.0
    return per_class, macro_p, macro_r, macro_f1


def evaluate_comment_indicator_metrics(
    rows: list[dict[str, Any]],
    *,
    pred_col: str = "pred_label",
    truth_col: str = "adjudicated_label",
    human_signoff_complete: bool = False,
    total_annotated_pool_count: int | None = None,
    n_boot: int = 500,
    seed: int = 42,
) -> dict[str, Any]:
    """Compute per-class P/R/F1, confusion matrix, video-cluster bootstrap CIs, and M5.1 filter gate."""
    if not rows:
        raise ValueError("rows must be non-empty for evaluation")

    y_true = [_require_valid_label(r.get(truth_col), truth_col) for r in rows]
    y_pred = [_require_valid_label(r.get(pred_col), pred_col) for r in rows]

    per_class, macro_p, macro_r, macro_f1 = _compute_class_prf(y_true, y_pred)

    rng = np.random.default_rng(seed)
    n = len(rows)
    vids = [str(r.get("video_id") or "").strip() for r in rows]
    unique_vids = sorted({v for v in vids if v})
    cluster_indices: dict[str, list[int]] = {}
    if len(unique_vids) >= 2 and all(vids):
        for idx_i, v in enumerate(vids):
            cluster_indices.setdefault(v, []).append(idx_i)

    boot_p: list[float] = []
    boot_r: list[float] = []
    boot_f1: list[float] = []
    for _ in range(n_boot):
        if cluster_indices:
            drawn_v = rng.integers(0, len(unique_vids), size=len(unique_vids))
            sample_idx = [i for vc in drawn_v for i in cluster_indices[unique_vids[int(vc)]]]
        else:
            sample_idx = [int(i) for i in rng.integers(0, n, size=n)]
        yt_b = [y_true[i] for i in sample_idx]
        yp_b = [y_pred[i] for i in sample_idx]
        _, mp, mr, mf = _compute_class_prf(yt_b, yp_b)
        boot_p.append(mp)
        boot_r.append(mr)
        boot_f1.append(mf)

    def _ci(vals: list[float], point: float) -> dict[str, float]:
        lo, hi = np.percentile(vals, [2.5, 97.5])
        return {"point": round(point, 4), "ci95_low": round(float(lo), 4), "ci95_high": round(float(hi), 4)}

    confusion: dict[str, dict[str, int]] = {}
    for yt, yp in zip(y_true, y_pred):
        row_map = confusion.setdefault(yt, {})
        row_map[yp] = row_map.get(yp, 0) + 1

    truth_counts = dict(sorted(Counter(y_true).items()))
    pred_counts = dict(sorted(Counter(y_pred).items()))

    eff_pool_count = int(total_annotated_pool_count) if total_annotated_pool_count is not None else len(rows)
    core_missing_support = sorted(
        c for c in CORE_POSITIVE_INDICATOR_CLASSES if int(per_class[c]["support"]) == 0
    )
    # M5.1 gate: >= 150 total human-verified pilot comments (>= 45 in held_out_third),
    # positive support across all 3 core indicator classes (duplicate, contact/link, noise),
    # P >= 0.85, and R >= 0.60.
    auto_filter_eligible = (
        eff_pool_count >= 150
        and len(rows) >= 45
        and human_signoff_complete
        and len(core_missing_support) == 0
        and macro_p >= 0.85
        and macro_r >= 0.60
    )

    return {
        "evaluated_comment_count": len(rows),
        "total_annotated_pool_count": eff_pool_count,
        "unique_video_count": len(unique_vids),
        "human_signoff_complete": human_signoff_complete,
        "bootstrap_mode": "video_cluster_resample" if cluster_indices else "row_iid_resample",
        "truth_class_counts": truth_counts,
        "pred_class_counts": pred_counts,
        "per_class_metrics": per_class,
        "core_positive_classes_missing_support": core_missing_support,
        "macro_precision": round(macro_p, 4),
        "macro_recall": round(macro_r, 4),
        "macro_f1": round(macro_f1, 4),
        "bootstrap_95_ci": {
            "macro_precision": _ci(boot_p, macro_p),
            "macro_recall": _ci(boot_r, macro_r),
            "macro_f1": _ci(boot_f1, macro_f1),
        },
        "confusion_matrix": confusion,
        "auto_filter_thresholds": {
            "min_annotated_comments": 150,
            "min_held_out_comments": 45,
            "min_core_positive_classes_with_support": len(CORE_POSITIVE_INDICATOR_CLASSES),
            "min_macro_precision": 0.85,
            "min_macro_recall": 0.60,
        },
        "auto_filter_eligible": auto_filter_eligible,
        "recommended_mode": (
            "auto_filter_validated"
            if auto_filter_eligible
            else "diagnostic_only_without_filtering"
        ),
    }


def build_annotation_pool(
    comments_df: pd.DataFrame,
    *,
    max_items: int = 300,
    double_overlap: int = 60,
    seed: int = 42,
    include_predictions: bool = False,
) -> list[dict[str, Any]]:
    """Sample <= 300 comments grouped contiguously by video_id with blinded N/K human assignments."""
    if max_items < 1 or max_items > 300:
        raise ValueError("M5.1 caps real pilot comment sample at <= 300 items")
    if comments_df.empty:
        return []

    work = comments_df.copy()
    work["video_id"] = work["video_id"].astype(str)
    work["comment_id"] = work["comment_id"].astype(str)

    rng = np.random.default_rng(seed)
    unique_vids = sorted(work["video_id"].unique().tolist())
    rng.shuffle(unique_vids)

    # Select whole video threads in shuffled video order so within-thread duplicates stay observable
    selected_chunks: list[pd.DataFrame] = []
    collected = 0
    for vid in unique_vids:
        if collected >= max_items:
            break
        v_df = work[work["video_id"] == vid].sort_values("comment_id")
        need = max_items - collected
        selected_chunks.append(v_df.iloc[:need])
        collected += min(len(v_df), need)

    sampled = pd.concat(selected_chunks, ignore_index=True)
    overlap = min(double_overlap, len(sampled))
    remaining = len(sampled) - overlap
    n_only_cutoff = overlap + (remaining // 2)

    items: list[dict[str, Any]] = []
    for i, row in enumerate(sampled.to_dict("records")):
        if i < overlap:
            assign = "double_review_N_K"
        elif i < n_only_cutoff:
            assign = "N_only"
        else:
            assign = "K_only"

        entry: dict[str, Any] = {
            "item_id": f"m5_1_{i + 1:03d}",
            "comment_id": str(row["comment_id"]),
            "video_id": str(row["video_id"]),
            "author_handle": str(row.get("author_handle") or ""),
            "original_text": str(row.get("original_text") or row.get("text") or ""),
            "review_assignment": assign,
            "N_label": None,
            "N_note": "",
            "N_human_verified": False,
            "K_label": None,
            "K_note": "",
            "K_human_verified": False,
            "adjudicated_label": None,
        }
        if include_predictions:
            obs = row.get("observable_label")
            if not obs:
                sr = row.get("seeding_reason")
                obs = SEEDING_REASON_TO_OBSERVABLE_LABEL.get(str(sr), "no_indicator_observed") if sr else "no_indicator_observed"
            entry["predicted_observable_label"] = str(obs)
            entry["predicted_reason_codes"] = list(row.get("observable_reason_codes") or [])
        items.append(entry)
    return items


def reconstruct_observable_predictions(
    comments_df: pd.DataFrame,
    pool_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compute or reconstruct detector predictions per full video thread without leaking into human sheets."""
    work = comments_df.copy()
    work["video_id"] = work["video_id"].astype(str)
    work["comment_id"] = work["comment_id"].astype(str)

    pool_vids = {str(item["video_id"]) for item in pool_items}
    pred_lookup: dict[tuple[str, str], CommentRecord] = {}
    for vid in sorted(pool_vids):
        v_df = work[work["video_id"] == vid].sort_values("comment_id")
        raw_inputs = [
            RawCommentInput(
                comment_id=str(r["comment_id"]),
                author_handle=str(r.get("author_handle") or ""),
                text=str(r.get("original_text") or r.get("text") or ""),
                like_count=int(r.get("like_count") or 0),
                reply_count=int(r.get("reply_count") or 0),
            )
            for r in v_df.to_dict("records")
        ]
        for rec in detect_seeding_comments(vid, raw_inputs):
            pred_lookup[(vid, rec.comment_id)] = rec

    enriched: list[dict[str, Any]] = []
    for item in pool_items:
        key = (str(item["video_id"]), str(item["comment_id"]))
        rec_opt = pred_lookup.get(key)
        enriched.append(
            {
                "item_id": item["item_id"],
                "video_id": str(item["video_id"]),
                "comment_id": str(item["comment_id"]),
                "predicted_observable_label": (
                    rec_opt.observable_label if rec_opt is not None else "no_indicator_observed"
                ),
                "predicted_reason_codes": (
                    list(rec_opt.observable_reason_codes) if rec_opt is not None else []
                ),
            }
        )
    return enriched


def compute_comment_filter_sensitivity(
    *,
    caption: str,
    transcript: str,
    comments: list[CommentRecord],
    utterances: list[RawWhisperSegment] | None = None,
    video_id: str = "sensitivity_audit",
) -> dict[str, Any]:
    """Compare ABSA viewer aspect averages and M5.2 supported discrepancy before vs after filtering."""
    koc_scores, _ = score_text_aspects([f"{caption}. {transcript}"])
    koc_mean = (koc_scores.taste + koc_scores.price + koc_scores.hygiene + koc_scores.service) / 4.0

    all_texts = [c.text for c in comments]
    unflagged_texts = [c.text for c in comments if not c.is_seeding]

    if all_texts:
        before_scores, _ = score_text_aspects(all_texts)
        before_mean: float | None = (
            before_scores.taste
            + before_scores.price
            + before_scores.hygiene
            + before_scores.service
        ) / 4.0
        before_scores_dict: dict[str, float] | None = before_scores.model_dump()
    else:
        before_mean = None
        before_scores_dict = None

    if unflagged_texts:
        after_scores, _ = score_text_aspects(unflagged_texts)
        after_mean: float | None = (
            after_scores.taste + after_scores.price + after_scores.hygiene + after_scores.service
        ) / 4.0
        after_scores_dict: dict[str, float] | None = after_scores.model_dump()
        after_abstained = False
    else:
        after_mean = None
        after_scores_dict = None
        after_abstained = True

    mean_shift = (
        round(float(after_mean - before_mean), 4)
        if (before_mean is not None and after_mean is not None)
        else None
    )
    before_gap = round(float(koc_mean - before_mean), 4) if before_mean is not None else 0.0
    after_gap = round(float(koc_mean - after_mean), 4) if after_mean is not None else 0.0

    unflagged_all_comments = [c.model_copy(update={"is_seeding": False}) for c in comments]
    before_comp = analyze_koc_vs_viewer_absa(
        video_id=video_id,
        caption=caption,
        transcript=transcript,
        comments=unflagged_all_comments,
        utterances=utterances,
    )
    after_comp = analyze_koc_vs_viewer_absa(
        video_id=video_id,
        caption=caption,
        transcript=transcript,
        comments=comments,
        utterances=utterances,
    )

    before_sup_disc = before_comp.supported_sentiment_discrepancy
    after_sup_disc = after_comp.supported_sentiment_discrepancy
    supported_discrepancy_shift = (
        round(float(after_sup_disc - before_sup_disc), 4)
        if (before_sup_disc is not None and after_sup_disc is not None)
        else None
    )

    per_aspect_filter_shift: dict[str, dict[str, Any]] = {}
    for aspect in ASPECT_NAMES:
        b_detail = before_comp.aspect_discrepancies[aspect]
        a_detail = after_comp.aspect_discrepancies[aspect]
        per_aspect_filter_shift[aspect] = {
            "before_viewer_support": b_detail.viewer_support_count,
            "after_viewer_support": a_detail.viewer_support_count,
            "before_viewer_mean": b_detail.viewer_mean_score,
            "after_viewer_mean": a_detail.viewer_mean_score,
            "before_comparison_status": b_detail.comparison_status,
            "after_comparison_status": a_detail.comparison_status,
            "before_sentiment_discrepancy": b_detail.sentiment_discrepancy,
            "after_sentiment_discrepancy": a_detail.sentiment_discrepancy,
        }

    threshold_sensitivity: list[dict[str, Any]] = []
    for tau in (0.05, 0.15, 0.25):
        for min_c in (1, 3, 5):
            grid_comp = (
                after_comp
                if (tau == 0.15 and min_c == 3)
                else analyze_koc_vs_viewer_absa(
                    video_id=video_id,
                    caption=caption,
                    transcript=transcript,
                    comments=comments,
                    utterances=utterances,
                    min_viewer_comments=min_c,
                    polarity_tau=tau,
                )
            )
            threshold_sensitivity.append(
                {
                    "polarity_tau": tau,
                    "min_viewer_comments": min_c,
                    "supported_overlapping_aspects": list(grid_comp.supported_overlapping_aspects),
                    "supported_aspect_count": len(grid_comp.supported_overlapping_aspects),
                    "supported_sentiment_discrepancy": grid_comp.supported_sentiment_discrepancy,
                }
            )

    return {
        "total_comments": len(comments),
        "flagged_indicator_count": len(comments) - len(unflagged_texts),
        "unflagged_comment_count": len(unflagged_texts),
        "after_filter_abstained": after_abstained,
        "before_filter_scores": before_scores_dict,
        "after_filter_scores": after_scores_dict,
        "before_filter_viewer_mean": round(float(before_mean), 4) if before_mean is not None else None,
        "after_filter_viewer_mean": round(float(after_mean), 4) if after_mean is not None else None,
        "mean_score_shift": mean_shift,
        "before_filter_hype_gap": before_gap,
        "after_filter_hype_gap": after_gap,
        "before_filter_supported_aspects": list(before_comp.supported_overlapping_aspects),
        "after_filter_supported_aspects": list(after_comp.supported_overlapping_aspects),
        "before_filter_supported_discrepancy": before_sup_disc,
        "after_filter_supported_discrepancy": after_sup_disc,
        "supported_discrepancy_shift": supported_discrepancy_shift,
        "per_aspect_filter_shift": per_aspect_filter_shift,
        "threshold_sensitivity": threshold_sensitivity,
    }


def validate_and_summarize_annotated_pool(
    pool_rows: list[dict[str, Any]],
    locked_prediction_rows: list[dict[str, Any]],
    *,
    min_pool_rows: int = 150,
    max_pool_rows: int = 300,
    min_double_overlap: int = 60,
) -> dict[str, Any]:
    """Fail-closed human signoff, adjudication, and locked-prediction validator for M5.1 real pools."""
    if not (min_pool_rows <= len(pool_rows) <= max_pool_rows):
        raise ValueError(
            f"Pool row count must be in [{min_pool_rows}, {max_pool_rows}], got {len(pool_rows)}"
        )
    if len(locked_prediction_rows) != len(pool_rows):
        raise ValueError(
            f"Locked prediction count ({len(locked_prediction_rows)}) != pool count ({len(pool_rows)})"
        )

    pred_by_item: dict[str, dict[str, Any]] = {}
    for p in locked_prediction_rows:
        iid = str(p.get("item_id") or "").strip()
        if not iid or iid in pred_by_item:
            raise ValueError(f"Missing or duplicate item_id in locked predictions: {iid!r}")
        _require_valid_label(p.get("predicted_observable_label"), "predicted_observable_label")
        pred_by_item[iid] = p

    seen_items: set[str] = set()
    seen_cid_pairs: set[tuple[str, str]] = set()
    double_n: list[str] = []
    double_k: list[str] = []
    disagreements: list[dict[str, Any]] = []
    merged_rows: list[dict[str, Any]] = []
    n_counts: Counter[str] = Counter()
    k_counts: Counter[str] = Counter()
    adj_counts: Counter[str] = Counter()
    assign_counts: Counter[str] = Counter()

    for row in pool_rows:
        iid = str(row.get("item_id") or "").strip()
        vid = str(row.get("video_id") or "").strip()
        cid = str(row.get("comment_id") or "").strip()
        if not iid or not vid or not cid:
            raise ValueError(f"Missing item_id/video_id/comment_id in row: {row!r}")
        if iid in seen_items or (vid, cid) in seen_cid_pairs:
            raise ValueError(f"Duplicate item or (video_id, comment_id) in pool: {iid} / {(vid, cid)}")
        seen_items.add(iid)
        seen_cid_pairs.add((vid, cid))

        pred_entry = pred_by_item.get(iid)
        if pred_entry is None:
            raise ValueError(f"Missing locked prediction for item_id={iid}")
        if str(pred_entry.get("video_id") or "").strip() != vid or str(pred_entry.get("comment_id") or "").strip() != cid:
            raise ValueError(f"Locked prediction key mismatch on {iid}: pool={(vid, cid)} vs pred={pred_entry}")

        assign = str(row.get("review_assignment") or "").strip()
        assign_counts[assign] += 1
        adj_lbl = _require_valid_label(row.get("adjudicated_label"), f"{iid}.adjudicated_label")

        if assign == "double_review_N_K":
            if row.get("N_human_verified") is not True:
                raise ValueError(f"{iid}: double_review_N_K requires N_human_verified=True")
            if row.get("K_human_verified") is not True:
                raise ValueError(f"{iid}: double_review_N_K requires K_human_verified=True")
            n_lbl = _require_valid_label(row.get("N_label"), f"{iid}.N_label")
            k_lbl = _require_valid_label(row.get("K_label"), f"{iid}.K_label")
            if n_lbl == k_lbl and adj_lbl != n_lbl:
                raise ValueError(
                    f"{iid}: cannot override unanimous N==K label {n_lbl!r} with {adj_lbl!r}"
                )
            double_n.append(n_lbl)
            double_k.append(k_lbl)
            n_counts[n_lbl] += 1
            k_counts[k_lbl] += 1
            if n_lbl != k_lbl:
                disagreements.append(
                    {
                        "item_id": iid,
                        "video_id": vid,
                        "comment_id": cid,
                        "author_handle": str(row.get("author_handle") or ""),
                        "original_text": str(row.get("original_text") or ""),
                        "N_label": n_lbl,
                        "K_label": k_lbl,
                        "adjudicated_label": adj_lbl,
                        "adjudication_note": str(row.get("adjudication_note") or ""),
                    }
                )
        elif assign == "N_only":
            if row.get("N_human_verified") is not True:
                raise ValueError(f"{iid}: N_only requires N_human_verified=True")
            if row.get("K_human_verified") is not False or row.get("K_label") is not None:
                raise ValueError(f"{iid}: N_only must keep K_human_verified=False and K_label=None")
            n_lbl = _require_valid_label(row.get("N_label"), f"{iid}.N_label")
            if adj_lbl != n_lbl:
                raise ValueError(f"{iid}: N_only adjudicated_label {adj_lbl!r} != N_label {n_lbl!r}")
            n_counts[n_lbl] += 1
        elif assign == "K_only":
            if row.get("K_human_verified") is not True:
                raise ValueError(f"{iid}: K_only requires K_human_verified=True")
            if row.get("N_human_verified") is not False or row.get("N_label") is not None:
                raise ValueError(f"{iid}: K_only must keep N_human_verified=False and N_label=None")
            k_lbl = _require_valid_label(row.get("K_label"), f"{iid}.K_label")
            if adj_lbl != k_lbl:
                raise ValueError(f"{iid}: K_only adjudicated_label {adj_lbl!r} != K_label {k_lbl!r}")
            k_counts[k_lbl] += 1
        else:
            raise ValueError(f"{iid}: invalid review_assignment {assign!r}")

        adj_counts[adj_lbl] += 1
        pred_lbl = _require_valid_label(
            pred_entry.get("predicted_observable_label"), f"{iid}.predicted_observable_label"
        )
        merged_rows.append(
            {
                **row,
                "adjudicated_label": adj_lbl,
                "pred_label": pred_lbl,
                "pred_reason_codes": list(pred_entry.get("predicted_reason_codes") or []),
            }
        )

    if len(double_n) < min_double_overlap:
        raise ValueError(
            f"Expected >= {min_double_overlap} double_review_N_K items, got {len(double_n)}"
        )

    agreement = compute_inter_annotator_agreement(double_n, double_k)
    return {
        "total_pool_rows": len(merged_rows),
        "unique_video_count": len({str(r["video_id"]) for r in merged_rows}),
        "assignment_counts": dict(sorted(assign_counts.items())),
        "n_verified_label_counts": dict(sorted(n_counts.items())),
        "k_verified_label_counts": dict(sorted(k_counts.items())),
        "adjudicated_label_counts": dict(sorted(adj_counts.items())),
        "agreement": agreement,
        "disagreements": disagreements,
        "merged_rows": merged_rows,
    }


__all__ = [
    "CORE_POSITIVE_INDICATOR_CLASSES",
    "OBSERVABLE_COMMENT_CLASSES",
    "POSITIVE_INDICATOR_CLASSES",
    "SEEDING_REASON_TO_OBSERVABLE_LABEL",
    "build_annotation_pool",
    "compute_comment_filter_sensitivity",
    "compute_inter_annotator_agreement",
    "evaluate_comment_indicator_metrics",
    "reconstruct_observable_predictions",
    "split_comments_by_video",
    "validate_and_summarize_annotated_pool",
]
