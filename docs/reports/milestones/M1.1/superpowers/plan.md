# M1.1 — Execution & Verification Plan

- **Date:** 2026-11-18
- **Task ID:** `M1.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)

## Execution Steps
1. **Reproducible Lineage & Stratified Sample Script (`evidence/run_m1_1_audit.py`):**
   - Compute exact non-null/non-empty/unknown counts, distributions, safe-ratio checks (`duration_sec == 0`, `play_count == 0`, `wps > 10` outliers), and dish/location anomaly counts over `data/corpus/20261117_recovered_v1/`.
   - Draw a deterministic stratified `120`-record sample (`seed=20261118`) across `city_bucket × food_category × has_transcript`, assigning `30` records to `shared_K_N` and `90` records to `N_primary`, and write `evidence/audit_sample_120.csv` + blank annotation columns for human labeling.
2. **TDD RED (Failing Taxonomy Tests First):**
   - Add unit tests to `tests/unit/test_taxonomy_and_corpus.py` for:
     - `quận 10` / `quận 11` / `quận 12` not colliding with `quận 1`;
     - `poi_name` & English city/district aliases (`Ho Chi Minh City`, `Hanoi`, `District 5`, `Hue`, `Ha Long`, `Phu Quoc`) and district-in-`llm_city` (`nhà bè`, `long biên`);
     - word-boundary dish matching (`"Trung Quốc tốc độ"` must not match `"ốc"`, while `"ốc hương"` and `"ăn ốc"` match `"ốc"`; `"tiramisu"` matches; `"ăn mì"` matches `"Món nước & Sợi"`);
     - `extract_occasions` returning `[]` when no occasion keyword matches (no forced `an_vat_xe_chieu` bias) and `extract_script_anatomy` ignoring `"null"`/`"NONE"`.
   - Run `pytest tests/unit/test_taxonomy_and_corpus.py -v` and capture RED output in `evidence/red-taxonomy-tests.log`.
3. **Implement Fixes (`packages/taxonomy/` & `pipelines/build_gold_corpus/builder.py`):**
   - Update `location_poi.py` (longest-first word-boundary district matching, English/city aliases, `poi_name` fallback under `poi_gps`, complete `CITY_TO_REGION`), `food_hierarchy.py` (word-boundary dish/category matching), and `rule_extractor.py` (neutral `[]` default for unknown occasions, case-insensitive null handling in `extract_script_anatomy`).
   - Pass `poi_name=poi_name` into `resolve_location(...)` in `pipelines/build_gold_corpus/builder.py` and `pipelines/ingest_incremental_to_gold/converter.py` (keeping `poi_name` optional with default `None` for compatibility).
4. **Update Qualified Data Card (`docs/data-cards/tiktok_fnb_corpus_v1.md`):**
   - Align snapshot ID (`20261117_recovered_v1`), document per-field lineage/coverage, unknown handling, discovered baseline taxonomy caveats, and explicit non-ground-truth / non-attendance disclaimers.
5. **TDD GREEN & Full Verification:**
   - Run `pytest tests/unit/test_taxonomy_and_corpus.py -v` -> save `evidence/green-taxonomy-tests.log`.
   - Run `ruff`, `scripts/check_secrets.py`, `mypy`, and full `pytest -v`.
   - Author `docs/reports/milestones/M1.1/README.md`, `evidence/workflow.md`, `evidence/annotation_guidelines.md`, and update `docs/reports/milestones/README.md`.
