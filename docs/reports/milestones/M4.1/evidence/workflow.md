# M4.1 — Workflow Provenance & Verification Ledger

- **Date:** 2026-11-23 (Asia/Ho_Chi_Minh)
- **Task ID:** `M4.1` (Timestamp & prosody CPU evaluation)
- **Branch:** `feat/m4.1-audio-prosody-and-timestamp-eval` (branched from `main` @ `bde4017f`)
- **Contributors:** Nguyễn Việt Nguyên (`N`, CPU prosody/invariant baseline, evaluator TDD & reference pool) · Trần Đình Khương (`K`, co-annotator & `M3.G` gate owner)
- **Spec & Plan:** [spec.md](../superpowers/spec.md), [plan.md](../superpowers/plan.md)

## Execution & TDD Log

1. **Superpowers planning (`AGENTS.md` §7):** Authored [spec.md](../superpowers/spec.md) and [plan.md](../superpowers/plan.md) on branch `feat/m4.1-audio-prosody-and-timestamp-eval` before writing code or tests.
2. **TDD RED (`tests/unit/test_m4_1_prosody_and_timestamps.py`):** Ran `.venv/bin/python -m pytest tests/unit/test_m4_1_prosody_and_timestamps.py -v` prior to implementing `packages/prosody` -> `4 failed in 0.34s` (`ModuleNotFoundError: No module named 'packages.prosody'`).
3. **Implementation (`packages/prosody/`, `packages/data_contracts/multimodal.py`, `pipelines/audit_m4_1_audio/`):**
   - Extended `VoiceSegmentRecord.timestamp_source` to accept `"audio_derived"` alongside legacy `"whisper_exact"` (preserving `M3.1` tests) and `"wps_estimated"`.
   - Implemented `decode_audio_pcm_16k`, `extract_prosody_features` (`pitch_std` Hz + RMS `energy_cv` + `None` on silence), `normalize_timestamp_source`, and `audit_temporal_invariants` (`0 <= start < end <= media_duration`) in `packages/prosody/extractor.py`.
   - Implemented explicit `TOKENIZATION_SPEC`, `tokenize_vi_words`, `tokenize_vi_chars`, `compute_levenshtein_distance`, `evaluate_m4_1_reference_set`, and `build_m4_1_reference_pool` in `packages/prosody/evaluation.py`.
   - Implemented bounded pilot runner `pipelines/audit_m4_1_audio/run_m4_1_pilot.py` enforcing `<= 60` audio minutes, `<= 4` CPU hours, `<= 8 GiB` peak RSS, `<= 20` sampled audio minutes, `>= 50` reference utterances, and relative receipt paths.
4. **Live CPU Pilot Audit Execution (`m3_3_pilot_snapshot_v1` + `29` `.mp3` files):**
   - Executed `.venv/bin/python -m pipelines.audit_m4_1_audio.run_m4_1_pilot` -> processed `29` `.mp3` files (`46.875` min `<= 60.0`, `22,524,055` B) in `25.331 s` (`RTF=0.009`, `peak_rss_mib=240.14 MiB`), audited all `436/436` `fact_voice_segments.parquet` utterances (`100%` `0 <= start < end <= media_duration`, all labeled `"audio_derived"`), computed descriptive prosody (`29/29` videos, `436/436` utterances finite), and exported blinded `60`-utterance sheet [m4_1_utterance_review_sheet.jsonl](m4_1_utterance_review_sheet.jsonl) across `16.752` min (`16 double_review_N_K`, `22 N_only`, `22 K_only`, `human_verified=false`) alongside [m4_1_audio_pilot_receipt.json](m4_1_audio_pilot_receipt.json) (`precise_playback_allowed=false`, `abstain_precise_playback=true`).
5. **Final Verification After Last Code Edit (`packages/prosody/evaluation.py`):** Re-ran full `pytest`, `ruff`, Linux + `win32` `mypy`, `check_secrets.py`, and relative link checks (recorded in [../README.md](../README.md)).
6. **Contributor `N` `38/38` Audio & Reference Verification (`2026-11-23`):** Audited all `10` trimmed `.mp3` pilot clips plus word-level PCM alignments; after explicit confirmation by `N`, recorded `N`'s `38/38` verified annotations (`22` `N_only` `human_verified=true` + `16` `double_review_N_K` `N_verified=true` with `K` fields preserved untouched at `false`) in [m4_1_utterance_review_sheet.jsonl](m4_1_utterance_review_sheet.jsonl) and logged preliminary `N` metrics (`WER=0.3042`, `CER=0.1770`, `median=0.08 s`, `p95=0.255 s`, fail-closed `precise_playback_allowed=false`) in [m4_1_n_reference_eval_receipt.json](m4_1_n_reference_eval_receipt.json).
