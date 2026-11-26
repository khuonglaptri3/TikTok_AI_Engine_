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
