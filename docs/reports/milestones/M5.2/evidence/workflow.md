# M5.2 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-20 (Asia/Ho_Chi_Minh)
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

## Phase 3 — Subagent-Driven Development Execution (Tasks 1–2, Paused per Owner Instruction)

1. **Skills read & invoked:** `subagent-driven-development`, `finishing-a-development-branch`, `verification-before-completion`.
2. **Task 1 (`4484a3bc..4103e100`):** Implementer subagent (`4583d2d9`) executed TDD `RED` (`ImportError: cannot import name 'ASPECT_NAMES'`) -> `GREEN` (`14/14` contract tests, `198/198` repo tests, Linux & `win32` `mypy` clean, `0` secret leaks) across `packages/data_contracts/multimodal.py`, `packages/data_contracts/__init__.py`, and `tests/unit/test_m5_2_aspect_spans.py`. Independent Task 1 Reviewer (`3818f8c2`) returned **`Spec ✅` & `Task quality: Approved`** (`0` Critical/Important issues).
3. **Task 2 (`4103e100..d52bcbfa`):**
   - Implementer subagent (`b1cefd00`) executed TDD `RED` (`ModuleNotFoundError: No module named 'packages.absa.spans'`) -> `GREEN` (`20/20` ABSA tests, Linux & `win32` `mypy` clean) implementing `packages/absa/spans.py`, `packages/absa/analyzer.py`, and `packages/absa/__init__.py` (`248e1898`).
   - Independent Task 2 Reviewer (`12e7d4c8`) identified 1 Critical + 3 Important edge cases (`CommentRecord.original_text` preservation for leading-whitespace viewer offsets, prepositional `với` & bare `mà` clause delimiters, negated neutral phrases, and Vietnamese F&B compounds `"quán lâu đời"` / `"ăn sạch"` / `"giá đỗ"`).
   - Fix Round 1 (`8a304cc2`, committed `5b7d6d49`) resolved all 4 findings via TDD (`RED -> GREEN`, `21/21` passed); Scoped Re-Reviewer R1 (`2fc9fb66`) verified all 4 `ADDRESSED` and caught 3 compound-mask lookaround interactions (`"Quán ăn sạch sẽ"`, `"Phục vụ lâu lắm"`, `"Giá như vậy là bình thường"`).
   - Fix Round 2 (`8a304cc2`, committed `d52bcbfa`) added fixed-width lookaround & service-wait context guards via TDD (`RED -> GREEN`, `22/22` passed); Scoped Re-Reviewer R2 (`42e57d23`) returned **`All findings addressed, no new Critical/Important breakage`**.
4. **Rulings recorded during SDD:**
   - Defaulted additive `M5.2` fields on `AbsaComparisonRecord` so pre-Task-2 callers in `tests/contract/test_data_contracts.py` remain 100% source-compatible.
   - Explicit `Model: "inherit"` passed on every `invoke_subagent` call per platform tool contract.
   - Implementer subagents executed all code/test edits and verification suites while foreground controller executed `git add`/`git commit` on untouched subagent working trees after observing background `git commit` block on a hidden UI approval dialog (`waiting_for_input`).
5. **Owner scope boundary (`2026-11-20T16:18+07:00`):** Contributor `K` instructed stopping cleanly after Task 2 (`"Dừng ở task thứ 2 đi làm xong task 2 là được rồi"`). Verified full repository suite ([pytest-tasks1-2.log](pytest-tasks1-2.log): `202 passed in 41.88s`), strict Linux & `win32` `mypy` (`101 source files`), and `python3 scripts/check_secrets.py` (`0` leaks). Tasks 3 & 4 remain ready in [plan.md](../superpowers/plan.md) for the next session.
