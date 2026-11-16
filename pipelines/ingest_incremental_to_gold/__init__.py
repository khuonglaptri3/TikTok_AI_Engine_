"""Dual-Sink Normalization Pipeline: merges 4-month incremental crawls into Gold fact_videos + multimodal tables."""

from pipelines.ingest_incremental_to_gold.converter import ingest_incremental_batch_to_gold

__all__ = ["ingest_incremental_batch_to_gold"]
