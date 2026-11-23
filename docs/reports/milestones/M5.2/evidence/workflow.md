# M5.2 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-20 to 2026-11-23 (Asia/Ho_Chi_Minh)
- **Task ID:** `M5.2` (Four-aspect sentiment with source spans; existing lexicon baseline upgrade)
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`, pending peer review & real-pilot double-annotation)
- **Branch:** `feat/k-m5.2-aspect-spans-baseline` (branched from `main` @ `60b80147`)
- **Spec & Plan:** [spec.md](../superpowers/spec.md), [plan.md](../superpowers/plan.md)

## Phase 1 — Superpowers Brainstorming & Written Specification (`2026-11-20`)

1. **Skills read & invoked:** `using-superpowers` (+ `references/antigravity-tools.md`) and `brainstorming` (`Architectural` path selected because `M5.2` extends shared multimodal contracts in `packages/data_contracts/multimodal.py`, refactors `packages/absa/`, updates `/api/v1/trust/audit-video` & `/demo/`, and introduces `packages/absa/evaluation.py` + `pipelines/audit_m5_2_absa/`).
2. **Codebase exploration:** Audited `packages/absa/analyzer.py`, `packages/data_contracts/multimodal.py`, `apps/api/app/routers/trust.py`, `apps/demo/presentation.py`, `packages/seeding/evaluation.py`, `pipelines/ingest_incremental_to_gold/converter.py`, and `tests/unit/test_incremental_absa_seeding.py`.
3. **Conversational design gate (`HARD-GATE` 1):** Presented shared understanding, 3 candidate CPU approaches (recommending Deterministic Clause-Window Span Extraction + Support-Gated Overlapping Discrepancy), and 4-section architecture in chat; approved by contributor `K` (`"Ok"` at `2026-11-20T11:43+07:00`).
4. **Written specification & self-review (`HARD-GATE` 2):** Authored [spec.md](../superpowers/spec.md) on branch `feat/k-m5.2-aspect-spans-baseline` (`e1050327`), verified zero placeholders, internal contract consistency, relative links, and workspace secret hygiene (`0` leaks); reviewed and approved by contributor `K` (`"ok"` at `2026-11-20T11:49+07:00`).

## Phase 2 — Superpowers Implementation Plan (`2026-11-20`)

1. **Skill read & invoked:** `writing-plans`.
2. **Plan authoring & self-review (`HARD-GATE` 3):** Authored 4-task TDD implementation plan in [plan.md](../superpowers/plan.md) (`4484a3bc`) with explicit `Global Constraints`, `Review Focus` (5 edge cases pinned to tests), exact interfaces, zero placeholders, portable `python3` commands, and zero machine-specific paths; contributor `K` selected **`Subagent-driven` (`2`)** at `2026-11-20T13:36+07:00`.

## Phase 3 — Subagent-Driven Development Execution (Tasks 1–2, `2026-11-20`)

1. **Skills read & invoked:** `subagent-driven-development`, `finishing-a-development-branch`, `verification-before-completion`.
2. **Task 1 (`4484a3bc..4103e100`):** Implementer subagent (`4583d2d9`) executed TDD `RED` (`ImportError: cannot import name 'ASPECT_NAMES'`) -> `GREEN` (`14/14` contract tests, `198/198` repo tests, Linux & `win32` `mypy` clean, `0` secret leaks) across `packages/data_contracts/multimodal.py`, `packages/data_contracts/__init__.py`, and `tests/unit/test_m5_2_aspect_spans.py`. Independent Task 1 Reviewer (`3818f8c2`) returned **`Spec ✅` & `Task quality: Approved`** (`0` Critical/Important issues).
3. **Task 2 (`4103e100..d52bcbfa`):**
   - Implementer subagent (`b1cefd00`) executed TDD `RED` (`ModuleNotFoundError: No module named 'packages.absa.spans'`) -> `GREEN` (`20/20` ABSA tests, Linux & `win32` `mypy` clean) implementing `packages/absa/spans.py`, `packages/absa/analyzer.py`, and `packages/absa/__init__.py` (`248e1898`).
   - Independent Task 2 Reviewer (`12e7d4c8`) identified 1 Critical + 3 Important edge cases (`CommentRecord.original_text` preservation for leading-whitespace viewer offsets, prepositional `với` & bare `mà` clause delimiters, negated neutral phrases, and Vietnamese F&B compounds `"quán lâu đời"` / `"ăn sạch"` / `"giá đỗ"`).
   - Fix Round 1 (`8a304cc2`, committed `5b7d6d49`) resolved all 4 findings via TDD (`RED -> GREEN`, `21/21` passed); Scoped Re-Reviewer R1 (`2fc9fb66`) verified all 4 `ADDRESSED` and caught 3 compound-mask lookaround interactions (`"Quán ăn sạch sẽ"`, `"Phục vụ lâu lắm"`, `"Giá như vậy là bình thường"`).
   - Fix Round 2 (`8a304cc2`, committed `d52bcbfa`) added fixed-width lookaround & service-wait context guards via TDD (`RED -> GREEN`, `22/22` passed); Scoped Re-Reviewer R2 (`42e57d23`) returned **`All findings addressed, no new Critical/Important breakage`**.
4. **Interim checkpoint (`7c28a9a2`):** Recorded [pytest-tasks1-2.log](pytest-tasks1-2.log) (`202 passed in 41.88s`), strict Linux & `win32` `mypy` (`101 source files`), and `python3 scripts/check_secrets.py` (`0` leaks) when pausing after Task 2 per contributor `K`'s instruction.

## Phase 4 — Subagent-Driven Continuation (Tasks 3–4, `2026-11-23`)

1. **Task 3 (`7c28a9a2..7cf7bc0e`):** Wired `TrustAuditRequest.utterances` into `/api/v1/trust/audit-video` and `compute_comment_filter_sensitivity`, added per-aspect before/after `M5.1` filter shifts plus the `3x3` `(polarity_tau in {0.05, 0.15, 0.25} x min_viewer_comments in {1, 3, 5})` sensitivity grid, and updated `apps/demo/presentation.py` (`format_trust_audit_markdown`) to render `absent_unknown` vs `observed neutral`, `n=<mention_unit_count>`, abstention statuses, and `[unit_id @ start_char:end_char]` `source_spans` citations (including empty-overlap abstention and legacy dict fallback coverage).
2. **Task 4 (`packages/absa/evaluation.py`, `pipelines/audit_m5_2_absa/`, [annotation_guidelines.md](annotation_guidelines.md), [m5_2_fixture_dry_run_v1.json](../../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json)):**
   - Executed TDD `RED` (`ModuleNotFoundError: No module named 'packages.absa.evaluation'`) -> `GREEN` (`11/11` `M5.2` tests) implementing `VALID_ASPECT_STATES`, `predict_unit_aspects`, `split_units_by_video`, `audit_source_span_validity`, `compute_m5_2_annotator_agreement`, `evaluate_m5_2_aspect_sentiment` (3-class gold-observed sentiment counting `pred == "absent_unknown"` as missed recall, 300-resample video-cluster bootstrap 95% CIs, and fail-closed `m5_2_pilot_gate_eligible`), and `build_m5_2_annotation_pool` (`1 <= max_units <= 200`, collision-free `::utt::` / `::cmt::` / `::cap` IDs, unstripped `original_text` preference, and blinded `include_predictions=False` default).
   - Implemented `pipelines.audit_m5_2_absa.run_baseline_checks` (`--mode fixture_dry_run` and `--mode real_pool`, both fail-closed via `FileExistsError`) and generated [m5_2_fixture_dry_run_v1.json](../../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json) after finalizing all Python source files so `code_files_sha256` matches exact on-disk source bytes (`held_out_aspect_f1 = 1.0000`, `held_out_sentiment_f1 = 0.9267`, `span_validity = 1.0000`, `m5_2_pilot_gate_eligible = false`).
   - Authored English [annotation_guidelines.md](annotation_guidelines.md) for `K` & `N` double-annotation on `120`–`200` `M3.3` pilot units across `>= 10` videos (`d83f52b7`).
   - **Task 4 Review (`45fc5960`) & Fix Round 1:** Reviewer flagged 1 Critical (`build_m5_2_annotation_pool` sampling historical `fact_videos.parquet` rows instead of restricting to multimodal `M3.3` `voice_df` / `comments_df` `video_id`s) and 1 Important (`audit_source_span_validity` returning `meets_95pct_gate=True` on `spans=[]` / skipping `dict` aspect & untrimmed whitespace checks, plus `evaluate_m5_2_aspect_sentiment` not verifying `>= 1` valid span per predicted observed `(unit_id, aspect)` pair). Resolved both via TDD (`RED` `AssertionError: assert 180 == 50` -> `GREEN` `12/12` `M5.2` tests) and regenerated [m5_2_fixture_dry_run_v1.json](../../../../../artifacts/benchmarks/m5_2_fixture_dry_run_v1.json) so `code_files_sha256` matches 100% on disk.
3. **Full verification before completion (`2026-11-23`):**
   - `python3 -m pytest -v` -> `206 passed in 29.80s` ([pytest-full-m5_2.log](pytest-full-m5_2.log)).
   - `python3 -m mypy packages apps pipelines tests/unit/test_m5_2_aspect_spans.py` -> `Success: no issues found in 105 source files` (sequential run after confirming concurrent Linux + `win32` invocations contend on shared `.mypy_cache`).
   - `python3 -m mypy --platform win32 packages apps pipelines` -> `Success: no issues found in 104 source files`.
   - `python3 scripts/check_secrets.py` -> `0` secret leaks.
   - Verified `M5.2/` top-level directory layout (`README.md`, `evidence/`, `superpowers/{spec.md, plan.md}`), zero machine-specific paths, and zero broken relative links.
