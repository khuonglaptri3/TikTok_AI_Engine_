# M1.1 — Taxonomy, Lineage & Coverage Audit

- Status: COMPLETE (`N` lineage audit, taxonomy fixes, and `N_*` review confirmed by project owner; `K` blinded 30-record human `K_*` annotation & code review complete)
- Execution date: 2026-11-18 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M1.1`)
- Repository version: `main` (merged `origin/feat/m1.1-taxonomy-audit` @ `f3dd0a84` + `K_*` overlap review)
- Primary owner: Nguyễn Việt Nguyên (`N`) · Peer reviewer: Trần Đình Khương (`K`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Completed the automated per-field lineage, coverage, safe-ratio, and disambiguation audit over `data/corpus/20261117_recovered_v1/` (`70,996` videos across `49` columns and `264` creators across `15` columns), fixed four verified taxonomy/location bugs via TDD (`packages/taxonomy/`), updated the qualified corpus data card ([tiktok_fnb_corpus_v1.md](../../../data-cards/tiktok_fnb_corpus_v1.md)), and completed **Trần Đình Khương (`K`)'s blinded manual human annotation on all `30` `shared_K_N` overlap records** ([audit_sample_120.csv](evidence/audit_sample_120.csv), [khuong-peer-review.md](evidence/khuong-peer-review.md)).

Comparing blinded human `K_*` (`n=30`) against `N_*` (`gemini-3.1-flash-lite` prelabels reviewed by `N`) yielded high agreement on `city_correct` (`96.67%`, $\kappa = 0.9231$; `K` human error rate `10/30 = 33.33%`) and `dishes_false_positive` (`90.00%`, $\kappa = 0.6667$; `K` false-positive row rate `5/30 = 16.67%`), while quantifying LLM leniency bias on `format_correct` (`70.00%`, $\kappa = 0.1318$; `K` error rate `9/30 = 30.00%` + `1 U`) and `category_correct` (`63.33%`, $\kappa = 0.2180$; `K` error rate `13/30 = 43.33%`). With `N`'s review confirmed by the project owner and `N_*` explicitly qualified as LLM-assisted rather than unassisted human ground truth, task `M1.1` is **COMPLETE** (formal gate `M1.G` / `G1` remains `NOT_RUN`), and its audited taxonomy fixes are materialized in `M1.2` (`data/corpus/20261118_taxonomy_fix_v1`).

## Work performed

- **Per-field lineage & coverage (`20261117_recovered_v1`):** Inventoried source lineage, non-null/non-empty coverage, and `unknown`/`unspecified` rates for all `49` `fact_videos` columns and `15` `dim_creators` columns via [run_m1_1_audit.py](evidence/run_m1_1_audit.py):
  - `location_source`: `poi_gps` `13,794` (`19.43%`), `llm_inferred` `2,208` (`3.11%`), `district_resolved` `1,012` (`1.43%`), `unknown` `53,982` (`76.04%`).
  - `city_norm` non-null: `17,014` (`23.96%`); `district_norm` non-null: `4,670` (`6.58%`); `region` non-`unknown`: `15,931` (`22.44%`).
  - `has_transcript = True`: `21,748` (`30.63%`); `poi_name` non-null: `23,448` (`33.03%`); `is_ad`: `4,779` (`6.73%`); `is_ec_video`: `5,798` (`8.17%`).
  - Safe ratios verified (`0` NaNs in `engagement_rate`, `viral_multiplier`, `word_per_second`; `duration_sec == 0` on `5,646` rows -> `wps == 0.0`; `play_count == 0` on `1` row -> `er == 0.0`).
- **Verified baseline bugs fixed in `packages/taxonomy/` (applied in `M1.2` snapshot `20261118_taxonomy_fix_v1`):**
  - [location_poi.py](../../../../packages/taxonomy/location_poi.py): Longest-first word-boundary district matching (`quận 1` vs `quận 10..12`), `poi_name` fallback (`9,212` unrecovered POI rows), and English/unaccented city/district aliases (`1,083` `region=unknown` rows).
  - [food_hierarchy.py](../../../../packages/taxonomy/food_hierarchy.py): Word-boundary dish/category regexes fixing `3,811 / 5,391 = 70.69%` false `"ốc"` substring hits (`"Trung Quốc"`, `"Hàn Quốc"`, `"gần dốc"`, `"Hát đốc"`).
  - [rule_extractor.py](../../../../packages/taxonomy/rule_extractor.py): Removed forced `"an_vat_xe_chieu"` fallback (`59,765 / 70,996 = 84.18%`) so unknown occasions return `[]`, and handled case-insensitive `"null"`/`"NONE"` in `extract_script_anatomy`.
- **Blinded 30-record `K_*` human audit & peer review (`2026-11-18`):** Trần Đình Khương (`K`) coded `K_city_correct`, `K_format_correct`, `K_category_correct`, `K_dishes_false_positive`, and `K_notes` on `sample_no = 1..30` blinded to `N_*`, published [khuong_m1_1_review_and_agreement.json](evidence/khuong_m1_1_review_and_agreement.json) and [khuong-peer-review.md](evidence/khuong-peer-review.md), and documented residual error modes (`"cắt sợi"` category collision, non-F&B creator sponsor vlogs, background song-lyric transcripts).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Workflow provenance, audit discoveries, and command receipts |
| [khuong-peer-review.md](evidence/khuong-peer-review.md) | Peer review & blinded 30-record human `K_*` error/agreement report by `K` |
| [khuong_m1_1_review_and_agreement.json](evidence/khuong_m1_1_review_and_agreement.json) | Machine-readable agreement, Cohen's $\kappa$, and 24 itemized disagreement cells (`K` human vs. `N` Gemini) |
| [run_m1_1_audit.py](evidence/run_m1_1_audit.py) | Reproducible script computing coverage, anomalies, and the 120-record sample |
| [field_coverage.csv](evidence/field_coverage.csv) | Per-column source lineage and coverage across `49` video + `15` creator fields |
| [field_lineage_and_coverage.json](evidence/field_lineage_and_coverage.json) | Full distributions, safe-ratio checks, and anomaly counts |
| [audit_sample_120.csv](evidence/audit_sample_120.csv) | Stratified `120`-record sample (`K_*` human-annotated on `1..30`; `N_*` populated via `gemini-3.1-flash-lite` on `1..120`) |
| [prelabel_with_gemini.py](evidence/prelabel_with_gemini.py) | Bounded `<= 15 RPM` Gemini Free-Tier labeler used for `N_*` |
| [llm_prelabels_checkpoint.jsonl](evidence/llm_prelabels_checkpoint.jsonl) | Per-row JSONL checkpoint for `N_*` Gemini prelabeling (`120` records) |
| [annotation_guidelines.md](evidence/annotation_guidelines.md) | Shared two-person coding rules for the `120`-record audit |
| [red-taxonomy-tests.log](evidence/red-taxonomy-tests.log) / [green-taxonomy-tests.log](evidence/green-taxonomy-tests.log) | TDD RED (`4 failed`) and GREEN (`7 passed`) taxonomy test logs |
| [mypy.log](evidence/mypy.log) / [pytest-full.log](evidence/pytest-full.log) / [check-secrets.log](evidence/check-secrets.log) | Typecheck, test suite, and secret scan logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python docs/reports/milestones/M1.1/evidence/run_m1_1_audit.py` | PASS | Full `70,996` videos & `264` creators audited; `120`-row sample exported |
| `.venv/bin/python -m pytest tests/unit/test_taxonomy_and_corpus.py -v` | PASS (`7 passed`) | Disambiguation, word-boundary dishes, neutral occasions, anatomy nulls; [green-taxonomy-tests.log](evidence/green-taxonomy-tests.log) |
| Blinded 30-record `K_*` human audit & $\kappa$ calculation | PASS (`30/30` coded, `24/120` diff cells logged) | [khuong_m1_1_review_and_agreement.json](evidence/khuong_m1_1_review_and_agreement.json), [khuong-peer-review.md](evidence/khuong-peer-review.md) |
| `python scripts/check_secrets.py` | PASS (`0` leaks) | Workspace-wide secret scan |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `N_*` columns in `audit_sample_120.csv` originated from `gemini-3.1-flash-lite` prelabels (`format` $\kappa=0.1318$, `category` $\kappa=0.2180$ leniency bias vs. manual `K_*`) and were accepted under owner-confirmed `N` review | `N_*` provenance remains explicitly qualified as LLM-assisted rather than independent two-human ground truth | Retained as an explicit methodological caveat for `M1.G` (`G1`) |
| Residual taxonomy edge cases (`"cắt sợi"` -> `Món nước & Sợi`, unaccented hashtags `#banhmi`/`#mienga`, non-F&B creator sponsor vlogs, song-lyric transcripts) | Measured human error rates (`30%` format, `43.3%` category on `n=30`) remain documented corpus caveats rather than silent perfection claims | Qualified in data card & `M1.G`; transcript/relevance filtering evaluated in `M2.2`/`M2.3` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Per-field source lineage, coverage, and unknown handling | Met | [field_coverage.csv](evidence/field_coverage.csv), [field_lineage_and_coverage.json](evidence/field_lineage_and_coverage.json) |
| City/dish disambiguation, safe ratios, anatomy & bug fixes verified | Met | [test_taxonomy_and_corpus.py](../../../../tests/unit/test_taxonomy_and_corpus.py), [green-taxonomy-tests.log](evidence/green-taxonomy-tests.log) |
| Qualified data card without ground-truth/attendance claims | Met | [tiktok_fnb_corpus_v1.md](../../../data-cards/tiktok_fnb_corpus_v1.md) |
| `120`-record stratified audit & `30`-record overlap agreement/errors | Met (`K_*` 30 manual rows + agreement/disagreements + owner-confirmed `N` review, with LLM-assisted `N_*` provenance recorded) | [audit_sample_120.csv](evidence/audit_sample_120.csv), [khuong_m1_1_review_and_agreement.json](evidence/khuong_m1_1_review_and_agreement.json) |

Final task status: **COMPLETE**. Formal gate `M1.G` (`G1`) remains `NOT_RUN` pending `M0.G` and dedicated gate review.
