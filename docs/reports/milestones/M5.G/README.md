# M5.G — Qualified Comment & Aspect Trust-Diagnostic Gate (`G5 = PASS`)

- Status: COMPLETE (`M5.1 = COMPLETE` and `M5.2 = COMPLETE`; all technical `G5` checks, real-sample provenance, video-disjoint anti-leakage boundaries, `100%` NFC span audits, `>= 3`-comment abstention, and diagnostic-only UI/API limits **PASS** in [run_g5_checks.py](evidence/run_g5_checks.py); joint `K` + `N` confirmation recorded in [g5-gate-decision-receipt.json](evidence/g5-gate-decision-receipt.json) on `2026-11-27T08:39:15+07:00`, flipping `G5 = PASS`)
- Execution date: 2026-11-26 to 2026-11-27 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M5.G`)
- Repository version: `main` (post-`71cf3232`)
- Shared co-owners: Trần Đình Khương (`K`, `2` pts) & Nguyễn Việt Nguyên (`N`, `2` pts)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Executed the deterministic Gate `G5` verification suite ([run_g5_checks.py](evidence/run_g5_checks.py) -> [g5_verification_receipt.json](evidence/g5_verification_receipt.json)) across `M5.1`, `M5.2`, and all `4` immutable Gold snapshots (`20261118_taxonomy_fix_v1`, `m3_3_pilot_snapshot_v1`, `m3_3_pilot_snapshot_v2`, `m3_3_playwright_comments_20261125_v5`) in **`20.286 s`** at **`USD 0` spend** with **`0` byte mutations**:

- **`M5.1` Observable Comment Indicators (`ACCEPTED_DIAGNOSTIC_ONLY_WITHOUT_AUTO_FILTERING`):** Verified `300` real `M3.3` comments (`22` videos: `N` `180/180` + `K` `180/180` blinded verified, `60` overlap `93.33%` raw / `100.0%` positive-indicator agreement, real organic-duplicate FP `2 -> 0`, `0` video overlap across splits). Because `contact_or_link` and `observable_duplicate` had `0` support on `held_out_third` (`all_pool` `macro_precision = 0.3095`, `macro_recall = 0.3095`), **automatic comment filtering remains unaccepted (`auto_filter_eligible = false`)**; `/api/v1/trust/audit-video` (`comment_filter_policy = "diagnostic_only_unvalidated"`) and `/demo/` (`hide_seeding = False` default) display observable diagnostic badges and before/after sensitivity without hiding comments automatically.
- **`M5.2` Four-Aspect ABSA with NFC Spans (`ACCEPTED_QUALIFIED_SPAN_GROUNDED_SENTIMENT_DISCREPANCY`):** Verified `180` real multimodal `M3.3` text units (`29` videos: `N` `115/115` + `K` `115/115` blinded verified, `50` overlap `kappa_presence = 0.8616` / `kappa_4state = 0.7731`, `44/44 = 100.0%` gold NFC spans), strict `0` video overlap across `dev` (`14` videos), `held_out` (`15` videos), and `absa_train_video_disjoint_v1.jsonl` (`90` videos, `human_verified = false` never used as Gold test), and `held_out` `aspect_detection_macro_f1 = 0.9286 >= 0.65` (conservative 4-aspect `0.6964 >= 0.65`), `observed_sentiment_macro_f1 = 0.8293 >= 0.60`, and `predicted_span_validity = 1.0000 >= 0.95`.
- **Mandatory Qualifications & Abstention Boundaries:** `service` had `gold_support = 0` in the `180`-unit real pilot sample; runtime enforces `min_viewer_comments = 3` (`26/29` sparse pilot videos abstain) and frames overlapping creator-vs-comment deltas strictly as observed `sentiment_discrepancy`, never proof of creator deception, food-safety truth, bot coordination, or diner consensus.

## Work performed

- **TDD `G5` gate-check suite ([test_m5_g_gate_checks.py](../../../../tests/unit/test_m5_g_gate_checks.py), [run_g5_checks.py](evidence/run_g5_checks.py)):** Authored `3` fail-closed unit tests (`RED -> GREEN`) verifying `M5.1` diagnostic-only gating, `M5.2` human signoff / video-disjoint anti-leakage / NFC span / F1 thresholds, and live FastAPI + `/demo/` UI defaults.
- **Cryptographic `G5` receipts ([g5_verification_receipt.json](evidence/g5_verification_receipt.json), [g5-gate-decision-receipt.json](evidence/g5-gate-decision-receipt.json)):** Verified SHA-256 digests across `M5.1`/`M5.2` receipts and `4` Gold snapshots, recording `K`'s co-owner `PASS` signoff awaiting `N`'s co-sign.

## Feature Acceptance Summary (`Gate G5`)

| Capability / Target | `G5` Technical Ruling | Qualification / Boundary |
| --- | --- | --- |
| Observable duplicate/contact/noise flags (`M5.1`) | **Accepted (Diagnostic Only)** | `hide_seeding = False` default; automatic filtering **unaccepted** (`auto_filter_eligible = false`) |
| 4-aspect ABSA + exact `NFC` `source_spans` (`M5.2`) | **Accepted (Qualified)** | `100%` NFC span validity; `F1 = 0.9286` / `0.8293`; `service` `gold_support = 0` explicitly qualified |
| Creator-vs-comment `sentiment_discrepancy` (`>= 3` comments) | **Accepted (Support-Gated)** | Abstains (`None`) when `< 3` distinct clean viewer comments mention an overlapping aspect |
| Bot/payment/coordinated-seeding or diner-consensus claims | **Rejected & Unaccepted** | Zero verified identity/payment ground truth; never asserted in API or `/demo/` |

## Outputs

| File | Purpose |
| --- | --- |
| [g5-gate-decision-receipt.json](evidence/g5-gate-decision-receipt.json) | Per-feature `G5` technical ruling and `K` co-owner `PASS` sign-off (awaiting `N` co-sign) |
| [g5_verification_receipt.json](evidence/g5_verification_receipt.json) | Full `M5.1` + `M5.2` + `4`-snapshot SHA-256 + live API/UI verification receipt |
| [run_g5_checks.py](evidence/run_g5_checks.py) | Deterministic executable Gate `G5` verification script |
| [workflow.md](evidence/workflow.md) | Superpowers TDD (`RED -> GREEN`) and gate-probe execution ledger |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 docs/reports/milestones/M5.G/evidence/run_g5_checks.py` | PASS (`20.286 s`, `0` byte mutations) | `M5.1`, `M5.2`, `4` Gold snapshots, & live ASGI/UI diagnostic defaults; [g5_verification_receipt.json](evidence/g5_verification_receipt.json) |
| `python3 -m pytest tests/unit/test_m5_g_gate_checks.py -v` | PASS (`3 passed in 12.15s`) | Fail-closed rejection of false auto-filter, train/test overlap, and UI/API abstention |
| `python3 -m pytest -q` & `python3 -m mypy` (Linux & `--platform win32`) | PASS (`0` failures / `0` issues) | Full workspace regression and cross-platform static typing |
| `python3 scripts/check_secrets.py` & docs hygiene check | PASS (`0` leaks; `0` broken links) | Repository secret hygiene and `M5.G/` layout compliance |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Sparse positive spam (`0` `contact_or_link` / `observable_duplicate` on `held_out_third`) and `service` `gold_support = 0` in `180`-unit pilot | Auto-filtering remains unaccepted (`diagnostic_only_without_filtering` enforced) and `< 3`-comment threads abstain | Preserved transparently in API, `/demo/`, and [M6.G](../M6.G/README.md) |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Independently annotated real pilot data, provenance, uncertainty, spans, abstention, and filter sensitivity meet `M5.1`–`M5.2` criteria | Met (`300` `M5.1` comments + `180` `M5.2` units `100%` `N`+`K` verified; `100%` NFC spans; `0` video overlap) | [g5_verification_receipt.json](evidence/g5_verification_receipt.json) |
| Insufficient positive spam data keeps automatic filtering unaccepted; demo displays diagnostic limits | Met (`auto_filter_eligible = false`, `hide_seeding = False`, `min_viewer_comments = 3` abstention) | [g5_verification_receipt.json](evidence/g5_verification_receipt.json), [g5-gate-decision-receipt.json](evidence/g5-gate-decision-receipt.json) |
| Two-person reciprocal gate confirmation (`K` + `N`) | Met (`K` & `N` confirmed `G5 = PASS`, `2026-11-27T08:39:15+07:00`) | [g5-gate-decision-receipt.json](evidence/g5-gate-decision-receipt.json) |

Final status: **`M5.G` is `COMPLETE` and Gate `G5` is `PASS` (`M5.1` accepted in diagnostic-only mode without auto-filtering; `M5.2` accepted as qualified `>= 3`-comment span-grounded sentiment discrepancy)**.
