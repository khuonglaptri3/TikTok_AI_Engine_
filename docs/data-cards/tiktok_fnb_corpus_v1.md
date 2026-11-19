# Data Card — TikTok Vietnamese F&B Gold Corpus (`20261117_recovered_v1` & `20261118_taxonomy_fix_v1`)

## 1. Snapshot Summary & Immutable Lineage
- **Taxonomy-Corrected Gold Snapshot (`M1.2`):** `20261118_taxonomy_fix_v1` (`data/corpus/20261118_taxonomy_fix_v1/`, `manifest.json` SHA256 `49f23739f9e2ea8f1f66fe1b299fe636c19965c99fcadf2bdd6eef7dc18c27de`, built `2026-11-18T05:43:03.050042+00:00`) — immutable child snapshot explicitly bound to `parent_snapshot_id="20261117_recovered_v1"` (`parent_manifest_sha256="10ed9c666707319f0a67c688e77d79ddc409e11c1f57ff075a01a3d718b714f4"`).
- **Recovered Baseline Snapshot (`M0.1`):** `20261117_recovered_v1` (`data/corpus/20261117_recovered_v1/`, `manifest.json` SHA256 `10ed9c666707319f0a67c688e77d79ddc409e11c1f57ff075a01a3d718b714f4`) — preserved untouched alongside legacy `20261116_v1/manifest.json`.
- **Observation Window:** `2023-11-25` → `2025-03-19` (`Asia/Ho_Chi_Minh`)
- **Creators (`dim_creators.parquet`):** `264` Vietnamese F&B creators (`15` columns)
- **Videos (`fact_videos.parquet`):** `70,996` deduplicated videos (`49` columns)
- **Spoken Vietnamese Transcripts:** `21,748` validated speech transcripts (`30.63%`, filtered for refusal strings and non-speech placeholders)
- **Platform GPS POI Tags (`poi_name`):** `23,448` videos (`33.03%`) recovered from `data/interim/final_raw_videos.csv`
- **TikTok Shop / E-Commerce Flagged (`is_ec_video`):** `5,798` videos (`8.17%`)
- **Platform Ad Disclosure (`is_ad`):** `4,779` videos (`6.73%`)

## 2. Lineage, Per-Field Coverage, Unknown Handling & `M1.2` Deltas
All upstream raw, interim, processed, transcript, content-analysis, and legacy application datasets (`37,840` files across the owner archive; `37,837` upstream revision `f142e5656a220f94f8024de168b0832754b3bd9e` files) are preserved untouched on disk. Complete per-column lineage and coverage across all `49` video columns and `15` creator columns are published in [field_coverage.csv](../reports/milestones/M1.1/evidence/field_coverage.csv), [field_lineage_and_coverage.json](../reports/milestones/M1.1/evidence/field_lineage_and_coverage.json), and [m1.2-build-receipt.json](../reports/milestones/M1.2/evidence/m1.2-build-receipt.json).

### Measured Coverage Comparison (`20261117_recovered_v1` vs `20261118_taxonomy_fix_v1`)

| Field / Metric | `20261117_recovered_v1` | `20261118_taxonomy_fix_v1` (`M1.2`) | Delta | Resolution Provenance |
| --- | ---: | ---: | ---: | --- |
| `city_norm` non-null | `17,014` (`23.96%`) | `23,478` (`33.07%`) | `+6,464` | `poi_name` fallback + English/unaccented city/district aliases (`packages/taxonomy/location_poi.py`) |
| `district_norm` non-null | `4,670` (`6.58%`) | `13,151` (`18.52%`) | `+8,481` | `District 1..12` aliases + longest-first word-boundary matching (`quận 10..12` vs `quận 1`) |
| `region != "unknown"` | `15,931` (`22.44%`) | `22,986` (`32.38%`) | `+7,055` | Expanded `CITY_TO_REGION` mapping; remaining `47,010+` unknown rows stay `"unknown"` |
| Videos tagged with dish `"ốc"` | `5,391` (`7.59%`) | `1,606` (`2.26%`) | `-3,785` | Word-boundary regex eliminating substring collisions (`"Trung Quốc"`, `"tốc độ"`, `"gần dốc"`, `"gốc"`) |
| Videos tagged `"an_vat_xe_chieu"` | `59,765` (`84.18%`) | `1,365` (`1.92%`) | `-58,400` | Removed forced default fallback in `packages/taxonomy/rule_extractor.py`; unmatched rows return `[]` |
| `price_tier == "unspecified"` | `59,068` (`83.20%`) | `59,068` (`83.20%`) | `0` | Explicit `"unspecified"` preserved when no price signal is observed |

### Safe Ratios & Numeric Invariants (Verified on Both Snapshots)
- `engagement_rate`: `(digg_count + comment_count + share_count + collect_count) / play_count`, strictly `0.0` when `play_count == 0` (`1` row verified; `0` `NaN`/`Inf`).
- `viral_multiplier`: `play_count / max(creator_median_play_count, 1000.0)` (`0` `NaN`/`Inf`).
- `word_per_second`: `word_count / duration_sec`, strictly `0.0` when `duration_sec == 0` (`5,646` rows verified; `0` `NaN`/`Inf`; `12` outlier rows exceed `10.0` wps due to short platform metadata durations).

### Sampled Error & Inter-Annotator Audit (`M1.1`, `n = 120` Stratified Sample)
In [M1.1/README.md](../reports/milestones/M1.1/README.md) ([audit_sample_120.csv](../reports/milestones/M1.1/evidence/audit_sample_120.csv), [khuong_m1_1_review_and_agreement.json](../reports/milestones/M1.1/evidence/khuong_m1_1_review_and_agreement.json)):
- Blinded manual human coding (`K_*`, `n = 30` overlap rows) vs Gemini-assisted coding reviewed by `N` (`N_*`, `n = 120` rows):
  - `city_correct`: `96.67%` agreement ($\kappa = 0.9231$; `K` baseline error rate `10/30 = 33.33%` prior to `M1.2` rebuild).
  - `dishes_false_positive`: `90.00%` agreement ($\kappa = 0.6667$; `K` baseline false-positive row rate `5/30 = 16.67%` prior to `M1.2` rebuild).
  - `format_correct`: `70.00%` agreement ($\kappa = 0.1318$; `K` human error rate `9/30 = 30.00%` + `1` uncertain).
  - `category_correct`: `63.33%` agreement ($\kappa = 0.2180$; `K` human error rate `13/30 = 43.33%`, reflecting residual `"cắt sợi"` / non-F&B lifestyle sponsor vlog collisions).
- `N_*` labels are explicitly documented as LLM-assisted review labels rather than unassisted human ground truth.

## 3. Geography Disambiguation Rules
1. `poi_gps`: Official TikTok GPS `poi.city`, `poi.address`, or unambiguous `poi.name` wins over caption/LLM guesses.
2. `district_resolved`: Unambiguous district overrides dish-origin city confusion (e.g., *"Bún đậu Hà Nội ở Quận 7"* resolves to `city_norm="hồ chí minh"`, `district_norm="quận 7"`, with longest-first boundary matching so `quận 10..12` never collide with `quận 1`).
3. `llm_inferred`: Fallback to standardized legacy LLM city extraction; missing/ambiguous locations remain `None` / `"unknown"`.

## 4. Known Caveats & Non-Claims
1. **Machine Labels Are Not Ground Truth:** Heuristic rules and legacy Gemini labels (`video_format`, `food_category`, `dishes`, `price_tier`, `occasions`, `hook_text`, `cta_text`) are operational approximations with documented error rates (`M1.1`), not ground-truth semantic labels.
2. **POIs Do Not Prove Physical Attendance:** TikTok platform POI tags (`poi_name`, `poi_city`, `poi_address`) record upload metadata, not verified physical dining attendance or current venue operation.
3. **Refusal Filtering Is Not ASR Word Accuracy:** Filtering empty/refusal transcripts (`21,748` accepted) does not establish word error rate (WER/CER) or exact speech timestamps; historical timings remain `wps_estimated`.
4. **Creator-Centric, Single-Snapshot Cohort:** Videos come from `264` tracked F&B channels (`2023-11-25` to `2025-03-19`) with single-capture engagement (March–April 2025), not a uniform random population sample or current real-time trend feed.

## 5. Source Terms, Privacy & Redistribution Boundary (`G1` Policy)
- **Upstream Reuse/Redistribution Terms Unresolved:** Historical records originate from pinned coursework/research archives (`f142e5656a220f94f8024de168b0832754b3bd9e` / owner archive) containing public creator handles and platform metadata without an established public redistribution license.
- **Public Corpus Redistribution BLOCKED:** Neither raw upstream files nor derived Gold Parquet / index snapshots may be published as an open public dataset or bundled into unauthenticated public redistribution until source rights and privacy terms are formally cleared.
- **Permitted Scope:** Local CPU evaluation, reproducible team development in the private repository, and controlled demonstration within [AGENTS.md](../../AGENTS.md) (`USD 0` paid spend) remain permitted.
