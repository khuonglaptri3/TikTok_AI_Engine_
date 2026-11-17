from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.common.exceptions import IndexNotReadyError
from packages.common.logging import StageTimer
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest
from packages.data_contracts.retrieval import EvidenceCard, RetrievalResponse, VideoCitation
from packages.retrieval.dense.qdrant_adapter import QdrantDenseAdapter
from packages.retrieval.fusion.rrf import apply_viral_multiplier_boost, reciprocal_rank_fusion
from packages.retrieval.rerank.scorer import EvidenceReranker
from packages.retrieval.sparse.bm25 import BM25Index


def _as_str_list(val: Any) -> list[str]:
    if val is None:
        return []
    if isinstance(val, (list, tuple, np.ndarray)):
        return [str(x) for x in val if x is not None and str(x).strip()]
    return [str(val)] if str(val).strip() else []


class HybridRetrievalService:
    """Evidence retrieval service supporting Vietnamese BM25, Qdrant Dense, RRF, and Reranking."""

    def __init__(
        self,
        df_videos: pd.DataFrame,
        bm25_index: BM25Index,
        qdrant_adapter: QdrantDenseAdapter | None = None,
        reranker: EvidenceReranker | None = None,
    ) -> None:
        self.df_transcribed = df_videos[df_videos["has_transcript"]].copy()
        self.bm25 = bm25_index
        self.qdrant = qdrant_adapter
        self.reranker = reranker or EvidenceReranker(enabled=True)

        self.video_lookup: dict[str, dict[str, Any]] = {}
        self.viral_multipliers: dict[str, float] = {}
        for rec in self.df_transcribed.to_dict(orient="records"):
            vid = str(rec["video_id"])
            self.video_lookup[vid] = rec
            self.viral_multipliers[vid] = float(rec.get("viral_multiplier") or 0.0)

        self._dense_encoder: Any = None

    @classmethod
    def from_dirs(
        cls,
        df_videos: pd.DataFrame,
        bm25_dir: Path,
        qdrant_url: str = "http://127.0.0.1:6333",
        qdrant_collection: str = "tiktok_fnb_videos_v1",
        reranker_enabled: bool = True,
    ) -> HybridRetrievalService:
        bm25 = BM25Index.load(bm25_dir)
        qdrant = QdrantDenseAdapter(qdrant_url=qdrant_url, collection_name=qdrant_collection)
        return cls(
            df_videos=df_videos,
            bm25_index=bm25,
            qdrant_adapter=qdrant,
            reranker=EvidenceReranker(enabled=reranker_enabled),
        )

    def _resolve_candidate_pool(
        self,
        filters: NicheQueryFilter,
        min_pool_size: int = 8,
    ) -> tuple[set[str] | None, list[str]]:
        active: list[tuple[str, str]] = []
        for field in (
            "video_format",
            "food_category",
            "city_norm",
            "region",
            "price_tier",
            "occasion",
            "duration_bucket",
        ):
            val = getattr(filters, field)
            if val:
                active.append((field, str(val).strip()))

        if not active:
            return None, []

        df = self.df_transcribed

        def _match_ids(items: list[tuple[str, str]]) -> set[str]:
            mask = pd.Series(True, index=df.index)
            for k, v in items:
                if k == "occasion":
                    v_low = v.lower()
                    mask &= df["occasions"].apply(
                        lambda arr: v_low in [str(x).lower() for x in arr] if arr is not None else False
                    )
                elif k in ("city_norm", "region", "price_tier", "duration_bucket"):
                    mask &= df[k].fillna("").str.lower() == v.lower()
                else:
                    mask &= df[k].fillna("") == v
            return set(df.loc[mask, "video_id"].astype(str).tolist())

        strict_ids = _match_ids(active)
        if len(strict_ids) >= min_pool_size:
            return strict_ids, []

        relax_order = ["duration_bucket", "occasion", "price_tier", "city_norm", "region", "food_category", "video_format"]
        remaining = list(active)
        relaxed: list[str] = []
        best_non_empty = strict_ids

        for drop_key in relax_order:
            before_len = len(remaining)
            remaining = [(k, v) for k, v in remaining if k != drop_key]
            if len(remaining) < before_len:
                relaxed.append(drop_key)
                if not remaining:
                    return None, relaxed
                cand_ids = _match_ids(remaining)
                if len(cand_ids) > len(best_non_empty):
                    best_non_empty = cand_ids
                if len(cand_ids) >= min_pool_size:
                    return cand_ids, relaxed

        return (best_non_empty if best_non_empty else None), relaxed

    def _encode_dense_query(self, query: str) -> list[float] | None:
        try:
            if self._dense_encoder is None:
                from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]

                self._dense_encoder = SentenceTransformer("intfloat/multilingual-e5-base")
            vec = self._dense_encoder.encode(f"query: {query}", normalize_embeddings=True)
            return [float(x) for x in vec]
        except Exception:
            return None

    def search(self, request: RetrievalRequest) -> RetrievalResponse:
        timer = StageTimer()
        candidate_limit = max(40, request.top_k * 8)

        with timer.measure("filter_ms"):
            allowed_ids, relaxed_filters = self._resolve_candidate_pool(
                request.filters, min_pool_size=max(3, request.top_k)
            )

        bm25_hits: list[tuple[str, float]] = []
        dense_hits: list[tuple[str, float]] = []
        effective_mode = request.mode

        if request.mode in ("bm25", "hybrid_rrf"):
            with timer.measure("bm25_ms"):
                bm25_hits = self.bm25.search(
                    query=request.query,
                    top_k=candidate_limit,
                    allowed_video_ids=allowed_ids,
                )
                # If metadata filter eliminated lexical hits completely, relax back to full BM25 corpus
                if not bm25_hits and allowed_ids is not None:
                    bm25_hits = self.bm25.search(query=request.query, top_k=candidate_limit, allowed_video_ids=None)
                    if "lexical_fallback_unfiltered" not in relaxed_filters:
                        relaxed_filters.append("lexical_fallback_unfiltered")

        if request.mode in ("dense", "hybrid_rrf"):
            with timer.measure("dense_ms"):
                qdrant_ready = self.qdrant.check_collection_ready()[0] if self.qdrant else False
                if not qdrant_ready:
                    if request.mode == "dense":
                        raise IndexNotReadyError(
                            "Dense Qdrant collection is offline or empty. Start docker-compose Qdrant or use mode='bm25' / 'hybrid_rrf'."
                        )
                    effective_mode = "bm25"
                else:
                    q_vec = self._encode_dense_query(request.query)
                    if q_vec is None:
                        if request.mode == "dense":
                            raise IndexNotReadyError("Local dense embedding model is not installed.")
                        effective_mode = "bm25"
                    elif self.qdrant is not None:
                        dense_hits = self.qdrant.search_vectors(
                            query_vector=q_vec,
                            top_k=candidate_limit,
                            allowed_video_ids=allowed_ids,
                        )

        lexical_map = {vid: score for vid, score in bm25_hits}

        with timer.measure("fusion_ms"):
            if effective_mode == "hybrid_rrf" and dense_hits:
                fused_raw = reciprocal_rank_fusion([bm25_hits, dense_hits], rrf_k=60)
            elif effective_mode == "dense":
                fused_raw = dense_hits
            else:
                fused_raw = bm25_hits

            boosted = apply_viral_multiplier_boost(
                candidates=fused_raw,
                viral_multipliers=self.viral_multipliers,
                boost_weight=0.06,
            )

        with timer.measure("rerank_ms"):
            if request.rerank and self.reranker.enabled:
                final_tuples = self.reranker.rerank(
                    query=request.query,
                    candidates=boosted,
                    video_lookup=self.video_lookup,
                    top_k=request.top_k,
                )
                did_rerank = True
            else:
                final_tuples = [(vid, score, None) for vid, score in boosted[: request.top_k]]  # type: ignore[misc]
                did_rerank = False

        cards: list[EvidenceCard] = []
        for rank_idx, (vid, final_score, r_score) in enumerate(final_tuples, start=1):
            row = self.video_lookup.get(vid)
            if not row:
                continue
            tr_full = str(row.get("transcript") or "")
            excerpt = tr_full[:320] + ("..." if len(tr_full) > 320 else "")
            cards.append(
                EvidenceCard(
                    rank=rank_idx,
                    score=round(float(final_score), 4),
                    lexical_score=round(float(lexical_map.get(vid, 0.0)), 4),
                    rerank_score=round(float(r_score), 4) if r_score is not None else None,
                    citation=VideoCitation(
                        video_id=vid,
                        author_handle=str(row.get("author_handle") or ""),
                        tiktok_url=str(row.get("tiktok_url") or ""),
                        play_count=int(row.get("play_count") or 0),
                        viral_multiplier=float(row.get("viral_multiplier") or 0.0),
                        engagement_rate=float(row.get("engagement_rate") or 0.0),
                    ),
                    video_format=str(row.get("video_format") or "Review món ăn"),
                    food_category=str(row.get("food_category") or "Ẩm thực Tổng hợp"),
                    dishes=_as_str_list(row.get("dishes")),
                    city_norm=row.get("city_norm") if pd.notna(row.get("city_norm")) else None,
                    district_norm=row.get("district_norm") if pd.notna(row.get("district_norm")) else None,
                    poi_name=row.get("poi_name") if pd.notna(row.get("poi_name")) else None,
                    price_tier=str(row.get("price_tier") or "unspecified"),
                    occasions=_as_str_list(row.get("occasions")),
                    duration_sec=int(row.get("duration_sec") or 0),
                    duration_bucket=str(row.get("duration_bucket") or "short_20_45s"),
                    hook_text=str(row.get("hook_text") or ""),
                    body_beats=_as_str_list(row.get("body_beats")),
                    cta_text=str(row.get("cta_text") or ""),
                    transcript_excerpt=excerpt,
                )
            )

        return RetrievalResponse(
            query=request.query,
            mode=effective_mode,
            reranked=did_rerank,
            total_candidates=len(boosted),
            relaxed_filters=relaxed_filters,
            items=cards,
            timings_ms=timer.finalize(),
        )
