# M4.G — Audio Timing/Provenance & Observable Promotion Gate (`G4`)

- Status: IN_PROGRESS (`M4.1 = COMPLETE` and `M4.2 = COMPLETE`; all technical `G4` checks, `29`-video fresh prosody-vs-promo audit, anti-leakage checks, and ASGI epistemic refusal guardrails **PASS** in [run_g4_checks.py](evidence/run_g4_checks.py) with `K` peer-review concurrence recorded in [g4-gate-decision-receipt.json](evidence/g4-gate-decision-receipt.json); awaiting `N` primary-owner co-sign alongside `M3.G` before flipping global `G4` from `NOT_RUN` to `PASS`)
- Execution date: 2026-11-26 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M4.G`)
- Repository version: `main` (post-`1ad93439`)
- Primary owner: Nguyễn Việt Nguyên (`N`, `2` pts) · Peer reviewer & probe author: Trần Đình Khương (`K`, `2` pts)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Executed the deterministic Gate `G4` verification suite ([run_g4_checks.py](evidence/run_g4_checks.py) -> [g4_verification_receipt.json](evidence/g4_verification_receipt.json)) across `M4.1`, `M4.2`, and the `3` immutable Gold snapshots (`20261118_taxonomy_fix_v1`, `m3_3_pilot_snapshot_v1`, `m3_3_pilot_snapshot_v2`) in **`19.007 s`** at **`USD 0` spend** with **`0` byte mutations**:

- **`M4.1` Audio Timing & Descriptive Prosody (`ACCEPTED_BOUNDED_AUDIO_DERIVED_ESTIMATES`):** All `29` pilot `.mp3`s (`46.875` min `<= 60.0` cap) processed in `222.60 s` combined ASR + prosody wall time (`<< 14,400 s` `4` CPU h cap; `240.14 MiB` prosody / `1,009.46 MiB` ASR `<< 8,192 MiB`), `436/436` (`100%`) temporal invariants pass, and both `N` (`38/38`) + `K` (`38/38`) verified the `60`-utterance pool (`53 >= 50` strictly agreed `human_verified=true` utterances: `WER = 0.2668`, `CER = 0.1689`, boundary `median = 0.06 s <= 1.0 s`, `p95 = 0.20 s <= 3.0 s`). Fresh utterance timestamps are accepted strictly as bounded `audio_derived` estimates (`never exact word-level speech timing`), historical interpolated rows remain `wps_estimated`, and prosody remains descriptive-only.
- **`M4.2` Observable Promotion Indicators (`ACCEPTED_SEPARATED_OBSERVABLE_INDICATORS`) & Hidden Sponsorship (`DEFERRED_NO_GROUND_TRUTH`):** Verified separation of `is_ad`/`is_ec_video` from 4-category promotional language cues (`unlabeled_unknown` retained, `0` author overlap `is_ad_only` vs `is_ec_only` `PR-AUC = 0.8915` / `0.8728` without MCN/Shop tags, `100/100` `N`+`K` historical items verified with `Cohen's kappa = 0.6364`), runtime `assert_no_feature_leakage` rejection of `is_ad`, `poi_id`, `prosody_pitch_std`, `video_format`, and `has_cta`, and ASGI HTTP `422` refusal on undisclosed-PR probability prompts.
- **Post-`M4.1` Fresh `29`-Video Prosody vs. Promo Check (`REJECTED_EPISTEMICALLY_INVALID` for Classification):** Joining `M4.1` `per_video_prosody` (`29` fresh clips; all `29` `unlabeled_unknown` on platform flags) with `M4.2` lexical cues shows complete acoustic overlap between clips with promo cues (`n = 5`: median `pitch_std = 49.40 Hz`, `energy_cv = 0.4778`) and clips without promo cues (`n = 24`: median `pitch_std = 51.36 Hz`, `energy_cv = 0.5407`), confirming prosody must never be used to infer promotional or undisclosed sponsorship intent.

## Work performed

- **TDD gate-check suite ([test_m4_g_gate_checks.py](../../../../tests/unit/test_m4_g_gate_checks.py), [run_g4_checks.py](evidence/run_g4_checks.py)):** Authored `4` fail-closed unit tests (`RED -> GREEN`) verifying `M4.1` boundary/count/compute abstention, `M4.2` policy/leakage/audit invariants, the `29`-video fresh prosody-vs-promo descriptive join, and live FastAPI epistemic guardrails.
- **Cryptographic `G4` receipts ([g4_verification_receipt.json](evidence/g4_verification_receipt.json), [g4-gate-decision-receipt.json](evidence/g4-gate-decision-receipt.json)):** Verified SHA-256 digests across all `M4.1`/`M4.2` receipts/workbooks and recorded `K`'s peer-review `PASS` recommendation awaiting `N`'s primary-owner co-sign.

## Feature Acceptance Summary (`Gate G4`)

| Capability / Target | `G4` Technical Ruling | Qualification / Boundary |
| --- | --- | --- |
| Fresh ASR segment playback offsets (`audio_derived`) | **Accepted (Bounded Estimates)** | `436/436` invariants; `med = 0.06 s`, `p95 = 0.20 s`; never presented as exact word-level speech timing |
| Historical interpolated segment offsets (`wps_estimated`) | **Retained (`wps_estimated`)** | Explicitly distinguished from `audio_derived` across contracts, API, and `/demo/` |
| CPU prosody (`pitch_std`, `energy_cv`) | **Accepted (Descriptive Only)** | `25.331 s` (`RTF = 0.009`); never intent, emotion certainty, or promotion classifier input |
| Platform flags (`is_ad`, `is_ec_video`) & promo lexicon | **Accepted (Separated Indicators)** | Unflagged rows remain `unlabeled_unknown` (never verified negatives) |
| Undisclosed sponsorship probability / hidden-PR detection | **Deferred & Abstained (`HTTP 422`)** | Zero verified ground truth; disclosed-ad flags or prosody never converted into hidden-PR labels |

## Outputs

| File | Purpose |
| --- | --- |
| [g4-gate-decision-receipt.json](evidence/g4-gate-decision-receipt.json) | Per-feature `G4` technical ruling and `K` peer-review `PASS` recommendation (awaiting `N` co-sign) |
| [g4_verification_receipt.json](evidence/g4_verification_receipt.json) | Full `M4.1` + `M4.2` + `29`-video fresh prosody-vs-promo + ASGI guardrail SHA-256 verification receipt |
| [run_g4_checks.py](evidence/run_g4_checks.py) | Deterministic executable Gate `G4` verification script |
| [g4_checks.log](evidence/g4_checks.log) | Console execution log (`PASS in 19.007s`) |
| [workflow.md](evidence/workflow.md) | Superpowers TDD (`RED -> GREEN`) and gate-probe execution ledger |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 docs/reports/milestones/M4.G/evidence/run_g4_checks.py` | PASS (`19.007 s`, `0` byte mutations) | `M4.1`, `M4.2`, `29`-video fresh prosody join, leakage & ASGI HTTP `422` refusal; [g4_verification_receipt.json](evidence/g4_verification_receipt.json) |
| `python3 -m pytest tests/unit/test_m4_g_gate_checks.py -v` | PASS (`4 passed`) | Fail-closed abstention, policy/leakage rejection, fresh prosody join, and ASGI guardrails |
| `python3 -m pytest -q` & `python3 -m mypy` (Linux & `--platform win32`) | PASS (`270 passed, 10 skipped`; `117` source files `0` errors) | Full workspace regression and cross-platform static typing |
| `python3 scripts/check_secrets.py` & docs hygiene check | PASS (`0` leaks; `0` broken links) | Repository secret hygiene and `M4.G/` layout compliance |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Final `N` primary-owner co-sign on `M4.G` (alongside `M3.G`) | Per two-person governance, `M4.G` stays `IN_PROGRESS` and global `G4` stays `NOT_RUN` until `N` confirms [g4-gate-decision-receipt.json](evidence/g4-gate-decision-receipt.json) | `N` co-signs `M3.G` and `M4.G` (`G3 -> PASS`, `G4 -> PASS`) |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Timestamp quality/resource limits meet `M4.1` criteria (`100%` invariants, `<= 1 s` med, `<= 3 s` p95, `<= 4 CPU h`, `<= 8 GiB`) | Met (`436/436`, `med = 0.06 s`, `p95 = 0.20 s`, `222.60 s`, `<= 1,009.46 MiB`) | [g4_verification_receipt.json](evidence/g4_verification_receipt.json) |
| Observed-target wording meets `M4.2` criteria; gate does not convert disclosed flags or prosody into hidden-sponsorship labels | Met (`DEFERRED_NO_GROUND_TRUTH`, `HTTP 422` refusal, `29`-video prosody classifier rejected) | [g4_verification_receipt.json](evidence/g4_verification_receipt.json), [g4-gate-decision-receipt.json](evidence/g4-gate-decision-receipt.json) |
| Two-person reciprocal gate confirmation (`N` + `K`) | Ready for `N` co-sign (`K` peer-review `PASS` recorded) | [g4-gate-decision-receipt.json](evidence/g4-gate-decision-receipt.json) |

Final status: **`M4.G` is `IN_PROGRESS` (all technical `G4` checks `PASS`; awaiting `N` co-sign alongside `M3.G` to flip `M4.G -> COMPLETE` / `G4 -> PASS`)**.
