"""Unified Gold Corpus builder (dim_creators.parquet + fact_videos.parquet + manifest.json)."""

from pipelines.build_gold_corpus.builder import build_gold_corpus, compute_engagement_rate, compute_viral_multiplier

__all__ = ["build_gold_corpus", "compute_engagement_rate", "compute_viral_multiplier"]
