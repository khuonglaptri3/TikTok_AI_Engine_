# M2.3 — Qualified Scripts, Structural Guardrails & Bounded Provider Bounds

- Status: IN_PROGRESS (`N`'s guardrail/provider scope + `N`'s bounded Gemini check on initial 15 drafts AND `K`'s peer-review TDD fixes, `15` briefs, and `30`-draft full-transcript `K`-side human claim audit (`108/120 = 90.00%`) complete; awaiting `N`'s independent human claim-entailment columns on the `30` drafts)
- Execution date: 2026-11-18 to 2026-11-19 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M2.3`)
- Repository version: `feat/k-m2.2-m2.3-m3.2-deliverables` (rebased onto `main` @ `f130d4b5`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Hardened `BoundedGeminiClient`, `recalculate_timeline_and_verify`, and `GroundedScriptEngine` for `M2.3`, followed by `N`'s bounded Gemini baseline check (`47/55 = 85.45%` on the initial 15 drafts) and `K`'s reciprocal peer review, three TDD bug-fix rounds (`33/33` guardrail/draft tests), `15` held-out briefs (`k01..k15`), and a `30`-draft full-transcript human claim-entailment audit over `20261118_taxonomy_fix_v1` + `bm25-v3` (`0` provider calls, `USD 0`). Across all `30` drafts (`15` `N` + `15` `K`, `120` beats), structural verification achieved `0` fabricated IDs, `30/30` (`100%`) valid source membership, `30/30` (`100%`) beat citation coverage, and `30/30` (`100%`) `±max(2s, 5%)` timeline compliance without mid-sentence truncation. `K`'s word-for-word audit of all cited full transcripts confirmed `120/120` (`100%`) verbatim substring presence in cited records and **`108/120` (`90.00%`) supported culinary claims** after strictly disqualifying `9` unmarked song-lyric/music-summary beats (`C1`) and `3` upstream location-mislabel / `"vibe Đà Lạt"` beats (`C2`), while recording `20/30` (`66.67%`) whole-draft editorial pass (`K_review_ok`). Task status remains `IN_PROGRESS` until `N` independently populates `N_total_factual_claims`, `N_supported_factual_claims`, and `N_citation_coverage_ok` across the `30` drafts.

## Work performed

- **Bounded provider call budget & timeout (`N`, [gemini.py](../../../../packages/llm/clients/gemini.py)):** Enforced `turn_calls_used < max_llm_calls_per_turn` (`2` calls/turn), passed `HttpOptions(timeout=timeout_ms)` from `llm_deadline_seconds`, redacted exception strings, and mapped `TimeoutError` / quota errors into bounded `QuotaBlockedError`.
- **No-evidence & structural guardrail separation (`N`, [verifier.py](../../../../packages/llm/guardrails/verifier.py)):** Emits an explicit warning when `valid_evidence_ids` is empty while reporting `valid_citations_ratio` (source membership) separately from `citation_coverage_ratio` (beat coverage) and preserving `grounding_verified=False`.
- **15-brief baseline & bounded Gemini check (`N`, [run_m2_3_audit.py](evidence/run_m2_3_audit.py), [audit_claims_with_gemini.py](evidence/audit_claims_with_gemini.py)):** Generated [nguyen_15_drafts_audit.csv](evidence/nguyen_15_drafts_audit.csv) and ran `gemini-3.1-flash-lite` (`<= 14 RPM`), surfacing `47/55 = 85.45%` supported claims due to truncated offline excerpts, `"Địa Phương"` fallback, and music-lyric spans ([nguyen_15_llm_claim_audit.json](evidence/nguyen_15_llm_claim_audit.json)).
- **Peer-review TDD hardening of offline synthesis & retrieval filters (`K`, [service.py](../../../../packages/script_engine/service.py), [test_offline_draft.py](../../../../tests/unit/test_offline_draft.py)):** Preserved `N`'s [nguyen_15_drafts_audit.csv](evidence/nguyen_15_drafts_audit.csv) untouched and resolved those exact failure modes plus four additional bugs via three `RED -> GREEN` rounds: (1) stopped cross-city fabrication from `c0.city_norm` / `"Địa Phương"` and stripped dish-origin city phrases (`"bún bò Huế"`, `"chuẩn vị Hà Nội"`), (2) removed `c0.dishes` topic hijacking, (3) added `_build_retrieval_filters` so explicit caller filters + geographic scope stay strict without soft-facet starvation on `20261118_taxonomy_fix_v1`, (4) replaced mid-sentence word slicing with complete-sentence combinatorial `wps` pacing across `35–55s`, and (5) filtered music summaries, prompt placeholders, and `< 3`-word trivial sign-off CTAs (`"Bye bye."`, `"Haha."`).
- **30-brief offline generation & `K` full-transcript human claim audit (`K`, [run_m2_3_30_drafts_audit.py](evidence/run_m2_3_30_drafts_audit.py), [khuong-peer-review.md](evidence/khuong-peer-review.md)):** Authored [khuong_15_queries.jsonl](evidence/khuong_15_queries.jsonl), generated [combined_30_drafts_audit.csv](evidence/combined_30_drafts_audit.csv) (`0` provider calls), audited 100% of cited full source transcripts across `120` beats, adjudicated hard-case clusters `C1–C5` with `K` ([khuong_c1_c5_adjudication.json](evidence/khuong_c1_c5_adjudication.json)), and populated `K_*` columns while leaving `N_*` columns blank for `N`.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | `N` and `K` workflow provenance, TDD cycles, and verification ledger |
| [nguyen_15_queries.jsonl](evidence/nguyen_15_queries.jsonl), [nguyen_15_drafts_audit.csv](evidence/nguyen_15_drafts_audit.csv) | `N`'s `15` held-out briefs and preserved baseline audit CSV |
| [audit_claims_with_gemini.py](evidence/audit_claims_with_gemini.py), [nguyen_15_llm_claim_audit.json](evidence/nguyen_15_llm_claim_audit.json), [llm_claim_audit_checkpoint.jsonl](evidence/llm_claim_audit_checkpoint.jsonl) | `N`'s bounded `<= 14 RPM` Gemini claim-audit baseline (`47/55 = 85.45%`) |
| [khuong_15_queries.jsonl](evidence/khuong_15_queries.jsonl) | `15` disjoint held-out Vietnamese F&B briefs authored by `K` (`k01..k15`) |
| [run_m2_3_30_drafts_audit.py](evidence/run_m2_3_30_drafts_audit.py) | Reproducible `0`-provider-call 30-draft runner over `20261118_taxonomy_fix_v1` + `bm25-v3` |
| [khuong_15_drafts_audit.csv](evidence/khuong_15_drafts_audit.csv), [combined_30_drafts_audit.csv](evidence/combined_30_drafts_audit.csv) | `K`'s 15 drafts and combined `30` drafts (`K_*` populated, `N_*` blank) |
| [combined_30_drafts_detailed.jsonl](evidence/combined_30_drafts_detailed.jsonl), [khuong_30_drafts_claim_audit.jsonl](evidence/khuong_30_drafts_claim_audit.jsonl) | Full beat dialogues, untruncated cited source records, and per-beat `K` claim-audit ledger |
| [khuong_c1_c5_adjudication.json](evidence/khuong_c1_c5_adjudication.json), [combined_30_summary.json](evidence/combined_30_summary.json) | `K`'s adjudicated `C1–C5` rules and aggregate 30-draft summary (`108/120 = 90.00%`) |
| [khuong-peer-review.md](evidence/khuong-peer-review.md) | `K`'s peer-review findings, TDD bug fixes, and semantic limitation report |
| [green-khuong-review-fixes-round3.log](evidence/green-khuong-review-fixes-round3.log), [pytest-full-k-review-linux.log](evidence/pytest-full-k-review-linux.log), [mypy-k-review-scoped.log](evidence/mypy-k-review-scoped.log), [check-secrets-k-review.log](evidence/check-secrets-k-review.log) | TDD GREEN (`33 passed`), full pytest, scoped `mypy` (`0` issues), and secret scan logs |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pytest tests/unit/test_offline_draft.py tests/unit/test_script_guardrails.py -v` | PASS (`33 passed`) | Guardrails + 3 `K` peer-review TDD rounds; [green-khuong-review-fixes-round3.log](evidence/green-khuong-review-fixes-round3.log) |
| `python3 docs/reports/milestones/M2.3/evidence/run_m2_3_30_drafts_audit.py` | PASS (`30/30` structural/timing; `108/120 = 90.0%` `K` claim support) | `30` briefs (`offline_grounded`, `0` provider calls) over `20261118_taxonomy_fix_v1` + `bm25-v3`; [combined_30_summary.json](evidence/combined_30_summary.json) |
| `python3 -m mypy packages/llm tests/unit/test_offline_draft.py tests/unit/test_script_guardrails.py --follow-imports=silent && python3 -m mypy packages/script_engine --follow-imports=silent` | PASS (`0` issues) | Edited `M2.3` modules (`packages/retrieval/dense/encoder.py:42` has pre-existing `anaconda3` numpy stub `Any` note when following imports); [mypy-k-review-scoped.log](evidence/mypy-k-review-scoped.log) |
| `python3 -m pytest -v` | PASS | Full workspace test suite verified on rebased branch |
| `python3 scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret hygiene scan; [check-secrets-k-review.log](evidence/check-secrets-k-review.log) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `N`'s independent human claim-entailment columns (`N_*`) on `combined_30_drafts_audit.csv` are pending | Two-person human claim audit is required before `M2.3` can transition to `COMPLETE` | `N` audits `combined_30_drafts_audit.csv` and reconciles any diffs with `K` before `M2.G` |
| Unmarked song lyrics (`C1`, `9/120` beats) and upstream `city_norm` mislabel (`7387712842968943880` Thủ Đức labeled Hanoi in `n11` B3) exist in historical corpus | Lowers whole-draft editorial fitness (`K_review_ok = 20/30`) despite `100%` structural pass and `90.0%` beat-level culinary claim support | Recorded transparently in [khuong-peer-review.md](evidence/khuong-peer-review.md); carry forward as known historical-corpus limitation into `M2.G` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Regressions for empty/foreign-ID/no-evidence/timing & `max(2s, 5%)` | Met | [test_script_guardrails.py](../../../../tests/unit/test_script_guardrails.py), [test_offline_draft.py](../../../../tests/unit/test_offline_draft.py) (`33 passed`) |
| Offline `0` calls; provider missing-key/quota/timeout & `<= 2` calls/turn | Met | [gemini.py](../../../../packages/llm/clients/gemini.py), [service.py](../../../../packages/script_engine/service.py) |
| `30`-draft human claim audit (`15` `N` + `15` `K`, `0` fabricated IDs, `>= 90%` supported & cited) & `K` peer review | Partial (`K` peer review + `15` `K` briefs + `K` 30-draft human audit `108/120 = 90.0%` complete; awaiting `N` `N_*` human audit columns) | [combined_30_drafts_audit.csv](evidence/combined_30_drafts_audit.csv), [khuong-peer-review.md](evidence/khuong-peer-review.md) |

Final task status: **IN_PROGRESS** (`K`'s peer-review deliverables and `K`-side 30-draft full-transcript human audit are complete; awaiting `N`'s `N_*` human claim-audit columns to close `M2.3` for Gate `G2` / `M2.G`).
