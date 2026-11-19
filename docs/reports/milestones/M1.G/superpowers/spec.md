# M1.G (G1) — Historical Gold Corpus Gate Specification

- **Task ID:** `M1.G` (Gate `G1`)
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M1.G`)
- **Date:** 2026-11-18 (Asia/Saigon)

## Scope

Assemble, verify, and publish the `G1` corpus gate package across `M1.1` (taxonomy/lineage audit & 120-record sample) and `M1.2` (immutable taxonomy-corrected Gold snapshot `20261118_taxonomy_fix_v1`), following formal owner approval of `G0 = PASS` (`M0.G = COMPLETE`).

## Acceptance Criteria (`M1.G`)

1. **Prerequisite gate & tasks:**
   - Gate `G0` (`M0.G`) is `PASS` / `COMPLETE`.
   - `M1.1` and `M1.2` reports and evidence bundles are `COMPLETE` and match [milestones/README.md](../../README.md).
2. **Immutable snapshot integrity & parent lineage:**
   - Both `data/corpus/20261117_recovered_v1` and `data/corpus/20261118_taxonomy_fix_v1` pass `load_verified_corpus` checksum, schema, and key uniqueness checks with `0` byte mutations.
   - `20261118_taxonomy_fix_v1/manifest.json` binds `parent_snapshot_id = "20261117_recovered_v1"` and `parent_manifest_sha256 = "10ed9c666707319f0a67c688e77d79ddc409e11c1f57ff075a01a3d718b714f4"`.
   - All `70,996` video rows (`49` columns) and `264` creator rows (`15` columns) maintain `0` `NaN`/`Inf` in `engagement_rate`, `viral_multiplier`, and `word_per_second`, and reproduce the audited `M1.1`→`M1.2` disambiguation deltas (`city_norm +6,464`, `district_norm +8,481`, `region +7,055`, `"ốc" -3,785`, `"an_vat_xe_chieu" -58,400`).
3. **Qualified Data Card & source rights boundary:**
   - Update [tiktok_fnb_corpus_v1.md](../../../../data-cards/tiktok_fnb_corpus_v1.md) so it documents both `20261117_recovered_v1` and `20261118_taxonomy_fix_v1`, links `M1.1` human-vs-LLM error rates (`K_*` vs `N_*`), states semantic/POI/ASR non-claims, and explicitly records unresolved upstream source reuse/redistribution terms (blocking public corpus redistribution while keeping local-only demonstration in scope).
4. **Two-person reciprocal gate rule:**
   - Because `K` is primary owner of `M1.G`, `K` publishes the verified `M1.G` bundle with technical recommendation `PASS` (local-only scope; public corpus redistribution `BLOCKED`), while keeping `M1.G = IN_PROGRESS` and formal `G1 = NOT_RUN` until Nguyễn Việt Nguyên (`N`) completes reciprocal peer review.

## Owner-Confirmed `N` Peer Review & `G1 = PASS` Addendum — 2026-11-18

On `2026-11-18T22:17:25+07:00`, the project owner confirmed that Nguyễn Việt Nguyên (`N`) completed reciprocal peer review and instructed marking tasks waiting solely on `N`'s review `COMPLETE`. Because `M1.G` has satisfied every upstream and technical gate criterion (`G0 = PASS`, `M1.1` & `M1.2` `COMPLETE`, dual-snapshot SHA256/lineage/delta verification `PASS`, and qualified data card with explicit local-only / public-redistribution-blocked policy), archive the pre-confirmation report, emit `evidence/g1-gate-decision-receipt.json`, and record `M1.G = COMPLETE` and `G1 = PASS` (local-only demonstration/evaluation scope; public corpus redistribution `BLOCKED`). Do **not** mark `M2.3` or `M6.1` `COMPLETE` because both still have unmet substantive deliverables (`K`'s 15 queries + 30-draft claim audit on `M2.3`; `M2.2` frozen human-judged qrels + `M4.G`/`M5.G` + `K` review on `M6.1`).
