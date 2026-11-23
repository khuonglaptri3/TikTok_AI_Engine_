"""Author-grouped genuine-target evaluation and PU audit helpers for M4.2."""
from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from typing import Any

import numpy as np
import pandas as pd
from scipy import optimize, sparse

from packages.absa.disclosure import (
    FORBIDDEN_DISCLOSURE_HASHTAGS,
    PLATFORM_CAMPAIGN_META_TAGS,
    assert_no_feature_leakage,
    classify_observed_disclosure_flags,
    extract_promotional_indicators,
)

_TOKEN_RE = re.compile(r"[0-9a-zA-ZÀ-ỹ]+")
_INLINE_HASHTAG_RE = re.compile(r"#([0-9a-zA-ZÀ-ỹ_]+)")


def strip_forbidden_inline_hashtags(
    text: str,
    *,
    extra_forbidden: frozenset[str] = frozenset(),
) -> str:
    """Remove inline disclosure hashtags (e.g. #ad, #quảngcáo) before tokenization or LLM prompting."""
    blocked = FORBIDDEN_DISCLOSURE_HASHTAGS | extra_forbidden

    def _repl(m: re.Match[str]) -> str:
        tag = unicodedata.normalize("NFC", m.group(1)).strip().lower()
        return " " if tag in blocked else m.group(0)

    return _INLINE_HASHTAG_RE.sub(_repl, text or "")


def _tokenize_for_study(
    text: str,
    hashtags: Any,
    *,
    exclude_platform_campaign_tags: bool = False,
) -> list[str]:
    extra_blocked = PLATFORM_CAMPAIGN_META_TAGS if exclude_platform_campaign_tags else frozenset()
    blocked = FORBIDDEN_DISCLOSURE_HASHTAGS | extra_blocked

    clean_tags: list[str] = []
    if hashtags is not None and not isinstance(hashtags, float):
        iterable = hashtags.tolist() if hasattr(hashtags, "tolist") else list(hashtags)
        for tag in iterable:
            norm_tag = unicodedata.normalize("NFC", str(tag)).strip().lstrip("#").lower()
            if norm_tag and norm_tag not in blocked:
                clean_tags.append(f"tag_{norm_tag}")

    scrubbed_text = strip_forbidden_inline_hashtags(text or "", extra_forbidden=extra_blocked)
    norm_text = unicodedata.normalize("NFC", scrubbed_text).lower()
    words = [w for w in _TOKEN_RE.findall(norm_text) if w not in blocked]
    bigrams = [f"{words[i]}_{words[i + 1]}" for i in range(len(words) - 1)]
    return words + bigrams + clean_tags


def grouped_author_split(
    df: pd.DataFrame,
    *,
    group_col: str = "author_handle",
    test_fraction: float = 0.30,
    seed: int = 42,
) -> tuple[np.ndarray, np.ndarray]:
    """Deterministic creator-disjoint split ensuring zero author overlap between partitions."""
    if not (0.05 <= test_fraction <= 0.5):
        raise ValueError("test_fraction must be within [0.05, 0.5]")
    authors = sorted({str(a) for a in df[group_col].tolist()})
    if len(authors) < 2:
        raise ValueError("Need at least 2 distinct authors for grouped held-out split")

    rng = np.random.default_rng(seed)
    shuffled = list(authors)
    rng.shuffle(shuffled)
    n_test_authors = max(1, int(round(len(shuffled) * test_fraction)))
    test_authors = set(shuffled[:n_test_authors])

    group_series = df[group_col].astype(str)
    is_test = group_series.isin(test_authors).to_numpy()
    train_idx = np.flatnonzero(~is_test)
    test_idx = np.flatnonzero(is_test)
    if len(train_idx) == 0 or len(test_idx) == 0:
        raise ValueError("Grouped split yielded an empty train or test partition")
    return train_idx, test_idx


def _compute_average_precision(y_true: np.ndarray, y_score: np.ndarray) -> float:
    n_pos = int(y_true.sum())
    if n_pos == 0 or n_pos == len(y_true):
        return float("nan")
    order = np.argsort(-y_score, kind="mergesort")
    sorted_y = y_true[order]
    tp_cum = np.cumsum(sorted_y)
    ranks = np.arange(1, len(sorted_y) + 1, dtype=np.float64)
    precisions = tp_cum / ranks
    return float((precisions * sorted_y).sum() / n_pos)


def _compute_brier_and_ece(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> tuple[float, float]:
    brier = float(np.mean((y_prob - y_true) ** 2))
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ece = 0.0
    n = len(y_true)
    for b_idx in range(n_bins):
        lo, hi = edges[b_idx], edges[b_idx + 1]
        if b_idx == n_bins - 1:
            mask = (y_prob >= lo) & (y_prob <= hi)
        else:
            mask = (y_prob >= lo) & (y_prob < hi)
        if mask.any():
            acc = float(y_true[mask].mean())
            conf = float(y_prob[mask].mean())
            ece += (float(mask.sum()) / n) * abs(acc - conf)
    return brier, float(ece)


def _bootstrap_metric_ci(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    *,
    groups: np.ndarray | None = None,
    n_boot: int = 500,
    seed: int = 42,
) -> dict[str, dict[str, float]]:
    rng = np.random.default_rng(seed)
    n = len(y_true)
    pr_vals: list[float] = []
    brier_vals: list[float] = []

    cluster_map: dict[str, np.ndarray] | None = None
    cluster_keys: list[str] = []
    if groups is not None and len(groups) == n:
        g_str = [str(g) for g in groups.tolist()]
        unique_g = sorted(set(g_str))
        if len(unique_g) >= 2:
            cluster_keys = unique_g
            g_arr = np.asarray(g_str)
            cluster_map = {k: np.flatnonzero(g_arr == k) for k in unique_g}

    for _ in range(n_boot):
        if cluster_map is not None:
            drawn_clusters = rng.integers(0, len(cluster_keys), size=len(cluster_keys))
            idx = np.concatenate([cluster_map[cluster_keys[int(ci)]] for ci in drawn_clusters])
        else:
            idx = rng.integers(0, n, size=n)
        yt = y_true[idx]
        yp = y_prob[idx]
        if 0 < int(yt.sum()) < len(yt):
            pr_vals.append(_compute_average_precision(yt, yp))
        brier_vals.append(float(np.mean((yp - yt) ** 2)))

    def _ci(vals: list[float], point: float) -> dict[str, float]:
        if not vals:
            return {"point": round(point, 4), "ci95_low": round(point, 4), "ci95_high": round(point, 4)}
        lo, hi = np.percentile(vals, [2.5, 97.5])
        return {"point": round(point, 4), "ci95_low": round(float(lo), 4), "ci95_high": round(float(hi), 4)}

    pt_pr = _compute_average_precision(y_true, y_prob)
    pt_brier = float(np.mean((y_prob - y_true) ** 2))
    return {"pr_auc": _ci(pr_vals, pt_pr), "brier_score": _ci(brier_vals, pt_brier)}


def _fit_tfidf_logreg(
    train_tokens: list[list[str]],
    test_tokens: list[list[str]],
    train_cats: list[str],
    test_cats: list[str],
    y_train: np.ndarray,
    *,
    min_df: int = 2,
    max_features: int = 4000,
    reg_lambda: float = 1.0,
) -> tuple[np.ndarray, list[str], np.ndarray]:
    df_counts: Counter[str] = Counter()
    for toks in train_tokens:
        for unique_tok in sorted(set(toks)):
            df_counts[unique_tok] += 1

    eligible_sorted = sorted(
        (
            (tok, cnt)
            for tok, cnt in df_counts.items()
            if cnt >= min_df and tok not in FORBIDDEN_DISCLOSURE_HASHTAGS
        ),
        key=lambda kv: (-kv[1], kv[0]),
    )
    kept = [tok for tok, _ in eligible_sorted[:max_features]]
    cat_vocab = sorted({c for c in train_cats if c})
    vocab: dict[str, int] = {tok: i for i, tok in enumerate(kept)}
    cat_offset = len(vocab)
    for j, cat in enumerate(cat_vocab):
        vocab[f"cat={cat}"] = cat_offset + j

    n_train = len(train_tokens)
    idf = np.ones(len(vocab), dtype=np.float64)
    for tok, idx in vocab.items():
        if idx < cat_offset:
            idf[idx] = math.log((1.0 + n_train) / (1.0 + df_counts[tok])) + 1.0

    def _vectorize(tokens_list: list[list[str]], cats_list: list[str]) -> sparse.csr_matrix:
        rows: list[int] = []
        cols: list[int] = []
        data: list[float] = []
        for r_i, (toks, cat) in enumerate(zip(tokens_list, cats_list)):
            tf = Counter(t for t in toks if t in vocab)
            for t, c in sorted(tf.items()):
                col = vocab[t]
                rows.append(r_i)
                cols.append(col)
                data.append((1.0 + math.log(float(c))) * float(idf[col]))
            cat_key = f"cat={cat}"
            if cat_key in vocab:
                rows.append(r_i)
                cols.append(vocab[cat_key])
                data.append(1.0)
        mat = sparse.csr_matrix(
            (np.asarray(data, dtype=np.float64), (rows, cols)),
            shape=(len(tokens_list), len(vocab) + 1),
        )
        if mat.shape[1] > 1:
            feat = mat[:, :-1]
            norms = sparse.linalg.norm(feat, axis=1)
            norms[norms == 0.0] = 1.0
            inv = sparse.diags(1.0 / norms)
            feat_normed = inv @ feat
            bias = sparse.csr_matrix(np.ones((len(tokens_list), 1), dtype=np.float64))
            return sparse.hstack([feat_normed, bias], format="csr")
        return sparse.csr_matrix(np.ones((len(tokens_list), 1), dtype=np.float64))

    x_train = _vectorize(train_tokens, train_cats)
    x_test = _vectorize(test_tokens, test_cats)

    def _loss_and_grad(weights: np.ndarray) -> tuple[float, np.ndarray]:
        logits = np.clip(x_train @ weights, -30.0, 30.0)
        probs = 1.0 / (1.0 + np.exp(-logits))
        eps = 1e-12
        nll = -np.mean(y_train * np.log(probs + eps) + (1.0 - y_train) * np.log(1.0 - probs + eps))
        w_feat = weights[:-1]
        reg = 0.5 * (reg_lambda / max(n_train, 1)) * float(np.dot(w_feat, w_feat))
        grad_logits = (probs - y_train) / max(n_train, 1)
        grad = np.asarray(x_train.T @ grad_logits, dtype=np.float64).ravel()
        grad[:-1] += (reg_lambda / max(n_train, 1)) * w_feat
        return float(nll + reg), grad

    w0 = np.zeros(x_train.shape[1], dtype=np.float64)
    opt = optimize.minimize(_loss_and_grad, w0, jac=True, method="L-BFGS-B", options={"maxiter": 150})
    w_hat = np.asarray(opt.x, dtype=np.float64)
    test_logits = np.clip(x_test @ w_hat, -30.0, 30.0)
    test_probs = 1.0 / (1.0 + np.exp(-test_logits))
    inv_vocab = [""] * len(vocab)
    for k, idx in vocab.items():
        inv_vocab[idx] = k
    return test_probs, inv_vocab, w_hat[:-1]


def evaluate_observed_ad_vs_ec_classifier(
    df: pd.DataFrame,
    *,
    feature_columns_declared: tuple[str, ...] = ("caption", "transcript", "hashtags", "food_category"),
    group_col: str = "author_handle",
    test_fraction: float = 0.30,
    seed: int = 42,
    n_boot: int = 500,
    min_df: int = 2,
    exclude_platform_campaign_tags: bool = False,
) -> dict[str, Any]:
    """Evaluate a leakage-free author-grouped classifier strictly on genuinely labeled ad-vs-EC rows.

    Excludes all unlabeled_unknown rows and ambiguous both-flagged rows so no unlabeled item
    is ever treated as a verified negative. Uses author-cluster bootstrap for 95% CIs.
    """
    assert_no_feature_leakage(feature_columns_declared)
    declared_set = set(feature_columns_declared)

    is_ad = df["is_ad"].fillna(False).astype(bool)
    is_ec = df["is_ec_video"].fillna(False).astype(bool)
    unlabeled_count = int((~is_ad & ~is_ec).sum())
    both_count = int((is_ad & is_ec).sum())
    labeled_mask = is_ad ^ is_ec
    sub = df.loc[labeled_mask].reset_index(drop=True)
    if len(sub) < 10:
        raise ValueError(f"Insufficient binary-labeled rows ({len(sub)}) for held-out evaluation")

    y_all = sub["is_ad"].astype(int).to_numpy()
    train_idx, test_idx = grouped_author_split(
        sub, group_col=group_col, test_fraction=test_fraction, seed=seed
    )

    train_authors = set(sub.iloc[train_idx][group_col].astype(str))
    test_authors = set(sub.iloc[test_idx][group_col].astype(str))

    use_cap = "caption" in declared_set
    use_tr = "transcript" in declared_set
    use_tags = "hashtags" in declared_set
    use_cat = "food_category" in declared_set

    tokens = [
        _tokenize_for_study(
            f"{(row.get('caption') or '') if use_cap else ''} {(row.get('transcript') or '') if use_tr else ''}",
            row.get("hashtags") if use_tags else None,
            exclude_platform_campaign_tags=exclude_platform_campaign_tags,
        )
        for row in sub.to_dict("records")
    ]
    cats = [str(c or "") if use_cat else "" for c in sub["food_category"].tolist()] if use_cat else [""] * len(sub)

    train_tokens = [tokens[i] for i in train_idx]
    test_tokens = [tokens[i] for i in test_idx]
    train_cats = [cats[i] for i in train_idx]
    test_cats = [cats[i] for i in test_idx]
    y_train = y_all[train_idx].astype(np.float64)
    y_test = y_all[test_idx].astype(np.float64)
    test_author_arr = sub.iloc[test_idx][group_col].astype(str).to_numpy()

    probs, feat_names, weights = _fit_tfidf_logreg(
        train_tokens,
        test_tokens,
        train_cats,
        test_cats,
        y_train,
        min_df=min_df,
    )
    pr_auc = _compute_average_precision(y_test, probs)
    brier, ece = _compute_brier_and_ece(y_test, probs)
    cis = _bootstrap_metric_ci(y_test, probs, groups=test_author_arr, n_boot=n_boot, seed=seed)
    cis_iid = _bootstrap_metric_ci(y_test, probs, groups=None, n_boot=n_boot, seed=seed)

    top_pos_idx = np.argsort(-weights)[:8] if len(weights) else np.array([], dtype=int)
    top_neg_idx = np.argsort(weights)[:8] if len(weights) else np.array([], dtype=int)

    excluded_tags = sorted(
        FORBIDDEN_DISCLOSURE_HASHTAGS
        | (PLATFORM_CAMPAIGN_META_TAGS if exclude_platform_campaign_tags else frozenset())
    )
    return {
        "target_name": "is_ad_only_vs_is_ec_only",
        "target_validity_note": (
            "Evaluates linguistic and food-category separability between genuinely flagged "
            "TikTok Ads (is_ad_only=1) and TikTok Shop commerce videos (is_ec_only=0). "
            "Does NOT evaluate unlabeled items as negatives and does NOT predict undisclosed sponsorship."
        ),
        "declared_input_features": list(feature_columns_declared),
        "prosody_features_joined": False,
        "exclude_platform_campaign_tags": exclude_platform_campaign_tags,
        "flag_leakage_excluded": excluded_tags,
        "unlabeled_excluded_count": unlabeled_count,
        "both_flags_excluded_count": both_count,
        "train_rows": int(len(train_idx)),
        "test_rows": int(len(test_idx)),
        "train_authors": len(train_authors),
        "test_authors": len(test_authors),
        "author_overlap_count": len(train_authors & test_authors),
        "test_positive_prevalence": round(float(y_test.mean()), 4),
        "bootstrap_mode": "author_cluster_resample",
        "metrics": {
            "pr_auc": round(pr_auc, 4),
            "brier_score": round(brier, 4),
            "ece_10bin": round(ece, 4),
            "bootstrap_95_ci": cis,
            "bootstrap_95_ci_row_iid_reference": cis_iid,
        },
        "top_ad_associated_features": [
            {"feature": feat_names[i], "weight": round(float(weights[i]), 4)}
            for i in top_pos_idx
        ],
        "top_ec_associated_features": [
            {"feature": feat_names[i], "weight": round(float(weights[i]), 4)}
            for i in top_neg_idx
        ],
    }


def compute_pu_observable_summary(df: pd.DataFrame) -> dict[str, Any]:
    """Summarize observable flag strata, lexical cue rates, and domain skew without PU negative assumptions."""
    is_ad = df["is_ad"].fillna(False).astype(bool)
    is_ec = df["is_ec_video"].fillna(False).astype(bool)
    flag_groups = [
        classify_observed_disclosure_flags(bool(a), bool(e))
        for a, e in zip(is_ad.tolist(), is_ec.tolist())
    ]
    captions = [str(c or "") for c in df["caption"].tolist()]
    transcripts = [str(t or "") for t in df["transcript"].tolist()]
    has_hashtags_col = "hashtags" in df.columns
    raw_hashtags = df["hashtags"].tolist() if has_hashtags_col else [None] * len(df)

    strata_summary: dict[str, Any] = {}
    group_arr = np.asarray(flag_groups)
    for status in (
        "observed_ad",
        "observed_ecommerce",
        "observed_ad_and_ecommerce",
        "unlabeled_unknown",
    ):
        idx = np.flatnonzero(group_arr == status)
        sub_df = df.iloc[idx]
        cat_rates: dict[str, float] = {}
        any_hits = 0
        for row_idx in idx:
            i = int(row_idx)
            ht = raw_hashtags[i]
            tags = (
                ht.tolist()
                if ht is not None and hasattr(ht, "tolist")
                else (list(ht) if isinstance(ht, (list, tuple)) else None)
            )
            _, matched_cats, _ = extract_promotional_indicators(
                caption=captions[i],
                transcript=transcripts[i],
                hashtags=tags,
            )
            if matched_cats:
                any_hits += 1
                for cat in matched_cats:
                    cat_rates[cat] = cat_rates.get(cat, 0.0) + 1.0
        denom = max(len(idx), 1)
        strata_summary[status] = {
            "row_count": int(len(idx)),
            "author_count": int(sub_df["author_handle"].nunique()),
            "transcribed_count": int(sub_df["has_transcript"].fillna(False).sum()),
            "has_cta_rate": round(float(sub_df["has_cta"].fillna(False).mean()), 4) if len(idx) and "has_cta" in sub_df.columns else 0.0,
            "any_promo_lexicon_rate": round(any_hits / denom, 4) if len(idx) else 0.0,
            "category_rates": {k: round(v / denom, 4) for k, v in sorted(cat_rates.items())},
            "top_food_categories": sub_df["food_category"].value_counts().head(4).to_dict(),
        }
    return {
        "total_rows": int(len(df)),
        "strata": strata_summary,
        "unlabeled_policy_note": (
            "unlabeled_unknown rows carry non-zero promotional lexicon hits and cannot be treated as "
            "verified organic/non-sponsored negatives."
        ),
    }


__all__ = [
    "compute_pu_observable_summary",
    "evaluate_observed_ad_vs_ec_classifier",
    "grouped_author_split",
    "strip_forbidden_inline_hashtags",
]
