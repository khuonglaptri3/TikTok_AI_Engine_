"""M5.1 video-disjoint splitting, agreement, P/R/F1 uncertainty, and filter sensitivity."""
from __future__ import annotations

from collections import Counter
from typing import Any

import numpy as np
import pandas as pd

from packages.absa.analyzer import score_text_aspects
from packages.data_contracts.multimodal import CommentRecord

OBSERVABLE_COMMENT_CLASSES: tuple[str, ...] = (
    "observable_duplicate",
    "contact_or_link",
    "noise_or_empty",
    "template_phrase_match",
    "no_indicator_observed",
    "unknown_ambiguous",
)

POSITIVE_INDICATOR_CLASSES: tuple[str, ...] = (
    "observable_duplicate",
    "contact_or_link",
    "noise_or_empty",
    "template_phrase_match",
)


def split_comments_by_video(
    rows: list[dict[str, Any]],
    *,
    video_id_col: str = "video_id",
    seed: int = 42,
) -> dict[str, list[dict[str, Any]]]:
    """Partition comments strictly by video/thread ID into 3 disjoint thirds."""
    vids = sorted({str(r[video_id_col]) for r in rows})
    if len(vids) < 3:
        raise ValueError(f"Need at least 3 distinct {video_id_col} values for 3-way disjoint split")

    rng = np.random.default_rng(seed)
    shuffled = list(vids)
    rng.shuffle(shuffled)

    # Round-robin modulo 3 guarantees each third stays balanced and video-disjoint.
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
        vid = str(row[video_id_col])
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

    total = len(labels_n)
    agree = sum(1 for a, b in zip(labels_n, labels_k) if a == b)
    raw_agreement = agree / total

    all_labels = sorted(set(labels_n) | set(labels_k))
    counts_a = Counter(labels_n)
    counts_b = Counter(labels_k)
    p_expected = sum((counts_a[lbl] / total) * (counts_b[lbl] / total) for lbl in all_labels)
    kappa = (raw_agreement - p_expected) / (1.0 - p_expected) if p_expected < 1.0 else 1.0

    unknown_count = sum(
        1 for a, b in zip(labels_n, labels_k) if a == "unknown_ambiguous" or b == "unknown_ambiguous"
    )
    pair_counts = Counter(f"{a} -> {b}" for a, b in zip(labels_n, labels_k))
    return {
        "total_double_annotated": total,
        "raw_agreement": round(raw_agreement, 4),
        "cohens_kappa": round(float(kappa), 4),
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
            active_r.append(rec)
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
    n_boot: int = 500,
    seed: int = 42,
) -> dict[str, Any]:
    """Compute per-class P/R/F1, confusion matrix, bootstrap uncertainty, and M5.1 filter gate."""
    if not rows:
        raise ValueError("rows must be non-empty for evaluation")

    y_true = [str(r[truth_col]) for r in rows]
    y_pred = [str(r[pred_col]) for r in rows]

    per_class, macro_p, macro_r, macro_f1 = _compute_class_prf(y_true, y_pred)

    rng = np.random.default_rng(seed)
    n = len(rows)
    boot_p: list[float] = []
    boot_r: list[float] = []
    boot_f1: list[float] = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        yt_b = [y_true[int(i)] for i in idx]
        yp_b = [y_pred[int(i)] for i in idx]
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

    # M5.1 gate: >= 150 human-verified comments, macro precision >= 0.85, macro recall >= 0.60
    auto_filter_eligible = (
        len(rows) >= 150
        and human_signoff_complete
        and macro_p >= 0.85
        and macro_r >= 0.60
    )

    return {
        "evaluated_comment_count": len(rows),
        "unique_video_count": len({str(r.get("video_id", "")) for r in rows}),
        "human_signoff_complete": human_signoff_complete,
        "truth_class_counts": truth_counts,
        "pred_class_counts": pred_counts,
        "per_class_metrics": per_class,
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
) -> list[dict[str, Any]]:
    """Sample <= 300 real comments with deterministic N/K overlap ready for human annotation."""
    if max_items < 1 or max_items > 300:
        raise ValueError("M5.1 caps real pilot comment sample at <= 300 items")
    if comments_df.empty:
        return []

    n_take = min(max_items, len(comments_df))
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(comments_df), size=n_take, replace=False)
    sampled = comments_df.iloc[idx].sort_values(["video_id", "comment_id"]).reset_index(drop=True)
    perm = rng.permutation(len(sampled))
    sampled = sampled.iloc[perm].reset_index(drop=True)

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
        items.append(
            {
                "item_id": f"m5_1_{i + 1:03d}",
                "comment_id": str(row["comment_id"]),
                "video_id": str(row["video_id"]),
                "author_handle": str(row.get("author_handle") or ""),
                "original_text": str(row.get("original_text") or row.get("text") or ""),
                "predicted_observable_label": str(
                    row.get("observable_label") or "no_indicator_observed"
                ),
                "predicted_reason_codes": list(row.get("observable_reason_codes") or []),
                "review_assignment": assign,
                "N_label": None,
                "N_note": "",
                "N_human_verified": False,
                "K_label": None,
                "K_note": "",
                "K_human_verified": False,
                "adjudicated_label": None,
            }
        )
    return items


def compute_comment_filter_sensitivity(
    *,
    caption: str,
    transcript: str,
    comments: list[CommentRecord],
) -> dict[str, Any]:
    """Compare ABSA viewer aspect averages before vs after excluding indicator-flagged comments."""
    koc_scores, _ = score_text_aspects([f"{caption}. {transcript}"])
    koc_mean = (koc_scores.taste + koc_scores.price + koc_scores.hygiene + koc_scores.service) / 4.0

    all_texts = [c.text for c in comments]
    unflagged_texts = [c.text for c in comments if not c.is_seeding]

    if all_texts:
        before_scores, _ = score_text_aspects(all_texts)
        before_mean = (
            before_scores.taste
            + before_scores.price
            + before_scores.hygiene
            + before_scores.service
        ) / 4.0
    else:
        before_mean = 0.0

    if unflagged_texts:
        after_scores, _ = score_text_aspects(unflagged_texts)
        after_mean = (
            after_scores.taste + after_scores.price + after_scores.hygiene + after_scores.service
        ) / 4.0
    else:
        after_mean = 0.0

    return {
        "total_comments": len(comments),
        "flagged_indicator_count": len(comments) - len(unflagged_texts),
        "unflagged_comment_count": len(unflagged_texts),
        "before_filter_viewer_mean": round(float(before_mean), 4),
        "after_filter_viewer_mean": round(float(after_mean), 4),
        "mean_score_shift": round(float(after_mean - before_mean), 4),
        "before_filter_hype_gap": round(float(koc_mean - before_mean), 4),
        "after_filter_hype_gap": round(float(koc_mean - after_mean), 4),
    }


__all__ = [
    "OBSERVABLE_COMMENT_CLASSES",
    "POSITIVE_INDICATOR_CLASSES",
    "build_annotation_pool",
    "compute_comment_filter_sensitivity",
    "compute_inter_annotator_agreement",
    "evaluate_comment_indicator_metrics",
    "split_comments_by_video",
]
