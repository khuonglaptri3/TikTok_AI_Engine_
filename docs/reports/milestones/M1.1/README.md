# M1.1 — Taxonomy, Lineage & Coverage Audit

- Status: IN_PROGRESS (Automated lineage/coverage audit, taxonomy bug fixes, qualified data card, and `gemini-3.1-flash-lite` `N_*` audit labels ready; awaiting `K_*` review/overlap annotation by Trần Đình Khương)
- Execution date: 2026-11-18 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M1.1`)
- Repository version: `feat/m1.1-taxonomy-audit` (branched from `main` at `c3348e93`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Completed the automated per-field lineage, coverage, safe-ratio, and disambiguation audit over `data/corpus/20261117_recovered_v1/` (`70,996` videos across `49` columns and `264` creators across `15` columns), fixed four verified taxonomy/location bugs via TDD (`67/67` pytest tests and `mypy` over `76` source files passing), updated the qualified corpus data card, and populated `N_*` columns across all `120` stratified sample records using `gemini-3.1-flash-lite` (`<= 15 RPM`) per the contributor's explicit override. Task status remains `IN_PROGRESS` pending independent `K_*` overlap annotation and review by Trần Đình Khương (`K`), with `N_*` explicitly documented as LLM-generated rather than human ground truth.

## Work performed

- **Per-field lineage & coverage (`20261117_recovered_v1`):** Inventoried source lineage, non-null/non-empty coverage, and `unknown`/`unspecified` rates for all `49` `fact_videos` columns and `15` `dim_creators` columns via [run_m1_1_audit.py](evidence/run_m1_1_audit.py):
  - `location_source`: `poi_gps` `13,794` (`19.43%`), `llm_inferred` `2,208` (`3.11%`), `district_resolved` `1,012` (`1.43%`), `unknown` `53,982` (`76.04%`).
  - `city_norm` non-null: `17,014` (`23.96%`); `district_norm` non-null: `4,670` (`6.58%`); `region` non-`unknown`: `15,931` (`22.44%`).
  - `has_transcript = True`: `21,748` (`30.63%`); `poi_name` non-null: `23,448` (`33.03%`); `is_ad`: `4,779` (`6.73%`); `is_ec_video`: `5,798` (`8.17%`).
  - Safe ratios verified (`0` NaNs in `engagement_rate`, `viral_multiplier`, `word_per_second`; `duration_sec == 0` on `5,646` rows safely yields `wps == 0.0`; `play_count == 0` on `1` row safely yields `er == 0.0`; `12` rows have `wps > 10.0` due to short metadata durations).
- **Verified baseline bugs fixed in `packages/taxonomy/` (effective on next `M1.2` snapshot build):**
  - [location_poi.py](../../../../packages/taxonomy/location_poi.py): Fixed `quận 1` matching `quận 10..12` via longest-first word-boundary patterns, added optional `poi_name` fallback (`9,212` `poi_name != null` rows in `20261117_recovered_v1` had `city_norm = null`), added English district/city aliases and missing `CITY_TO_REGION` entries (`1,083` rows in `20261117_recovered_v1` had `city_norm != null` & `region = unknown`), and wired `poi_name` in [builder.py](../../../../pipelines/build_gold_corpus/builder.py) and [converter.py](../../../../pipelines/ingest_incremental_to_gold/converter.py).
  - [food_hierarchy.py](../../../../packages/taxonomy/food_hierarchy.py): Switched dish and category matching to word-boundary regexes (fixing `3,811 / 5,391 = 70.69%` false `"ốc"` substring hits from words like `"Trung Quốc"` / `"tốc độ"` in `20261117_recovered_v1`).
  - [rule_extractor.py](../../../../packages/taxonomy/rule_extractor.py): Removed forced `"an_vat_xe_chieu"` fallback (`59,765 / 70,996 = 84.18%` in `20261117_recovered_v1`) so unknown occasions return `[]`, and handled case-insensitive `"null"`/`"NONE"` in `extract_script_anatomy`.
- **Stratified sample & qualified documentation:** Generated `120`-record stratified sample ([audit_sample_120.csv](evidence/audit_sample_120.csv)) and [annotation_guidelines.md](evidence/annotation_guidelines.md); ran bounded `<= 15 RPM` automated labeling with `gemini-3.1-flash-lite` ([prelabel_with_gemini.py](evidence/prelabel_with_gemini.py)) populating `N_*` columns directly in [audit_sample_120.csv](evidence/audit_sample_120.csv) per explicit contributor override (`120/120` rows: `N_city_correct=90/120`, `N_format_correct=103/120`, `N_category_correct=87/120`, `N_dishes_false_positive=21/120` + `5 U`, `N_price_correct=118/120`, `N_occasion_correct=33/120`, `N_anatomy_usable=28/36` transcribed + `84 NA`; `K_*` columns remain blank for `K` review); updated [tiktok_fnb_corpus_v1.md](../../../data-cards/tiktok_fnb_corpus_v1.md) with exact coverage, unknown handling, and explicit non-ground-truth / non-attendance caveats.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Workflow provenance, audit discoveries, and command receipts |
| [run_m1_1_audit.py](evidence/run_m1_1_audit.py) | Reproducible script computing coverage, anomalies, and the 120-record sample |
| [field_coverage.csv](evidence/field_coverage.csv) | Per-column source lineage and coverage across `49` video + `15` creator fields |
| [field_lineage_and_coverage.json](evidence/field_lineage_and_coverage.json) | Full distributions, safe-ratio checks, and anomaly counts |
| [audit_sample_120.csv](evidence/audit_sample_120.csv) | Stratified `120`-record sample (`N_*` populated via `gemini-3.1-flash-lite`; `K_*` blank for `K` review) |
| [prelabel_with_gemini.py](evidence/prelabel_with_gemini.py) | Bounded `<= 15 RPM` Gemini Free-Tier labeler populating `N_*` in `audit_sample_120.csv` |
| [llm_prelabels_checkpoint.jsonl](evidence/llm_prelabels_checkpoint.jsonl) | Resumable per-row JSONL checkpoint for Gemini labeling (`120` records) |
| [annotation_guidelines.md](evidence/annotation_guidelines.md) | Shared two-person coding rules for the `120`-record audit |
| [red-taxonomy-tests.log](evidence/red-taxonomy-tests.log) | TDD RED failure log before taxonomy fixes (`4 failed, 3 passed`) |
| [green-taxonomy-tests.log](evidence/green-taxonomy-tests.log) | TDD GREEN unit test log (`7 passed`) |
| [mypy.log](evidence/mypy.log) | Strict static typecheck (`76 source files`) |
| [pytest-full.log](evidence/pytest-full.log) | Full project test suite (`67 passed in 17.12s`) |
| [check-secrets.log](evidence/check-secrets.log) | Workspace secret scan (`0` leaks) |
| [ruff.log](evidence/ruff.log) | Scoped Ruff output (`packages/taxonomy` clean; pre-existing style notices in `pipelines/`) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python docs/reports/milestones/M1.1/evidence/run_m1_1_audit.py` | PASS | Full `70,996` videos & `264` creators audited; `120`-row sample exported |
| `.venv/bin/python -m pytest tests/unit/test_taxonomy_and_corpus.py -v` | PASS (`7 passed`) | Disambiguation, word-boundary dishes, neutral occasions, anatomy nulls; [green-taxonomy-tests.log](evidence/green-taxonomy-tests.log) |
| `.venv/bin/python -m mypy packages apps pipelines` | PASS (`76 source files`) | Strict type checking across all modules; [mypy.log](evidence/mypy.log) |
| `.venv/bin/python -m pytest -v` | PASS (`67 passed`) | Full contract, unit, eval, and ASGI smoke suites; [pytest-full.log](evidence/pytest-full.log) |
| `.venv/bin/python scripts/check_secrets.py` | PASS (`0` leaks) | Workspace-wide secret scan; [check-secrets.log](evidence/check-secrets.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `N_*` populated by `gemini-3.1-flash-lite` instead of manual human annotation; `K_*` pending | `N_*` values reflect LLM evaluation rather than independent human ground truth | Recorded transparently in provenance; `K` completes `K_*` overlap check and reviews at `M1.1` / `M1.G` |
| Published `20261117_recovered_v1` parquet still reflects pre-fix taxonomy rules | Existing snapshot retains `3,811` false `"ốc"` tags, `9,212` unrecovered `poi_name` cities, and `84.18%` `an_vat_xe_chieu` | Rebuilt automatically when `K` publishes the new immutable snapshot in `M1.2` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Per-field source lineage, coverage, and unknown handling | Met | [field_coverage.csv](evidence/field_coverage.csv), [field_lineage_and_coverage.json](evidence/field_lineage_and_coverage.json) |
| City/dish disambiguation, safe ratios, anatomy & bug fixes verified | Met | [test_taxonomy_and_corpus.py](../../../../tests/unit/test_taxonomy_and_corpus.py), [green-taxonomy-tests.log](evidence/green-taxonomy-tests.log) |
| Qualified data card without ground-truth/attendance claims | Met | [tiktok_fnb_corpus_v1.md](../../../data-cards/tiktok_fnb_corpus_v1.md) |
| `120`-record `N_*` audit & `30`-record `K_*` overlap review | `N_*` populated (LLM-assisted); `K_*` pending | [audit_sample_120.csv](evidence/audit_sample_120.csv), [annotation_guidelines.md](evidence/annotation_guidelines.md) |

Final task status: **IN_PROGRESS** (automated audit, taxonomy fixes, data card, and `gemini-3.1-flash-lite` `N_*` labeling complete; awaiting `K_*` overlap annotation and review before closing `M1.1`).
