# M4.1 — Timestamp & Prosody CPU Evaluation

- Status: IN_PROGRESS (`N` implemented CPU prosody/invariant extraction in `packages/prosody/` & `pipelines/audit_m4_1_audio/`, verified `100%` temporal invariants across `29` `.mp3` files / `436` utterances ([m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json)), and completed `N`'s `38/38` (`22 N_only` + `16` overlap half) audio-verified references in [m4_1_utterance_review_sheet.jsonl](evidence/m4_1_utterance_review_sheet.jsonl) ([m4_1_n_reference_eval_receipt.json](evidence/m4_1_n_reference_eval_receipt.json): `WER=0.3042`, `CER=0.1770`, `median=0.08 s`, `p95=0.255 s`); **stays `IN_PROGRESS` (`precise_playback_allowed = false`)** awaiting `K`'s `22 K_only` + `16` overlap references (`>= 50` joint gate) and `M3.G` closure)
- Execution date: 2026-11-23 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M4.1`)
- Repository version: `feat/m4.1-audio-prosody-and-timestamp-eval` (branched from `main` @ `bde4017f`)
- Contributors: Nguyễn Việt Nguyên (`N`, CPU pipeline, evaluator & reference/error reviewer) · Trần Đình Khương (`K`, co-annotator & `M3.G` gate owner)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

**CPU prosody extraction, strict temporal-invariant enforcement, CER/WER/boundary evaluator TDD, and blinded `60`-utterance reference-pool export are complete on real `M3.3` pilot audio (`436/436` valid `0 <= start < end <= media_duration` intervals labeled `audio_derived`, `29/29` `.mp3` files processed in `25.331 s` at `RTF = 0.009` and `240.14 MiB` peak RSS); `M4.1` stays `IN_PROGRESS` (`abstain_precise_playback = true`) until `K` & `N` annotate [m4_1_utterance_review_sheet.jsonl](evidence/m4_1_utterance_review_sheet.jsonl) and `M3.G` closes.**

- **Descriptive CPU Prosody & Resource Budget ([m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json)):** Processed all `29` captured `.mp3` files (`2,812.51 s` = `46.875` min `<= 60.0` cap; `22,524,055` B) in `25.331 s` (`RTF = 0.009`, `peak_rss_mib = 240.14 MiB <= 8,192 MiB`), yielding finite descriptive `pitch_std` (video median `49.8221` Hz) and `energy_cv` (video median `0.5052`) for `29/29` files and `436/436` utterance slices (`never intent, emotion certainty, or undisclosed sponsorship`).
- **100% Temporal Invariant & Provenance Audit:** Decoded exact `.mp3` durations via `ffmpeg` and verified **`436/436` (`invariant_pass_rate = 1.0`, `0` violations)** satisfy `0.0 <= start_sec < end_sec <= media_duration_sec` and resolve 1-to-1 to `m3_3_pilot_snapshot_v1`, with every Whisper utterance normalized strictly to **`audio_derived`** (`0` `wps_estimated`).
- **Two-Person Reference Sheet (`<= 20` min, `>= 50` utterances):** Exported **`60` utterances** across `10` transcribed videos (`16.752` audio min `<= 20.0` cap; `16 double_review_N_K`, `22 N_only`, `22 K_only`) under explicit `TOKENIZATION_SPEC` (`Unicode NFC -> lowercase -> strip punctuation`). `N` directly inspected all `10` audio clips + word-level acoustic alignments and confirmed **`38/38` `N`-assigned utterances** (`22/22` `N_only` `human_verified=true` + `16/16` `double_review_N_K` `N_verified=true`, keeping all `K` fields untouched at `false`), measuring preliminary `WER = 0.3042`, `CER = 0.1770`, boundary median **`0.08 s`**, and p95 **`0.255 s`** ([m4_1_n_reference_eval_receipt.json](evidence/m4_1_n_reference_eval_receipt.json)). Fail-closed gate keeps `precise_playback_allowed = false` until `K` completes `K`'s half (`>= 50` joint verified utterances).

## Work performed

- **Core prosody & timestamp library ([packages/prosody/](../../../../packages/prosody)):** Added `decode_audio_pcm_16k`, `extract_prosody_features`, `normalize_timestamp_source`, `audit_temporal_invariants` ([extractor.py](../../../../packages/prosody/extractor.py)), `tokenize_vi_words`, `tokenize_vi_chars`, `compute_levenshtein_distance`, `evaluate_m4_1_reference_set`, and `build_m4_1_reference_pool` ([evaluation.py](../../../../packages/prosody/evaluation.py)), plus additive `"audio_derived"` literal support in `VoiceSegmentRecord` ([multimodal.py](../../../../packages/data_contracts/multimodal.py)).
- **Audit CLI, real pilot execution & `N` reference verification ([run_m4_1_pilot.py](../../../../pipelines/audit_m4_1_audio/run_m4_1_pilot.py), [m4_1_n_reference_eval_receipt.json](evidence/m4_1_n_reference_eval_receipt.json)):** Processed all `29` `.mp3` files and `436` utterances from `m3_3_pilot_snapshot_v1`, audited all `10` clips by listening + word-level alignments, and recorded `N`'s confirmed `38/38` references (`22 N_only` + `16 N_overlap`) while preserving `K`'s `22` `K_only` + `16` overlap fields untouched.
- **TDD tests ([test_m4_1_prosody_and_timestamps.py](../../../../tests/unit/test_m4_1_prosody_and_timestamps.py)):** Verified synthetic prosody vs silence abstention, temporal invariant failure modes, `"whisper_exact"` -> `"audio_derived"` normalization, hand-checked CER/WER, `<= 1s` median / `<= 3s` p95 abstention gates, `20m`/`60m` pool bounds, and fail-closed file overwrite checks.

## Outputs

| File | Purpose |
| --- | --- |
| [m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json) | Real CPU prosody stats (`29` `.mp3`, `436` utterances), `100%` temporal invariant audit, resource usage (`25.331 s`, `240.14 MiB`), and initial fail-closed baseline status |
| [m4_1_utterance_review_sheet.jsonl](evidence/m4_1_utterance_review_sheet.jsonl) | `60`-utterance (`16.752` min `<= 20.0`) reference workbook (`22 N_only` verified + `16 double_review_N_K` `N`-half verified; `22 K_only` + `16` `K`-half pending `K`) |
| [m4_1_n_reference_eval_receipt.json](evidence/m4_1_n_reference_eval_receipt.json) | Measured `N` `38`-utterance preliminary `WER = 0.3042`, `CER = 0.1770`, boundary median `0.08 s`, p95 `0.255 s` (`precise_playback_allowed = false` until `>= 50` joint count) |
| [workflow.md](evidence/workflow.md) | TDD RED -> GREEN trace, pilot run provenance, and verification ledger |
| [packages/prosody/](../../../../packages/prosody), [run_m4_1_pilot.py](../../../../pipelines/audit_m4_1_audio/run_m4_1_pilot.py) | Reusable CPU prosody extractor, invariant auditor, CER/WER & boundary evaluator, and bounded CLI runner |
| [test_m4_1_prosody_and_timestamps.py](../../../../tests/unit/test_m4_1_prosody_and_timestamps.py) | `5` TDD unit and end-to-end pipeline verification tests |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `.venv/bin/python -m pipelines.audit_m4_1_audio.run_m4_1_pilot` | PASS (`29` `.mp3`, `46.875` min, `inv_rate=1.0`, `60` pool utts) | Real CPU audit on `m3_3_pilot_snapshot_v1`; [m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json) |
| `.venv/bin/python -m pytest -v` | PASS (`224 passed in 46.18s`) | Full repository suite including `5/5` M4.1 TDD & audit tests |
| `.venv/bin/ruff check` (M4.1 paths) & `mypy` Linux / `win32` | PASS (`All checks passed!`; `111` Linux / `110` `win32` files) | Strict lint and cross-platform static types |
| `python3 scripts/check_secrets.py` & relative link check | PASS (`0` leaks; `60` relative links `0` broken) | Workspace secret hygiene & `M4.1/` layout (`README.md`, `evidence/`, `superpowers/{spec.md, plan.md}`) |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| `K` half of [m4_1_utterance_review_sheet.jsonl](evidence/m4_1_utterance_review_sheet.jsonl) pending (`N` completed `38/38`: `22 N_only` + `16` overlap; `K` has `22 K_only` + `16` overlap pending) | Joint verified utterance count on sheet is `22 < 50` (`38` counting `N`'s un-adjudicated overlap); `precise_playback_allowed` remains `false` (`abstain_precise_playback = true`) | `K` completes `K`'s `38` utterances (`22 K_only` + `16` overlap), both adjudicate any differences, and run `evaluate_m4_1_reference_set` before closing `M4.1` -> `COMPLETE` & `M4.G` |
| Upstream Gate `G3` (`M3.G`) still `NOT_RUN` (`K` `annotation_time_minutes` & `G3` ruling on `comment_coverage_rate = 0.0` pending) | `M4.1` depends on `M3.G` closure per [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md); baseline code/receipts are ready ahead of `G3` sign-off | `K` adds `K_minutes` + joint `G3` decision in `M3.G` before closing `M4.1` -> `COMPLETE` & `M4.G` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Process only captured pilot audio (`<= 60` min) within `<= 4 CPU h` & `<= 8 GiB RAM`; label ASR `audio_derived` (never exact speech timing) & prosody descriptive | Met (`29` `.mp3`, `46.875` min, `25.331 s`, `240.14 MiB`, `436/436` `audio_derived`) | [m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json) |
| Enforce `100%` `0 <= start < end <= media_duration` & source resolvability | Met (`436/436`, `invariant_pass_rate = 1.0`) | [m4_1_audio_pilot_receipt.json](evidence/m4_1_audio_pilot_receipt.json), [extractor.py](../../../../packages/prosody/extractor.py) |
| Sample `<= 20` min & `>= 50` utterances for 2-person CER/WER & boundary check (`<= 1 s` median, `<= 3 s` p95; abstain if unmet) + `N` review | Partial (`60` utterances / `16.752` min; `N` `38/38` verified: `WER=0.3042`, `CER=0.1770`, `med=0.08 s`, `p95=0.255 s`; `K` half pending -> `precise_playback_allowed = false`) | [m4_1_utterance_review_sheet.jsonl](evidence/m4_1_utterance_review_sheet.jsonl), [m4_1_n_reference_eval_receipt.json](evidence/m4_1_n_reference_eval_receipt.json) |

Final task status: **IN_PROGRESS** (`precise_playback_allowed = false`; CPU prosody/invariant extraction, `60`-utterance review sheet, and `N`'s `38/38` verified annotations complete; awaiting `M3.G` `K` timing/ruling + `K`'s `38`-utterance annotation & joint adjudication before `M4.1 -> COMPLETE` & `M4.G`).
