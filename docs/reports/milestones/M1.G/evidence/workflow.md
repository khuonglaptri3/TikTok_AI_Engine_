# M1.G (G1) — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-18 (Asia/Saigon)
- **Task / Gate ID:** `M1.G` (`G1`)
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`, pending reciprocal gate review)
- **Evaluated Revision:** `main` @ `e050d7d5bbcf90e310bbfd144407086d82479341` (with owner-approved `G0 = PASS`)

## Process & Superpowers Ledger (`AGENTS.md` Section 7)
- Skills read and applied: `using-superpowers`, `brainstorming` (bounded design presented and approved by owner prior to execution), `writing-plans`, `executing-plans`, `verification-before-completion`.
- Authored [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md) before modifying [tiktok_fnb_corpus_v1.md](../../../../data-cards/tiktok_fnb_corpus_v1.md) or running verification probes.
- Pre-flight: `M1.G` consumes `M0.G` (`G0 == PASS`), `M1.1` (`COMPLETE`), and `M1.2` (`COMPLETE`); no shared-code interface conflicts (`0` production source changes).

## Key Decisions
1. **Data Card Upgrade (`20261117_recovered_v1` + `20261118_taxonomy_fix_v1`):** Updated [tiktok_fnb_corpus_v1.md](../../../../data-cards/tiktok_fnb_corpus_v1.md) (`sha256=5f65b2800ca38adb218976c00ac8eb489a85bbe6960e6edee155a996a9645d10`) to document both the baseline and `M1.2` taxonomy-corrected snapshots, report `M1.1` human-vs-LLM (`K_*` vs `N_*`) sampled error/agreement rates, and formalize Section 5 blocking public corpus redistribution while upstream reuse/redistribution terms remain unresolved.
2. **Reciprocal Two-Person Gate Discipline:** Because `K` is primary owner of `M1.G`, `M1.G` stays `IN_PROGRESS` and formal Gate `G1` stays `NOT_RUN` awaiting reciprocal review by Nguyễn Việt Nguyên (`N`). Technical recommendation is `PASS` for local-only corpus scope (`PUBLIC_REDISTRIBUTION = BLOCKED`).

## Verification Commands & Receipts
- `uv run --offline --no-project --with-editable ".[demo,dev]" --python 3.12 python docs/reports/milestones/M1.G/evidence/run_g1_checks.py` -> `EXIT=0`, `PASS: G1 verification probe succeeded in 5.841s -> g1_verification_receipt.json` ([g1_checks.log](g1_checks.log), [g1_verification_receipt.json](g1_verification_receipt.json)).
- Verified `0` byte mutations across `data/corpus/20261117_recovered_v1` (`manifest.json` `10ed9c66...`) and `data/corpus/20261118_taxonomy_fix_v1` (`manifest.json` `49f23739...`), `(264, 15)` creators, `(70996, 49)` videos, finite safe ratios, and `scripts/check_secrets.py` `EXIT=0`.

## Owner-Confirmed `N` Peer Review & `G1 = PASS` Closure (`2026-11-18`)
- On `2026-11-18T22:17:25+07:00`, the project owner confirmed that Nguyễn Việt Nguyên (`N`) completed reciprocal peer review and instructed marking tasks waiting solely on review `COMPLETE`.
- Archived pre-confirmation `M1.G/README.md` byte-for-byte to [report-before-n-review-confirmation.md](report-before-n-review-confirmation.md) (`sha256=091734ef81f752292be0defa4954fa81d9561dc178c3900c14b6d96522edaadb`), emitted [g1-gate-decision-receipt.json](g1-gate-decision-receipt.json), and updated `M1.G` to `COMPLETE` and `G1` to `PASS` (local-only scope; public corpus redistribution `BLOCKED`).
- Preserved `M2.3` and `M6.1` as `IN_PROGRESS` per `AGENTS.md` Section 4 because both still have unmet substantive deliverables beyond peer review.
