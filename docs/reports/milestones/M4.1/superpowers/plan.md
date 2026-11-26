# M4.1 — Timestamp & Prosody CPU Evaluation Implementation Plan

**Architecture:** Build deterministic CPU DSP & temporal invariant checks in `packages/prosody/{__init__.py, extractor.py, evaluation.py}`, wire CLI audit runner `pipelines/audit_m4_1_audio/run_m4_1_pilot.py`, execute against the real `29`-`.mp3` `M3.3` pilot corpus into `docs/reports/milestones/M4.1/evidence/`, and verify via `pytest` TDD + `mypy` + `ruff` + secret hygiene.

## Steps

1. **TDD RED (`tests/unit/test_m4_1_prosody_and_timestamps.py`):**
   - Write failing tests for DSP `pitch_std` / `energy_cv` (modulated sine wave vs silence `None`), strict `0 <= start < end <= media_duration` invariants, `"whisper_exact"` -> `"audio_derived"` normalization, hand-calculated `CER`/`WER` tokenization, boundary error median `<= 1.0s` / p95 `<= 3.0s` + abstention gate (`< 50` utterances or violated threshold), and `<= 20.0` min / `>= 50` utterance pool sampling.
2. **Contract & Core Implementation (`packages/data_contracts/multimodal.py`, `packages/prosody/`):**
   - Allow `"audio_derived"` alongside legacy `"whisper_exact"` and `"wps_estimated"` on `VoiceSegmentRecord.timestamp_source` (backward compatible with `M3.1`/`M3.3`).
   - Implement `decode_audio_pcm_16k`, `extract_prosody_features`, `normalize_timestamp_source`, `audit_temporal_invariants` in `packages/prosody/extractor.py`.
   - Implement `tokenize_vi_words`, `tokenize_vi_chars`, `compute_levenshtein_distance`, `evaluate_m4_1_reference_set`, `build_m4_1_reference_pool` in `packages/prosody/evaluation.py`.
3. **Audit Pipeline (`pipelines/audit_m4_1_audio/run_m4_1_pilot.py`):**
   - Process all `29` `.mp3` files (`<= 60` min) + `436` `fact_voice_segments.parquet` utterances from `m3_3_pilot_snapshot_v1`, enforcing `<= 4 CPU hours` and `<= 8 GiB RSS`, producing `m4_1_audio_pilot_receipt.json` and `m4_1_utterance_review_sheet.jsonl` (`60` utterances across `16.683` audio min `<= 20.0`, blinded `human_verified=false`).
4. **TDD GREEN & Real-Audio Verification:**
   - Run `pytest`, `ruff`, Linux/`win32` `mypy`, real `run_m4_1_pilot.py` execution, secret hygiene (`check_secrets.py`), relative link checks, author `M4.1/README.md` + `workflow.md` (`Status: IN_PROGRESS` pending human annotation), update `milestones/README.md`, and open PR into `main` referencing `M3.G` open requirements for `K`.
5. **Phase 2 (`2026-11-26`, Contributor `K`):**
   - **Step 5.1 (TDD RED -> GREEN):** Add `test_m4_1_k_review_strict_verified_bounds_pool_cap_and_iaa` in `tests/unit/test_m4_1_prosody_and_timestamps.py`; watch RED; implement strict `human_verified` completeness/temporal validation, full-pool `total_sampled_audio_minutes`, S/D/I edit counts, and `compute_m4_1_annotator_agreement` in `packages/prosody/evaluation.py`; verify GREEN + Linux/`win32` `mypy`.
   - **Step 5.2 (Independent Audio Audit & `K` Confirmation Gate):** Slice sample-accurate audio clips + `10 ms` RMS speech onset/offset profiles across all `10` videos (`38` `K` utterances = `22 K_only` + `16 double_review_N_K`), present the full review workbook + tricky cases to `K` for explicit confirmation before setting `K_verified=True` / `human_verified=True`.
   - **Step 5.3 (Overlap IAA, Adjudication & Final `60`-Utterance Receipt):** Record `K`'s confirmed `38/38` annotations, compute `16`-utterance `N`-vs-`K` IAA (`compute_m4_1_annotator_agreement`), adjudicate overlap rows into `ref_text`/`ref_start_sec`/`ref_end_sec` (`human_verified=True` across `60/60 >= 50`), write `m4_1_joint_reference_eval_receipt.json` (plus `khuong_prosody_peer_review.md`), and update `M4.1/README.md` + `milestones/README.md`.
