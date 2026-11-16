# Data Card — TikTok Vietnamese F&B Gold Corpus (`20261116_v1`)

## 1. Snapshot Summary
- **Snapshot ID:** `20261116_v1` (`data/corpus/20261116_v1/`)
- **Observation Window:** `2023-11-25` → `2025-03-19` (`Asia/Ho_Chi_Minh`)
- **Creators (`dim_creators.parquet`):** `264` Vietnamese F&B creators (`15` columns)
- **Videos (`fact_videos.parquet`):** `70,996` deduplicated videos (`49` columns)
- **Spoken Vietnamese Transcripts:** `21,748` validated speech transcripts (purged of LLM refusal strings and non-speech placeholders)
- **Restored Official TikTok GPS POIs:** `23,448` videos (`poi_name`, `poi_address`, `poi_city`, `poi_category_tiny`) recovered from `data/interim/final_raw_videos.csv`
- **TikTok Shop / E-Commerce Flagged (`is_ec_video`):** `5,798` videos

## 2. Lineage & 100% Data Preservation
All upstream raw, interim, processed, transcript, content-analysis, and legacy application datasets (`37,840` files, `~1.50 GB`) are preserved untouched in `data/` and `archive/legacy_coursework/`. The Gold Corpus pipeline (`python3 -m pipelines.build_gold_corpus`) reads upstream tables non-destructively and emits Snappy-compressed Parquet artifacts verified via `manifest.json` SHA256 checksums.

## 3. Canonical Metrics & Disambiguation Rules
- **`engagement_rate`:** `(digg_count + comment_count + share_count + collect_count) / max(play_count, 1)` (`0.0` when `play_count == 0`).
- **`viral_multiplier`:** `play_count / max(creator_median_play_count, 1000.0)` — normalizes breakout performance across micro, mid, macro, and mega creators so retrieval does not collapse onto mega-channels.
- **Geography Disambiguation (`location_source`):**
  1. `poi_gps`: Official TikTok GPS `poi.city` / `poi.address` wins over caption/LLM guesses.
  2. `district_resolved`: Unambiguous district overrides dish-origin city confusion (e.g., *"Bún đậu Hà Nội ở Quận 7"* resolves to `city_norm="hồ chí minh"`, `district_norm="quận 7"`).
  3. `llm_inferred`: Fallback to standardized legacy LLM city extraction.

## 4. Known Caveats
1. **Creator-Centric Cohort:** Videos come from 264 tracked F&B channels rather than a uniform random sample of all TikTok Vietnam uploads.
2. **Single-Snapshot Engagement:** View and interaction counts reflect a March–April 2025 collection snapshot rather than fixed-horizon (`T+7d`) curves.
3. **Transcript Selection:** Spoken transcripts prioritize top weekly performing and enriched subsets (`21,748` videos), whereas niche metadata & POI benchmarks span all `70,996` videos.
