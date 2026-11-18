# M1.1 — Specification: Taxonomy, Lineage & Coverage Audit

- **Date:** 2026-11-18
- **Task ID:** `M1.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M1.1`)

## Scope & Requirements
1. Audit per-field source (lineage), non-null/non-empty coverage, and `unknown`/`unspecified` handling across all `49` columns of `fact_videos.parquet` (`70,996` rows) and `15` columns of `dim_creators.parquet` (`264` rows) in `data/corpus/20261117_recovered_v1/`.
2. Audit and verify city/dish disambiguation (`packages/taxonomy/location_poi.py`, `food_hierarchy.py`), safe ratios (`engagement_rate`, `viral_multiplier`, `word_per_second`, zero-division guards), script anatomy (`extract_script_anatomy`), and `unknown` handling (`extract_occasions`, `extract_price_tier`).
3. Fix verified taxonomy/disambiguation bugs discovered during audit via TDD without silently mutating the already-published immutable `20261117_recovered_v1` parquet snapshot (changes apply to the next immutable `M1.2` snapshot build).
4. Generate a reproducible, deterministic **120-record stratified audit sample** across `city_norm`, `food_category`, and `has_transcript` availability (`30` overlapping records for both `K` and `N`, `90` remaining records for `N` with `K` review) and provide written annotation guidelines (`evidence/annotation_guidelines.md`) without fabricating human annotations.
5. Update `docs/data-cards/tiktok_fnb_corpus_v1.md` with qualified per-field coverage, unknown handling, and explicit disclaimers that heuristic/LLM labels are not ground truth and platform POIs do not prove physical attendance.

## Acceptance Criteria
- Automated per-field source, coverage, and anomaly report (`evidence/field_lineage_and_coverage.json` and `evidence/field_coverage.csv`) verified over `70,996` videos and `264` creators.
- TDD unit tests in `tests/unit/test_taxonomy_and_corpus.py` verify fixes for district substring collisions (`quận 1` vs `quận 10..12`), English/unaccented POI city/district aliases (`Ho Chi Minh City`, `Hanoi`, `District 1..12`), dish substring false positives (`ốc` vs `Trung Quốc` / `tốc độ`), and neutral `unknown` occasion handling (`[]` instead of forced `an_vat_xe_chieu`).
- `120`-record stratified sample (`evidence/audit_sample_120.csv`) ready for independent two-person annotation (`30` shared `K+N`, `90` `N`), with `M1.1` honestly kept `IN_PROGRESS` until human annotations and `K` review are completed.
- `scripts/check_secrets.py`, `ruff`, `mypy`, and full `pytest` pass cleanly.
