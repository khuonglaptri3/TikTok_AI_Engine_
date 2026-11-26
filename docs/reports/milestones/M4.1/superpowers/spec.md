# M4.1 — Timestamp & Prosody CPU Evaluation Specification

- **Task ID:** `M4.1` ([TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md))
- **Status at Authoring:** `IN_PROGRESS` (Technical CPU prosody/invariant extraction, `>= 50`-utterance reference review sheet generation, and evaluator TDD; two-person manual reference annotation and `N` error/reference review remain pending human execution)
- **Contributors:** Nguyễn Việt Nguyên (`N` — CPU pipeline, evaluator, & reference/error reviewer) & Trần Đình Khương (`K` — co-annotator & `M3.G` joint gate completion)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M4.1`, line 104)
- **Branch:** `feat/m4.1-audio-prosody-and-timestamp-eval` (from `main` @ `bde4017f`)

## 1. Scope & Acceptance Rules

1. **Bounded Pilot Audio Scope:**
   - Process ONLY the successfully captured `M3.3` pilot audio (`29` `.mp3` files under `data/raw_incremental/m3_3_pilot_run/batch/audio_64k/`, strictly `<= 60.0` audio minutes).
   - Enforce pilot compute budgets fail-closed: `wall_seconds <= 14,400` (`4` CPU hours) and `peak_rss_mib <= 8,192` (`8 GiB`); exceeding limits triggers sample reduction rather than silent overrun.
2. **Temporal Invariants & Provenance Qualification:**
   - Decode exact media duration (`media_duration_sec`) from each `.mp3` via `ffmpeg` 16kHz PCM (no PyAV `metadata_errors` assumption).
   - Enforce **`0.0 <= start_sec < end_sec <= media_duration_sec`** and 100% `video_id` / `segment_id` source resolvability across all utterances in `fact_voice_segments.parquet`.
   - Normalize Whisper-based utterance timestamps (`whisper_exact` or `audio_derived`) strictly to **`audio_derived`** (estimates, never exact speech timing), keeping interpolated timestamps strictly as **`wps_estimated`**.
3. **Descriptive CPU Prosody (`USD 0`):**
   - Extract per-file (and per-segment where finite/voiced) **`pitch_std`** (Hz standard deviation across voiced frames `70–380 Hz`, normalized autocorrelation `r >= 0.35`, `>= 5` voiced frames required else `None`) and **`energy_cv`** (coefficient of variation of active-frame RMS amplitude, else `None`), strictly finite (no `NaN`/`Inf`).
   - Qualify all prosody outputs explicitly as **descriptive acoustic variation** — never intent, deception, excitement certainty, or undisclosed-sponsorship evidence.
4. **Two-Person Reference Review (`<= 20` min, `>= 50` utterances) & CER/WER/Boundary Gate:**
   - Sample `>= 50` utterances across `<= 20.0` audio minutes of ASR-transcribed pilot videos into a clean annotation sheet (`human_verified = false`) split equally with double-review overlap for `N` and `K` to supply `ref_transcript`, `ref_start_sec`, and `ref_end_sec`.
   - Evaluate **`CER`** and **`WER`** under stated explicit tokenization (`NFC`, lowercased, Unicode punctuation stripped) plus absolute boundary errors (`|pred_start - ref_start|`, `|pred_end - ref_end|`).
   - Gate rule (`precise_playback_allowed`): requires `is_real_human_verified=True`, `evaluated_utterance_count >= 50`, `total_sampled_audio_minutes <= 20.0`, `invariant_pass_rate == 1.0`, `boundary_median_abs_err_sec <= 1.0`, and `boundary_p95_abs_err_sec <= 3.0`; otherwise fail closed (`abstain_precise_playback = True`).

## 2. Phase 2 — Primary-Owner (`K`) Code Review, TDD Hardening, `38`-Utterance Audio Verification & Joint Adjudication (`2026-11-26`)

1. **Adversarial Evaluator Hardening (`packages/prosody/evaluation.py`):**
   - Enforce fail-closed completeness and temporal validity on every `human_verified=True` row: require non-empty normalized `ref_text` and finite `0.0 <= ref_start_sec < ref_end_sec <= audio_duration_sec`; expose `invalid_verified_row_count` and block `precise_playback_allowed` if any `human_verified=True` row is malformed or incomplete.
   - Compute `total_sampled_audio_minutes` across all sampled pool rows (`rows`) rather than only `human_verified=True` rows so leaving videos unverified can never mask a `> 20.0` minute pool overrun.
   - Add edit-operation breakdowns (`word_substitutions`, `word_deletions`, `word_insertions`, `char_substitutions`, `char_deletions`, `char_insertions`) and `compute_m4_1_annotator_agreement(rows)` over `double_review_N_K` rows (`exact_normalized_text_match_rate`, symmetric inter-annotator `WER`/`CER`, boundary median/p95 delta between `N` and `K`, and explicit disagreement records).
2. **Independent `K` `38`-Utterance Audio Verification & Overlap Adjudication:**
   - Independently listen to all `10` pilot `.mp3` clips (`0–19 s` + sample-accurate utterance slices and `10 ms` RMS onset/offset envelopes) blinded to `N_ref_*`, present all `38` `K`-assigned items (`22 K_only` + `16 double_review_N_K`) to contributor `K` for explicit human confirmation, record `K`'s confirmed annotations, compute `16`-item `N`-vs-`K` IAA, adjudicate any differences transparently, and run the final `60`-utterance (`>= 50`) `evaluate_m4_1_reference_set` receipt.
