from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.common.exceptions import IndexNotReadyError
from packages.common.logging import StageTimer
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest
from packages.data_contracts.retrieval import EvidenceCard, RetrievalResponse, VideoCitation
from packages.retrieval.dense.encoder import DenseTextEncoder, load_saved_encoder
from packages.retrieval.dense.local_index import LocalDenseIndex
from packages.retrieval.dense.qdrant_adapter import QdrantDenseAdapter
from packages.retrieval.fusion.rrf import apply_viral_multiplier_boost, reciprocal_rank_fusion
from packages.retrieval.query_intent import (
    check_vocab_anchor_support,
    parse_query_intent,
    row_has_observed_anchor_word_overlap,
    row_satisfies_intent_anchors,
)
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
        dense_index: LocalDenseIndex | None = None,
        dense_encoder: DenseTextEncoder | None = None,
        restrict_to_df: bool = False,
    ) -> None:
        self.df_transcribed = df_videos[df_videos["has_transcript"]].copy()
        self.bm25 = bm25_index
        self.qdrant = qdrant_adapter
        self.dense_index = dense_index
        self.reranker = reranker or EvidenceReranker(enabled=True)
        self._restrict_to_df = restrict_to_df

        self.video_lookup: dict[str, dict[str, Any]] = {}
        self.viral_multipliers: dict[str, float] = {}
        for rec in self.df_transcribed.to_dict(orient="records"):
            vid = str(rec["video_id"])
            self.video_lookup[vid] = rec
            self.viral_multipliers[vid] = float(rec.get("viral_multiplier") or 0.0)

        self._dense_encoder: Any = dense_encoder

    @classmethod
    def from_dirs(
        cls,
        df_videos: pd.DataFrame,
        bm25_dir: Path,
        qdrant_url: str = "http://127.0.0.1:6333",
        qdrant_collection: str = "tiktok_fnb_videos_v1",
        reranker_enabled: bool = True,
        dense_dir: Path | None = None,
        restrict_to_df: bool = False,
    ) -> HybridRetrievalService:
        bm25 = BM25Index.load(bm25_dir)
        qdrant = QdrantDenseAdapter(qdrant_url=qdrant_url, collection_name=qdrant_collection)
        dense_index: LocalDenseIndex | None = None
        dense_encoder: DenseTextEncoder | None = None
        if dense_dir is not None and dense_dir.exists():
            dense_index = LocalDenseIndex.load(dense_dir)
            dense_encoder = load_saved_encoder(dense_dir)
        return cls(
            df_videos=df_videos,
            bm25_index=bm25,
            qdrant_adapter=qdrant,
            reranker=EvidenceReranker(enabled=reranker_enabled),
            dense_index=dense_index,
            dense_encoder=dense_encoder,
            restrict_to_df=restrict_to_df,
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

        has_geo_filter = any(k in ("city_norm", "region") for k, _ in active)
        strict_ids = _match_ids(active)
        if len(strict_ids) >= min_pool_size:
            return strict_ids, []

        # Keep explicit geographic filters (city_norm, region) strict so retrieval never
        # fabricates cross-city support; relax only soft format/category/context facets.
        relax_order = ["duration_bucket", "occasion", "price_tier", "food_category", "video_format"]
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

        if has_geo_filter:
            return best_non_empty, relaxed
        return (best_non_empty if best_non_empty else None), relaxed

    def _encode_dense_query(self, query: str) -> list[float] | None:
        try:
            if self._dense_encoder is None:
                return None
            if isinstance(self._dense_encoder, DenseTextEncoder):
                return self._dense_encoder.encode_query(query)
            vec = self._dense_encoder.encode(f"query: {query}", normalize_embeddings=True)
            return [float(x) for x in vec]
        except Exception:
            return None

    def search(self, request: RetrievalRequest) -> RetrievalResponse:
        timer = StageTimer()
        candidate_limit = max(40, request.top_k * 8)
        intent = parse_query_intent(request.query)
        if not intent.positive_query and intent.negated_terms:
            return RetrievalResponse(
                query=request.query,
                mode=request.mode,
                reranked=False,
                total_candidates=0,
                relaxed_filters=[],
                items=[],
                insufficient_evidence=True,
                abstain_reason="query_contains_only_negations",
                timings_ms=timer.finalize(),
            )
        has_geo_filter = bool(request.filters.city_norm or request.filters.region)

        with timer.measure("filter_ms"):
            allowed_ids, relaxed_filters = self._resolve_candidate_pool(
                request.filters, min_pool_size=max(3, request.top_k)
            )
            if allowed_ids is not None and len(allowed_ids) == 0:
                return RetrievalResponse(
                    query=request.query,
                    mode=request.mode,
                    reranked=False,
                    total_candidates=0,
                    relaxed_filters=relaxed_filters,
                    items=[],
                    insufficient_evidence=True,
                    abstain_reason="no_indexed_videos_in_requested_location",
                    timings_ms=timer.finalize(),
                )
            if allowed_ids is None and self._restrict_to_df:
                allowed_ids = set(self.video_lookup.keys())

        early_oov = check_vocab_anchor_support(intent, self.bm25.vocab) if self.bm25.vocab else None
        if request.mode in ("bm25", "hybrid_rrf") and early_oov is not None:
            return RetrievalResponse(
                query=request.query,
                mode=request.mode,
                reranked=False,
                total_candidates=0,
                relaxed_filters=relaxed_filters,
                items=[],
                insufficient_evidence=True,
                abstain_reason=early_oov,
                timings_ms=timer.finalize(),
            )

        bm25_hits: list[tuple[str, float]] = []
        dense_hits: list[tuple[str, float]] = []
        effective_mode = request.mode
        bm25_query = intent.expanded_bm25_query or intent.normalized_query

        if request.mode in ("bm25", "hybrid_rrf"):
            with timer.measure("bm25_ms"):
                bm25_hits = self.bm25.search(
                    query=bm25_query,
                    top_k=candidate_limit,
                    allowed_video_ids=allowed_ids,
                )
                if not bm25_hits and allowed_ids is not None:
                    if has_geo_filter:
                        if not intent.has_specific_anchors:
                            ranked_geo = sorted(
                                allowed_ids,
                                key=lambda vid: self.viral_multipliers.get(vid, 0.0),
                                reverse=True,
                            )[:candidate_limit]
                            bm25_hits = [(vid, 0.1) for vid in ranked_geo]
                    else:
                        fallback_ids = set(self.video_lookup.keys()) if self._restrict_to_df else None
                        bm25_hits = self.bm25.search(
                            query=bm25_query,
                            top_k=candidate_limit,
                            allowed_video_ids=fallback_ids,
                        )
                        if "lexical_fallback_unfiltered" not in relaxed_filters:
                            relaxed_filters.append("lexical_fallback_unfiltered")

        if request.mode in ("dense", "hybrid_rrf"):
            with timer.measure("dense_ms"):
                local_ready = self.dense_index.check_collection_ready()[0] if self.dense_index else False
                qdrant_ready = (
                    False
                    if local_ready
                    else (self.qdrant.check_collection_ready()[0] if self.qdrant else False)
                )
                if not local_ready and not qdrant_ready:
                    if request.mode == "dense":
                        raise IndexNotReadyError(
                            "Dense vector index is offline or empty. Build local dense index, start Qdrant, or use mode='bm25' / 'hybrid_rrf'."
                        )
                    effective_mode = "bm25"
                else:
                    if early_oov is not None:
                        return RetrievalResponse(
                            query=request.query,
                            mode=effective_mode,
                            reranked=False,
                            total_candidates=0,
                            relaxed_filters=relaxed_filters,
                            items=[],
                            insufficient_evidence=True,
                            abstain_reason=early_oov,
                            timings_ms=timer.finalize(),
                        )
                    dense_query = intent.positive_query or intent.normalized_query
                    q_vec = self._encode_dense_query(dense_query)
                    if q_vec is None:
                        if request.mode == "dense":
                            raise IndexNotReadyError("Dense embedding model is unavailable.")
                        effective_mode = "bm25"
                    elif local_ready and self.dense_index is not None:
                        dense_hits = self.dense_index.search_vectors(
                            query_vector=q_vec,
                            top_k=candidate_limit,
                            allowed_video_ids=allowed_ids,
                        )
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

            in_lookup_raw = [(vid, score) for vid, score in fused_raw if vid in self.video_lookup]
            boosted = apply_viral_multiplier_boost(
                candidates=in_lookup_raw,
                viral_multipliers=self.viral_multipliers,
                boost_weight=0.06,
            )

        if effective_mode in ("bm25", "hybrid_rrf", "dense"):
            oov_reason = (
                check_vocab_anchor_support(intent, self.bm25.vocab) if self.bm25.vocab else None
            )
            if oov_reason is not None:
                return RetrievalResponse(
                    query=request.query,
                    mode=effective_mode,
                    reranked=False,
                    total_candidates=0,
                    relaxed_filters=relaxed_filters,
                    items=[],
                    insufficient_evidence=True,
                    abstain_reason=oov_reason,
                    timings_ms=timer.finalize(),
                )
            if intent.has_specific_anchors:
                tier_1 = [
                    (vid, score)
                    for vid, score in boosted
                    if vid in self.video_lookup
                    and row_satisfies_intent_anchors(self.video_lookup[vid], intent)
                ]
                if not tier_1:
                    reason = (
                        "no_matching_evidence_in_requested_location"
                        if has_geo_filter
                        else "no_candidate_matches_query_anchors"
                    )
                    return RetrievalResponse(
                        query=request.query,
                        mode=effective_mode,
                        reranked=False,
                        total_candidates=0,
                        relaxed_filters=relaxed_filters,
                        items=[],
                        insufficient_evidence=True,
                        abstain_reason=reason,
                        timings_ms=timer.finalize(),
                    )
                if len(tier_1) >= request.top_k:
                    boosted = tier_1
                else:
                    tier_1_ids = {vid for vid, _ in tier_1}
                    tier_2 = [
                        (vid, score * 0.5)
                        for vid, score in boosted
                        if vid not in tier_1_ids
                        and vid in self.video_lookup
                        and row_has_observed_anchor_word_overlap(self.video_lookup[vid], intent)
                    ]
                    boosted = tier_1 + tier_2

        with timer.measure("rerank_ms"):
            if request.rerank and self.reranker.enabled:
                final_tuples = self.reranker.rerank(
                    query=intent.positive_query or intent.normalized_query,
                    candidates=boosted,
                    video_lookup=self.video_lookup,
                    top_k=request.top_k,
                    negated_terms=intent.negated_terms,
                )
                did_rerank = True
            else:
                final_tuples = [(vid, score, None) for vid, score in boosted[: request.top_k]]  # type: ignore[misc]
                did_rerank = False

        cards: list[EvidenceCard] = []
        for vid, final_score, r_score in final_tuples:
            row = self.video_lookup.get(vid)
            if not row:
                continue
            rank_idx = len(cards) + 1
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
