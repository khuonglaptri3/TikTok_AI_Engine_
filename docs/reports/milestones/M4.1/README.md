# M4.1 — Timestamp & Prosody CPU Evaluation

- Status: COMPLETE (Two-contributor `N` + `K` audio/reference audit, reciprocal TDD hardening, `100%` `436/436` `audio_derived` temporal invariants, `29`-`.mp3` CPU prosody extraction `RTF = 0.009`, and `53 >= 50` strictly agreed human-verified utterances complete with `WER = 0.2668`, `CER = 0.1689`, boundary `median = 0.06 s <= 1.0 s`, `p95 = 0.20 s <= 3.0 s`, `precise_playback_allowed = true` as bounded `audio_derived` estimates; downstream Gate `M4.G` remains `NOT_RUN`)
- Execution date: 2026-11-23 to 2026-11-26 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M4.1`)
- Repository version: `main` (post-`431ec5f8` Phase 2 completion)
- Contributors: Trần Đình Khương (`K`, primary owner: reciprocal evaluator TDD hardening, `38/38` audio verification & acoustic error taxonomy) · Nguyễn Việt Nguyên (`N`, CPU prosody/invariant pipeline, `60`-utterance pool export & `38/38` audio verification)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**Completed `M4.1` end-to-end across real `M3.3` pilot audio (`29` `.mp3` files = `46.875` min `<= 60.0` cap) with both `N` (`38/38`) and `K` (`38/38`) independent audio verifications (`53 >= 50` strictly agreed utterances + `7` preserved double-review phrasing variants across `16.752` min `<= 20.0` cap):**

- **100% Temporal Invariants & Provenance Qualification ([m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json)):** All `436/436` (`1.0000`, `0` violations) Whisper utterances satisfy `0.0 <= start_sec < end_sec <= media_duration_sec` and resolve 1-to-1 to `m3_3_pilot_snapshot_v1`, normalized strictly to **`audio_derived`** (bounded acoustic estimates, never exact word-level speech timing), while historical interpolated rows remain **`wps_estimated`**.
- **Descriptive CPU Prosody Within Compute Budgets (`USD 0`):** Extracted finite `pitch_std` (median `49.8221` Hz) and `energy_cv` (median `0.5052`) across `29/29` `.mp3` files and `436/436` utterances in **`25.331 s`** (`RTF = 0.009`, `peak_rss_mib = 240.14 MiB <= 8,192 MiB`), paired with `M3.3` CPU ASR (`197.269 s`, `RTF = 0.1971`, `1,009.46 MiB` `<< 4` CPU hours), framed strictly as descriptive acoustic variation rather than intent or sponsorship evidence.
- **Two-Person CER/WER, Boundary Accuracy & Inter-Annotator Agreement ([m4_1_joint_reference_eval_receipt.json](evidence/m4_1_joint_reference_eval_receipt.json)):**
  - Across the **`53` strictly agreed `human_verified=true` utterances** (`22 N_only` + `22 K_only` + `9/16` exact-match `N==K` overlap; `551` words, `1,753` chars, `106` boundaries): **`WER = 0.2668`** (`119 S, 27 D, 1 I`; **`0.2450`** after ITN numeral/currency normalization), **`CER = 0.1689`** (`0.1492` ITN-normalized), boundary **`median = 0.06 s <= 1.0 s`** (`start = 0.04 s`, `end = 0.06 s`), and **`p95 = 0.20 s <= 3.0 s`** (`precise_playback_allowed = true` for bounded `audio_derived` segment offsets).
  - Full `60`-utterance sensitivity checks (`K`-phrasing vs `N`-phrasing on the `7` preserved overlap phrasing variants) yield `WER = 0.2873` vs `0.2909`, `CER = 0.1777` vs `0.1808`, `median = 0.06 s`, and `p95 = 0.20 s` (`precise_playback_allowed = true` in both).
  - Across all `16/16` double-reviewed utterances (`compute_m4_1_annotator_agreement`), `N` and `K` achieved `9/16` (`56.25%` raw; `10/16 = 62.50%` equating `"ngàn"`/`"nghìn"`) exact word-sequence agreement, symmetric inter-annotator **`WER = 0.1366`** (`0.1056` dialect-normalized), **`CER = 0.0943`** (`0.0781` dialect-normalized), and boundary difference **`median = 0.04 s`** (`p95 = 0.158 s`).
  - Documented high-impact Vietnamese F&B ASR lexical failure modes (e.g., `"40 50 nghìn"` -> `"450k"`, `"cao cấp"` -> `"cao thấp"`, Southern `"lột"` -> `"lộp"`, `"vú sữa dầm"` -> `"suy dạm"`) in [khuong_prosody_peer_review.md](evidence/khuong_prosody_peer_review.md).

## Work performed

- **Phase 1 — CPU DSP prosody extractor, temporal invariant auditor, `60`-utterance pool & `N` `38/38` verification (`N`):** Implemented [packages/prosody/](../../../../packages/prosody) and [run_m4_1_pilot.py](../../../../pipelines/audit_m4_1_audio/run_m4_1_pilot.py), processed all `29` `.mp3` files and `436` utterances, and recorded `N`'s `38/38` verified references ([m4_1_n_reference_eval_receipt.json](evidence/m4_1_n_reference_eval_receipt.json)).
- **Phase 2 — Reciprocal evaluator TDD hardening, `K` `38/38` sample-accurate `.wav`/`.mp3` audit & joint evaluation (`K`):** Hardened `evaluate_m4_1_reference_set` (`invalid_verified_row_count` fail-closed validation, full-pool `20.0`-min cap, `S/D/I` counts) and added `compute_m4_1_annotator_agreement` via TDD (`6/6` tests in [test_m4_1_prosody_and_timestamps.py](../../../../tests/unit/test_m4_1_prosody_and_timestamps.py)), verified `K`'s `38/38` utterances (`27.0` min), preserved all `7` nuanced `N`-vs-`K` phrasing differences transparently without overwriting `N_ref_*`, and published [m4_1_joint_reference_eval_receipt.json](evidence/m4_1_joint_reference_eval_receipt.json) + [khuong_prosody_peer_review.md](evidence/khuong_prosody_peer_review.md).

## Outputs

| File | Purpose |
| --- | --- |
| [m4_1_joint_reference_eval_receipt.json](evidence/m4_1_joint_reference_eval_receipt.json) | Canonical `53`-utterance joint `WER`/`CER`/boundary receipt (`precise_playback_allowed = true`), `60`-utt & ITN sensitivities, and `16`-utt `N`-vs-`K` IAA |
| [m4_1_utterance_review_sheet.jsonl](evidence/m4_1_utterance_review_sheet.jsonl) | `60`-utterance workbook (`22 N_only` + `22 K_only` + `9` exact consensus = `53` `human_verified=true`; `7` double-verified phrasing diffs preserved in `N_ref_*`/`K_ref_*`) |
| [khuong_prosody_peer_review.md](evidence/khuong_prosody_peer_review.md) | `K`'s reciprocal code/evaluator audit and Vietnamese F&B ASR acoustic error taxonomy |
| [m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json) | Real `29`-`.mp3` CPU prosody (`25.331 s`, `240.14 MiB`) and `436/436` temporal invariant receipt |
| [m4_1_n_reference_eval_receipt.json](evidence/m4_1_n_reference_eval_receipt.json) | Preserved Phase 1 `N` `38`-utterance preliminary receipt |
| [workflow.md](evidence/workflow.md) | Two-contributor (`N` + `K`) Superpowers TDD and audio-verification provenance ledger |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 -m pytest tests/unit/test_m4_1_prosody_and_timestamps.py -v` | PASS (`6 passed in 4.95s`) | DSP prosody/silence, invariants, CER/WER/boundary gate, strict verified bounds, full-pool `20m` cap, and `N`-vs-`K` IAA |
| `python3 -m pytest -q` & `python3 -m mypy` (Linux & `--platform win32`) | PASS (`266 passed, 10 skipped`; `117` source files `0` errors) | Full workspace regression and cross-platform static typing |
| `python3 scripts/check_secrets.py` & docs link/structure check | PASS (`0` leaks; `0` broken links) | Repository secret hygiene and `M4.1/` layout compliance |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `7/16` double-reviewed overlap utterances retain minor colloquial/dialect phrasing differences (`"19 nghìn"` vs `"19 ngàn"`, `"với"` vs `"với lại"`, `"Hà Nội"` vs `"họ nói ở"`, `"Dừa"` vs `"Dữ"`) | Zero gate impact: strict consensus already has `53 >= 50` verified utterances, and both `60`-utterance sensitivity variants pass (`med = 0.06 s`, `p95 = 0.20 s`) | Preserve both `N_ref_*` and `K_ref_*` transparently for joint review during Gate `M4.G` |
| Upstream Gate `M3.G` (`G3`) awaits final `N` co-sign & Gate `M4.G` (`G4`) is `NOT_RUN` | `M4.1` and `M4.2` are both `COMPLETE`, ready for joint `M4.G` evaluation once `G3` is co-signed | `N` & `K` execute `M4.G` (`Gate G4`) decision |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Process `<= 60` min captured pilot audio within `<= 4 CPU h` & `<= 8 GiB RAM`; qualify `audio_derived` vs `wps_estimated` & descriptive prosody | Met (`29` `.mp3`, `46.875` min, `25.331 s` prosody + `197.269 s` ASR, `<= 1,009.46 MiB` RSS) | [m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json) |
| `100%` `0 <= start < end <= media_duration` & source resolvability | Met (`436/436 = 1.0000`, `0` violations) | [m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json) |
| Two-person `<= 20` min & `>= 50` utterance CER/WER & boundary audit (`<= 1 s` median, `<= 3 s` p95) + reciprocal review | Met (`16.752` min, `53 >= 50` agreed verified utts: `WER = 0.2668`, `CER = 0.1689`, `med = 0.06 s`, `p95 = 0.20 s`; `N` + `K` reviewed) | [m4_1_joint_reference_eval_receipt.json](evidence/m4_1_joint_reference_eval_receipt.json), [khuong_prosody_peer_review.md](evidence/khuong_prosody_peer_review.md) |

Final task status: **`COMPLETE`** (`M4.1` and `M4.2` are both `COMPLETE`; Gate `M4.G` remains **`NOT_RUN`** pending joint `N`+`K` gate review).
