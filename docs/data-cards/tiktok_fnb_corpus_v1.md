# Data Card — TikTok Vietnamese F&B Gold Corpus (`20261117_recovered_v1`)

## 1. Snapshot Summary
- **Active Default Snapshot ID:** `20261117_recovered_v1` (`data/corpus/20261117_recovered_v1/`) — rebuilt from preserved upstream archives after `20261116_v1` (`manifest.json` retained for reference).
- **Observation Window:** `2023-11-25` → `2025-03-19` (`Asia/Ho_Chi_Minh`)
- **Creators (`dim_creators.parquet`):** `264` Vietnamese F&B creators (`15` columns)
- **Videos (`fact_videos.parquet`):** `70,996` deduplicated videos (`49` columns)
- **Spoken Vietnamese Transcripts:** `21,748` validated speech transcripts (`30.63%`, purged of LLM refusal strings and non-speech placeholders)
- **Platform GPS POI Tags (`poi_name`):** `23,448` videos (`33.03%`) recovered from `data/interim/final_raw_videos.csv`
- **TikTok Shop / E-Commerce Flagged (`is_ec_video`):** `5,798` videos (`8.17%`)
- **Platform Ad Disclosure (`is_ad`):** `4,779` videos (`6.73%`)

## 2. Lineage, Per-Field Coverage & Unknown Handling (`M1.1` Audit)
All upstream raw, interim, processed, transcript, content-analysis, and legacy application datasets (`37,840` files) are preserved untouched in `data/` and `archive/legacy_coursework/`. Full per-column lineage and coverage across all `49` video columns and `15` creator columns are recorded in [field_coverage.csv](../reports/milestones/M1.1/evidence/field_coverage.csv) and [field_lineage_and_coverage.json](../reports/milestones/M1.1/evidence/field_lineage_and_coverage.json).

### Key Coverage & Unknown Observations on `20261117_recovered_v1`
- **Geography (`city_norm`, `district_norm`, `region`, `location_source`):**
  - `location_source`: `poi_gps` (`13,794` / `19.43%`), `llm_inferred` (`2,208` / `3.11%`), `district_resolved` (`1,012` / `1.43%`), `unknown` (`53,982` / `76.04%`).
  - `city_norm` non-null: `17,014` (`23.96%`); `district_norm` non-null: `4,670` (`6.58%`); `region` non-`unknown`: `15,931` (`22.44%`).
  - **Audit finding (`M1.1`):** `9,212` videos had `poi_name` populated (e.g., `"Ho Chi Minh City"`, `"Hanoi"`) with `city_norm = null`, and `1,083` had unmapped `city_norm` aliases (`"hue"`, `"district 5"`, `"nhà bè"`, `"long biên"`) leaving `region = "unknown"`. These resolver gaps were fixed in `packages/taxonomy/location_poi.py` for the next immutable `M1.2` snapshot build.
- **Taxonomy & Context (`video_format`, `food_category`, `price_tier`, `dishes`, `occasions`):**
  - `video_format`: `100%` populated via legacy `content_analysis` labels (`3,004` rows) or heuristic rules (`infer_video_format`).
  - `food_category`: `100%` populated, with `29,732` (`41.88%`) falling into `"Ẩm thực Tổng hợp"`.
  - `price_tier`: `59,068` (`83.20%`) explicitly marked `"unspecified"` when no price signal is present.
  - **Audit findings (`M1.1`):**
    1. `dishes` in `20261117_recovered_v1` contains `5,391` `"ốc"` tags, of which **`3,811` (`70.69%`) were false substring matches** (e.g., `"Trung Quốc"`, `"tốc độ"`). Fixed with word-boundary matching in `packages/taxonomy/food_hierarchy.py` for future builds.
    2. `occasions` in `20261117_recovered_v1` assigned `"an_vat_xe_chieu"` to `59,765` (`84.18%`) videos due to a default fallback when no occasion keyword matched. Fixed to return `[]` (`unknown`) in `packages/taxonomy/rule_extractor.py` for future builds.
- **Safe Ratios & Numeric Invariants:**
  - `engagement_rate`: `(digg_count + comment_count + share_count + collect_count) / play_count`, strictly `0.0` when `play_count == 0` (`1` row verified).
  - `viral_multiplier`: `play_count / max(creator_median_play_count, 1000.0)` — normalizes breakout performance across creator tiers.
  - `word_per_second`: `word_count / duration_sec`, strictly `0.0` when `duration_sec == 0` (`5,646` rows verified); `12` outlier rows exceed `10.0` wps due to very short metadata durations.

## 3. Geography Disambiguation Rules
1. `poi_gps`: Official TikTok GPS `poi.city`, `poi.address`, or unambiguous `poi.name` wins over caption/LLM guesses.
2. `district_resolved`: Unambiguous district overrides dish-origin city confusion (e.g., *"Bún đậu Hà Nội ở Quận 7"* resolves to `city_norm="hồ chí minh"`, `district_norm="quận 7"`, with longest-first boundary matching so `quận 10..12` never collide with `quận 1`).
3. `llm_inferred`: Fallback to standardized legacy LLM city extraction; missing/ambiguous locations remain `None` / `"unknown"`.

## 4. Known Caveats & Non-Claims
1. **Machine Labels Are Not Ground Truth:** Heuristic rules and legacy Gemini labels (`video_format`, `food_category`, `dishes`, `price_tier`, `occasions`, `hook_text`, `cta_text`) are operational approximations with measured error modes; human-audited error rates are tracked in `M1.1`.
2. **POIs Do Not Prove Physical Attendance:** TikTok platform POI tags (`poi_name`, `poi_city`, `poi_address`) indicate metadata attached to an upload, not verified physical dining attendance or current venue operation.
3. **Creator-Centric Cohort:** Videos come from `264` tracked F&B channels rather than a uniform random sample of all TikTok Vietnam uploads.
4. **Single-Snapshot Engagement:** View and interaction counts reflect a March–April 2025 collection snapshot rather than fixed-horizon (`T+7d`) curves.
5. **Transcript Selection:** Spoken transcripts prioritize top weekly performing and enriched subsets (`21,748` videos), whereas metadata and POI benchmarks span all `70,996` videos.
