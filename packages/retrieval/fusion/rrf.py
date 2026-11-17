from __future__ import annotations

import math


def reciprocal_rank_fusion(
    ranked_lists: list[list[tuple[str, float]]],
    rrf_k: int = 60,
) -> list[tuple[str, float]]:
    """Fuse multiple ranked candidate lists via Reciprocal Rank Fusion (RRF)."""
    fused: dict[str, float] = {}
    for candidates in ranked_lists:
        for rank_idx, (vid, _) in enumerate(candidates, start=1):
            fused[vid] = fused.get(vid, 0.0) + (1.0 / (rrf_k + rank_idx))
    return sorted(fused.items(), key=lambda kv: kv[1], reverse=True)


def apply_viral_multiplier_boost(
    candidates: list[tuple[str, float]],
    viral_multipliers: dict[str, float],
    boost_weight: float = 0.06,
) -> list[tuple[str, float]]:
    """Apply bounded logarithmic creator-normalized viral boost without drowning relevance."""
    if not candidates:
        return []
    max_base = max(score for _, score in candidates) or 1.0
    scored: list[tuple[str, float]] = []
    for vid, base_score in candidates:
        norm_base = base_score / max_base
        v_mult = max(0.0, min(float(viral_multipliers.get(vid, 1.0)), 50.0))
        viral_bonus = boost_weight * math.log1p(v_mult)
        scored.append((vid, round(norm_base + viral_bonus, 5)))
    return sorted(scored, key=lambda kv: kv[1], reverse=True)
