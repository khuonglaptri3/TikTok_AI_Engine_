# M1.1 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-18 (Asia/Ho_Chi_Minh)
- **Task ID:** `M1.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`, pending)

## Process & Skill Check
- Standalone `superpowers` skill files (`using-superpowers`, `brainstorming`, `writing-plans`, `test-driven-development`, `verification-before-completion`) remain uninstalled in local skill directories; followed the `AGENTS.md` Section 7 spec/plan/TDD/verification workflow directly.
- Created feature branch `feat/m1.1-taxonomy-audit` cleanly from `main` (`c3348e93`) before editing.
- Authored `superpowers/spec.md` and `superpowers/plan.md` prior to code modifications.

## Key Audit Findings & Decisions
1. **Do Not Mutate Published Snapshot `20261117_recovered_v1`:** Audited the existing `70,996`-row `fact_videos.parquet` and `264`-row `dim_creators.parquet` read-only. Taxonomy/resolver fixes take effect on the next immutable `M1.2` snapshot build and incremental ingestion.
2. **Discovered Bugs Fixed via TDD:**
   - **District substring collision:** Unordered `set` lookup allowed `"quận 1"` to match `"quận 10"`, `"quận 11"`, and `"quận 12"`. Fixed with longest-first word-boundary regex (`_DISTRICT_PATTERNS`).
   - **POI coverage gap (`9,212` POI-tagged rows with `city_norm = null`; `1,083` rows with `city_norm != null` & `region = unknown`):** Added optional `poi_name` fallback (`poi_gps` tier), English district/city aliases (`Ho Chi Minh City`, `Hanoi`, `District 1..12`, `Hue`, `Ha Long`, `Phu Quoc`, `Quy Nhon`), and district-in-`llm_city` recovery (`nhà bè`, `long biên`).
   - **Dish substring false positives (`3,811 / 5,391 = 70.69%` false `"ốc"` matches):** Switched `extract_dishes_from_text` and `map_food_category` to word-boundary regexes (`(?<!\w)...(?!\w)`), eliminating false matches from `"Trung Quốc"`, `"tốc độ"`, `"gốc"`, `"sốc"`.
   - **Forced `an_vat_xe_chieu` occasion bias (`59,765 / 70,996 = 84.18%`):** Removed forced fallback in `extract_occasions` so videos without occasion signals return `[]` (`unknown`).
3. **Annotation Provenance (`N_*` Populated via `gemini-3.1-flash-lite`):** Initially exported blank `audit_sample_120.csv` (`30` `shared_K_N` + `90` `N_primary`) and a separate `llm_prelabels_120.csv`. Per the contributor's explicit instruction to allow automated LLM labeling directly into `N_*`, `llm_prelabels_120.csv` was removed and `N_*` columns in `audit_sample_120.csv` were populated from `llm_prelabels_checkpoint.jsonl` (`gemini-3.1-flash-lite`, `<= 15 RPM`). `K_*` columns remain blank for independent review; this report explicitly records `N_*` as LLM-generated rather than human-annotated ground truth.

## Commands & Verification Receipts
- `.venv/bin/python docs/reports/milestones/M1.1/evidence/run_m1_1_audit.py` -> generated `field_coverage.csv`, `field_lineage_and_coverage.json`, `audit_sample_120.csv`
- `.venv/bin/python docs/reports/milestones/M1.1/evidence/prelabel_with_gemini.py --limit 120` -> `12/12` batches (`120/120` rows) labeled with `gemini-3.1-flash-lite` (`<= 15 RPM`) directly into `N_*` columns of `audit_sample_120.csv` (`K_*` preserved blank)
- `.venv/bin/python -m pytest tests/unit/test_taxonomy_and_corpus.py -v` (RED) -> `EXIT=1`, `4 failed, 3 passed` ([red-taxonomy-tests.log](red-taxonomy-tests.log))
- `.venv/bin/python -m pytest tests/unit/test_taxonomy_and_corpus.py -v` (GREEN) -> `EXIT=0`, `7 passed in 0.67s` ([green-taxonomy-tests.log](green-taxonomy-tests.log))
- `.venv/bin/python scripts/check_secrets.py` -> `EXIT=0`, `PASS: Zero secret leaks detected across workspace.` ([check-secrets.log](check-secrets.log))
- `.venv/bin/python -m mypy packages apps pipelines` -> `EXIT=0`, `Success: no issues found in 76 source files` ([mypy.log](mypy.log))
- `.venv/bin/python -m pytest -v` -> `EXIT=0`, `67 passed in 17.12s` ([pytest-full.log](pytest-full.log))

## Peer Review & Blinded 30-Row `K_*` Audit Addendum (`2026-11-18`, Trần Đình Khương)
- Read and applied `using-superpowers`, `receiving-code-review`, `test-driven-development`, and `verification-before-completion`.
- Extracted `sample_no = 1..30` (`shared_K_N`) with `N_*` stripped, manually coded `K_city_correct`, `K_format_correct`, `K_category_correct`, `K_dishes_false_positive`, and `K_notes` strictly from `caption` / `poi_*` / `transcript_excerpt` per [annotation_guidelines.md](annotation_guidelines.md), then computed exact raw agreement and Cohen's $\kappa$ in [khuong_m1_1_review_and_agreement.json](khuong_m1_1_review_and_agreement.json) and authored [khuong-peer-review.md](khuong-peer-review.md).
