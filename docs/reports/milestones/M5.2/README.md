# M5.2 — Four-Aspect Sentiment with Source Spans

- Status: IN_PROGRESS (`K` completed & SDD-reviewed Tasks 1–2 of [plan.md](superpowers/plan.md): typed `M5.2` multimodal contracts, NFC-exact 4-aspect character-offset `source_spans` engine, `absent_unknown` vs `observed neutral` separation, and `>= 3`-comment support-gated `sentiment_discrepancy` (`202 passed`, `101`-file Linux/Windows `mypy`); Tasks 3–4 API/`/demo/` threshold sensitivity wiring, video-disjoint evaluator CLI, `120`–`200`-unit `M3.3` real-pilot double-annotation, and `N` peer review remaining)
- Execution date: 2026-11-20 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M5.2`)
- Repository version: `feat/k-m5.2-aspect-spans-baseline` (branched from `main` @ `60b80147`)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer: Nguyễn Việt Nguyên (`N`, pending peer review & real-pilot double-annotation)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**Core `M5.2` contracts and the deterministic NFC-indexed 4-aspect span & support-abstention engine (Tasks 1–2 of 4) are complete and verified via Subagent-Driven Development (`202 passed`, `101`-file Linux/Windows `mypy`, `0` secret leaks); execution paused cleanly after Task 2 per contributor instruction (`IN_PROGRESS`).**

- **Typed multimodal contracts ([multimodal.py](../../../../packages/data_contracts/multimodal.py)):** Added frozen `allow_inf_nan=False` models `AspectSpanEvidence` (enforcing `0 <= start_char < end_char` and unstripped `len(span_text) == end_char - start_char`), `AspectAggregateSummary` (enforcing bidirectional invariants separating `absent_unknown` / `mean_score=None` from `observed` + `neutral` / `mean_score=0.0`), and `AspectDiscrepancyDetail` (enforcing `sentiment_discrepancy is None` on all `"abstained_*"` statuses and framing deltas strictly as an observed `sentiment discrepancy`, never proof of deception, hygiene truth, or verified diner consensus), while keeping legacy `AbsaComparisonRecord` fields and 14-column `fact_absa_reviews.parquet` 100% backward-compatible.
- **NFC-exact 4-aspect span extractor & support-gated discrepancy ([spans.py](../../../../packages/absa/spans.py), [analyzer.py](../../../../packages/absa/analyzer.py)):** Normalizes inputs to Unicode `NFC` once with 1-to-1 codepoint index preservation (`_char_preserving_lower`) and whitespace/punctuation index trimming so `nfc_text[start_char:end_char] == span_text` holds across NFD strings and unstripped `CommentRecord.original_text`. Splits contrastive and coordinated Vietnamese multi-aspect clauses (`nhưng`, `tuy nhiên`, `, mà`, `,`, `và`, `còn`), guards real Vietnamese F&B false-positive traps (`"check in"`, `"100k views"`, `"quán lâu đời"`, `"ăn sạch cả tô"` vs `"Quán ăn sạch sẽ"`, `"giá đỗ"` / `"giá như..."` vs `"Giá như vậy là bình thường"`, negated neutral `"không chấp nhận được"` / `"không ổn"`), eliminates legacy `taste` catch-all contamination on generic praise, and gates creator-vs-viewer `sentiment_discrepancy` on `min_viewer_comments = 3` **distinct comment units** (`mention_unit_count`).
- **Remaining scope for `M5.2`:** Tasks 3–4 of [plan.md](superpowers/plan.md) (`/api/v1/trust/audit-video` `utterances` + `(polarity_tau, min_viewer_comments)` sensitivity grid, `/demo/` span-citation & support table formatting, `packages/absa/evaluation.py`, and `pipelines/audit_m5_2_absa/`), followed by `120`–`200`-unit double-annotation across `>= 10` real `M3.3` pilot videos and `N`'s peer review.

## Work performed

- **Task 1 — Typed `M5.2` contracts & validator invariants ([multimodal.py](../../../../packages/data_contracts/multimodal.py), [__init__.py](../../../../packages/data_contracts/__init__.py)):** Implemented and re-exported `ASPECT_NAMES`, `AspectSpanEvidence`, `AspectAggregateSummary`, `AspectDiscrepancyDetail`, additive `AbsaComparisonRecord` fields, and `TrustAuditRequest.utterances` (`4103e100`; passed independent Task 1 spec & code-quality review).
- **Task 2 — Exact-offset 4-aspect span engine & support-gated discrepancy ([spans.py](../../../../packages/absa/spans.py), [analyzer.py](../../../../packages/absa/analyzer.py), [test_m5_2_aspect_spans.py](../../../../tests/unit/test_m5_2_aspect_spans.py)):** Implemented `TextUnitInput`, `extract_unit_aspect_spans`, `summarize_units_aspects`, and `M5.2` aggregation inside `analyze_koc_vs_viewer_absa` (`248e1898`), followed by two scoped TDD review/fix rounds (`5b7d6d49`, `d52bcbfa`) fixing `CommentRecord.original_text` leading-whitespace alignment, prepositional `với` / bare `mà` clause boundaries, negated neutral acceptability phrases, and lookaround guards for `"Quán ăn sạch sẽ"`, `"Phục vụ lâu lắm"`, and `"Giá như vậy là bình thường"`.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Superpowers `brainstorming`, `writing-plans`, and `subagent-driven-development` provenance, review loops, and rulings |
| [pytest-tasks1-2.log](evidence/pytest-tasks1-2.log) | Full `202`-test workspace `pytest` verification log after Task 2 completion |
| [spans.py](../../../../packages/absa/spans.py), [analyzer.py](../../../../packages/absa/analyzer.py) | Deterministic NFC-indexed 4-aspect span extractor, neutral/unknown separator, and `>= 3`-comment support-gated discrepancy engine |
| [multimodal.py](../../../../packages/data_contracts/multimodal.py) | Frozen Pydantic v2 contracts for `AspectSpanEvidence`, `AspectAggregateSummary`, and `AspectDiscrepancyDetail` |
| [test_m5_2_aspect_spans.py](../../../../tests/unit/test_m5_2_aspect_spans.py) | `8` TDD unit/contract/regression tests covering invariants, NFD exact slices, abstention, and Vietnamese linguistic edge cases |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pytest tests/unit/test_m5_2_aspect_spans.py tests/unit/test_m4_2_disclosure.py tests/unit/test_incremental_absa_seeding.py -v` | PASS (`22 passed in 11.57s`) | `8` `M5.2` span/contract/regression tests + `11` `M4.2` + `3` `M3.1` Dual-Sink tests |
| `python3 -m pytest -v` | PASS (`202 passed in 41.88s`) | Full repository suite; [pytest-tasks1-2.log](evidence/pytest-tasks1-2.log) |
| `python3 -m mypy packages apps pipelines` (+ `--platform win32`) | PASS (`101 source files` each) | Strict Linux & Windows static type checks |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Full workspace secret hygiene |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Tasks 3 & 4 of [plan.md](superpowers/plan.md) deferred per contributor instruction | `/api/v1/trust/audit-video` `utterances` forwarding, `3x3` threshold sensitivity grid, `/demo/` span-citation table, and `packages/absa/evaluation.py` + `pipelines/audit_m5_2_absa/` CLI not yet wired | Resume [plan.md](superpowers/plan.md) at **Task 3** (`M5.2`, owner `K`) |
| Real pilot text units (`120`–`200` across `>= 10` videos) awaiting `M3.3` live capture | Held-out aspect detection macro-F1 (`>= 0.65`), observed sentiment macro-F1 (`>= 0.60`), audited span validity (`>= 95%`), and `K`+`N` double-annotation cannot be finalized until `M3.3` runs | Complete `M3.3` capture, run `M5.2` pool sampler, double-annotate (`K` & `N`), and complete `N` peer review before `M5.G` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Preserve aspect presence/unknown separately from observed neutral, unit IDs, character offsets, and support counts for Taste, Price, Hygiene, Service | Met in core contracts & ABSA engine (Tasks 1–2) | [multimodal.py](../../../../packages/data_contracts/multimodal.py), [spans.py](../../../../packages/absa/spans.py), [test_m5_2_aspect_spans.py](../../../../tests/unit/test_m5_2_aspect_spans.py) |
| Compare creator speech and comments only on supported overlapping aspects (`>= 3` comments); qualify as `sentiment discrepancy` | Met in `analyze_koc_vs_viewer_absa` (API/`/demo/` table rendering scheduled in Task 3) | [analyzer.py](../../../../packages/absa/analyzer.py) |
| Publish before/after-filter gaps and threshold sensitivity; video-disjoint evaluator (`F1 >= 0.65` / `0.60`, span validity `>= 95%`) | Pending (scheduled in Tasks 3–4 of [plan.md](superpowers/plan.md)) | [plan.md](superpowers/plan.md) |
| Double-annotate `120`–`200` real pilot units across `>= 10` videos & `N` peer review | Pending (`M3.3` real capture prerequisite) | `M3.3` -> `M5.2` -> `M5.G` |

Final task status: **IN_PROGRESS** (`M5.G` gate remains **`NOT_RUN`**; Tasks 1–2 verified and ready for Task 3–4 continuation).
