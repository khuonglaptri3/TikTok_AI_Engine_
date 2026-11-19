# M1.G — Historical Gold Corpus Gate Package (`G1`)

- Status: IN_PROGRESS (`K` primary gate verification, data-card update, and dual-snapshot integrity probe complete; awaiting reciprocal peer review by Nguyễn Việt Nguyên, `N`, before setting `G1 = PASS`)
- Gate result: NOT_RUN (technical recommendation: `PASS` for local-only demonstration/evaluation scope; public corpus redistribution `BLOCKED` due to unresolved upstream source rights)
- Execution date: 2026-11-18 (Asia/Saigon)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M1.G`)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer: Nguyễn Việt Nguyên (`N`)
- Repository version: `main` @ `e050d7d5bbcf90e310bbfd144407086d82479341` (following formal `G0 = PASS`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Following formal owner approval of `G0 = PASS` ([M0.G](../M0.G/README.md)) and completion of [M1.1](../M1.1/README.md) and [M1.2](../M1.2/README.md), all primary `M1.G` corpus gate checks pass in `5.841s` on Windows 11 CPU ([g1_verification_receipt.json](evidence/g1_verification_receipt.json)). Both `data/corpus/20261117_recovered_v1` (`manifest.json` SHA256 `10ed9c66...`) and `data/corpus/20261118_taxonomy_fix_v1` (`manifest.json` SHA256 `49f23739...`, bound to `parent_snapshot_id="20261117_recovered_v1"`) pass `load_verified_corpus` checksum, schema (`264x15` creators, `70,996x49` videos), key uniqueness, join, and finite safe-ratio assertions with `0` byte changes, reproducing every audited `M1.1`→`M1.2` disambiguation delta (`city_norm +6,464`, `district_norm +8,481`, `region +7,055`, `"ốc" -3,785`, `"an_vat_xe_chieu" -58,400`).

The qualified data card ([tiktok_fnb_corpus_v1.md](../../../data-cards/tiktok_fnb_corpus_v1.md)) has been updated to document both snapshots, link `M1.1` sampled human-vs-LLM error rates (`K_*` vs `N_*`), and explicitly record that **public corpus redistribution is `BLOCKED`** due to unresolved upstream reuse/redistribution terms while **local CPU demonstration and private team evaluation remain eligible**. Per the two-person gate rule, `M1.G` remains `IN_PROGRESS` and `G1` remains `NOT_RUN` pending reciprocal review by Nguyễn Việt Nguyên (`N`).

## Work performed

- Updated [tiktok_fnb_corpus_v1.md](../../../data-cards/tiktok_fnb_corpus_v1.md) (`sha256=5f65b280...`) with `20261118_taxonomy_fix_v1` lineage/deltas, `M1.1` blinded human (`K_*`, `n=30`) vs LLM-assisted (`N_*`, `n=120`) error/agreement metrics, semantic/POI/ASR non-claims, and the `G1` source-rights boundary.
- Implemented and executed [run_g1_checks.py](evidence/run_g1_checks.py) to assert `G0 == PASS`, `M1.1`/`M1.2` completion, dual-snapshot SHA256 & parent-manifest verification, finite safe ratios, taxonomy deltas, unchanged snapshot bytes, and `scripts/check_secrets.py` (`0` leaks).

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Superpowers skill provenance, decisions, and verification ledger |
| [run_g1_checks.py](evidence/run_g1_checks.py) | Reproducible asserting `G1` corpus, lineage, delta, and data-card probe |
| [g1_verification_receipt.json](evidence/g1_verification_receipt.json) | Machine-readable `G1` verification receipt, snapshot SHA256s, and scope boundaries |
| [g1_checks.log](evidence/g1_checks.log) | Console output from `run_g1_checks.py` (`PASS` in `5.841s`) |
| [tiktok_fnb_corpus_v1.md](../../../data-cards/tiktok_fnb_corpus_v1.md) | Updated qualified Gold corpus data card covering both snapshots and rights limits |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python docs/reports/milestones/M1.G/evidence/run_g1_checks.py` | PASS (`5.841s`, `0` byte mutations) | `G0 == PASS`, `M1.1`/`M1.2` `COMPLETE`, `load_verified_corpus` on both snapshots, parent lineage, safe ratios, deltas, and data-card checks; [g1_verification_receipt.json](evidence/g1_verification_receipt.json) |
| `python scripts/check_secrets.py` | PASS (`0` leaks) | Workspace secret scan invoked inside `run_g1_checks.py`; [g1_verification_receipt.json](evidence/g1_verification_receipt.json) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Reciprocal peer review by Nguyễn Việt Nguyên (`N`) pending | Primary owner (`K`) cannot unilaterally mark `G1 = PASS` | `N` reviews `M1.G` bundle and data card to close `M1.G` and set `G1 = PASS` (local-only scope) |
| Upstream source reuse/redistribution license unresolved | Public redistribution of raw/Gold corpus remains `BLOCKED` | Retain local-only boundary in `M2.G` and `M6.G` unless source rights are established |
| Residual heuristic category/format errors (`M1.1`: `K` `format` `30.00%`, `category` `43.33%` on `n=30`) | Machine labels cannot be presented as semantic ground truth | Enforced via descriptive non-claim wording in `M2.1`–`M6.2` and [tiktok_fnb_corpus_v1.md](../../../data-cards/tiktok_fnb_corpus_v1.md) |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Prerequisite `G0 = PASS` and `M1.1`–`M1.2` `COMPLETE` | Met | [owner-gate-decision-receipt.json](../M0.G/evidence/owner-gate-decision-receipt.json), [M1.1](../M1.1/README.md), [M1.2](../M1.2/README.md) |
| Immutable Gold snapshots, SHA256s, parent lineage, and safe ratios verified | Met | [g1_verification_receipt.json](evidence/g1_verification_receipt.json) |
| Qualified data card & local-only / public-redistribution-blocked policy documented | Met | [tiktok_fnb_corpus_v1.md](../../../data-cards/tiktok_fnb_corpus_v1.md) |
| Reciprocal peer review by `N` | Pending `N` review | Ready for `N` sign-off on `M1.G` |

Final status: **`M1.G` is `IN_PROGRESS` and Gate `G1` is `NOT_RUN`** (technical recommendation: `PASS` for local-only demonstration scope; public corpus redistribution `BLOCKED`), ready for reciprocal review by Nguyễn Việt Nguyên (`N`).
