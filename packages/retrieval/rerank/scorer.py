from __future__ import annotations

import math
import unicodedata
from typing import Any

from packages.retrieval.sparse.bm25 import tokenize_vietnamese
from packages.taxonomy import extract_dishes_from_text, extract_occasions, extract_price_tier


class EvidenceReranker:
    """Vietnamese phrase, dish/context alignment, and script-anatomy completeness reranker."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled

    def rerank(
        self,
        query: str,
        candidates: list[tuple[str, float]],
        video_lookup: dict[str, dict[str, Any]],
        top_k: int = 5,
    ) -> list[tuple[str, float, float]]:
        """Return list of (video_id, final_score, rerank_score)."""
        if not candidates:
            return []
        if not self.enabled:
            return [(vid, score, score) for vid, score in candidates[:top_k]]

        q_nfc = unicodedata.normalize("NFC", query).lower()
        q_tokens = set(tokenize_vietnamese(q_nfc, include_bigrams=True))
        q_bigrams = {t.replace("_", " ") for t in q_tokens if "_" in t}
        q_dishes = set(extract_dishes_from_text(q_nfc))
        q_price = extract_price_tier(q_nfc, "")
        q_occasions = set(extract_occasions(q_nfc, ""))

        reranked: list[tuple[str, float, float]] = []
        for vid, base_score in candidates:
            row = video_lookup.get(vid)
            if not row:
                continue

            lead_text = unicodedata.normalize(
                "NFC",
                f"{row.get('caption', '')} {row.get('poi_name') or ''} {row.get('hook_text', '')}",
            ).lower()
            doc_text = unicodedata.normalize(
                "NFC",
                f"{lead_text} {row.get('transcript', '')[:800]}",
            ).lower()
            doc_tokens = set(tokenize_vietnamese(doc_text, include_bigrams=True))

            overlap_ratio = len(q_tokens & doc_tokens) / max(len(q_tokens), 1)
            lead_phrase_hits = sum(1 for bg in q_bigrams if bg in lead_text)
            lead_bonus = min(0.24, 0.08 * lead_phrase_hits)

            raw_dishes = row.get("dishes")
            row_dishes = {str(d).lower() for d in (raw_dishes if raw_dishes is not None else [])}
            dish_bonus = 0.18 if (q_dishes and (q_dishes & row_dishes)) else 0.0

            price_bonus = (
                0.08
                if (q_price != "unspecified" and row.get("price_tier") == q_price)
                else 0.0
            )
            raw_occ = row.get("occasions")
            row_occ = {str(o).lower() for o in (raw_occ if raw_occ is not None else [])}
            occ_bonus = 0.06 if (q_occasions & row_occ) else 0.0

            # Reward videos with rich script anatomy (clear hook + body beats + CTA)
            beats = row.get("body_beats")
            beat_count = len(beats) if beats is not None else 0
            anatomy_bonus = 0.05 if (row.get("hook_text") and beat_count >= 2) else 0.0

            v_mult = max(0.0, min(float(row.get("viral_multiplier") or 1.0), 40.0))
            viral_signal = 0.04 * math.log1p(v_mult)

            rerank_score = round(
                0.55 * base_score
                + 0.30 * overlap_ratio
                + lead_bonus
                + dish_bonus
                + price_bonus
                + occ_bonus
                + anatomy_bonus
                + viral_signal,
                5,
            )
            reranked.append((vid, rerank_score, rerank_score))

        reranked.sort(key=lambda item: item[1], reverse=True)
        return reranked[:top_k]
