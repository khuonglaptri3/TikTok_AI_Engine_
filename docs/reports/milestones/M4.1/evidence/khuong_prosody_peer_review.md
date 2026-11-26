# M4.1 — Contributor `K` Reciprocal Code Review & Acoustic Error Analysis

- **Reviewer & Co-Annotator:** Trần Đình Khương (`K`)
- **Review Date:** 2026-11-26 (Asia/Ho_Chi_Minh)
- **Reviewed Scope:** `packages/prosody/{extractor.py, evaluation.py, __init__.py}`, `pipelines/audit_m4_1_audio/run_m4_1_pilot.py`, `tests/unit/test_m4_1_prosody_and_timestamps.py`, [m4_1_audio_pilot_receipt.json](m4_1_audio_pilot_receipt.json), and [m4_1_utterance_review_sheet.jsonl](m4_1_utterance_review_sheet.jsonl)

## 1. Code & Evaluator Audit Findings (Resolved via TDD `RED -> GREEN`)

1. **Fail-Closed Validation on `human_verified=True` Rows (`packages/prosody/evaluation.py`):**
   - *Finding:* `evaluate_m4_1_reference_set` previously counted any row with `human_verified=True` toward `evaluated_utterance_count >= 50` even if `ref_text` was empty, `ref_start_sec`/`ref_end_sec` was `None`, or `ref_end_sec > audio_duration_sec`.
   - *Resolution:* Added strict row-level validation requiring non-empty normalized `ref_text` and finite `0.0 <= ref_start_sec < ref_end_sec <= audio_duration_sec`, exposing `invalid_verified_row_count` and blocking `precise_playback_allowed` if `invalid_verified_row_count > 0`.
2. **Full-Pool `20.0`-Minute Sampling Ceiling (`packages/prosody/evaluation.py`):**
   - *Finding:* `total_sampled_audio_minutes` previously summed `audio_duration_sec` only across `human_verified=True` rows rather than all sampled pool rows, meaning leaving videos unverified could mask an oversized (`> 20.0` min) pool.
   - *Resolution:* Computed `pool_video_audio_sec` across all `rows` in the pool (`pool_unique_video_count = 10`, `total_sampled_audio_minutes = 16.752 <= 20.0`).
3. **Edit Breakdown & `N`-vs-`K` Inter-Annotator Agreement (`compute_m4_1_annotator_agreement`):**
   - *Resolution:* Added word/character substitution, deletion, and insertion counts (`S/D/I`) and implemented `compute_m4_1_annotator_agreement` over the `16` `double_review_N_K` utterances, covered by `test_m4_1_k_review_strict_verified_bounds_pool_cap_and_iaa` (`6/6` passing in [test_m4_1_prosody_and_timestamps.py](../../../../../tests/unit/test_m4_1_prosody_and_timestamps.py)).

## 2. Acoustic Error Taxonomy on Real Vietnamese F&B Speech (`faster-whisper/small-cpu-int8`)

Across the `53` strictly agreed reference utterances (`551` reference words: `119` substitutions, `27` deletions, `1` insertion; `WER = 0.2668`, `CER = 0.1689`) and `16` double-reviewed utterances:

- **Price & Polarity Hallucinations (High Downstream Impact):**
  - `7710143263436508417_s005`: Rapid spoken `"40 50 nghìn một cái bánh"` (`40–50K/lá`) was transcribed as `"450k 1 bắn"` (10x price inflation).
  - `7710143263436508417_s004`: `"cực cao cấp"` was transcribed as `"cực cao thấp"` (polarity inversion).
- **Southern Vietnamese Street-Food Phonetics & Dish Names:**
  - `"lột"` -> `"lộp"` (`7710150153201536262`), `"vú sữa dầm"` -> `"phú sử dạm"` / `"suy dạm"` (`7710927418533399815`), `"tô bún bò sườn sụn"` -> `"tố bún bò sừng sùng"` (`7710598047721458945`), `"Khoai tây trứng muối"` -> `"Hoài Tây chín muối"` (`7710799156024986887`).
- **Inverse Text Normalization (`ITN`) Formatting (`~2.2%` WER share):**
  - Whisper formats spoken `"19 ngàn"` / `"300 nghìn"` / `"một"` as `"19k"` / `"300k"` / `"1"`. Normalizing spoken numerals/currency reduces `WER` from `0.2668` to **`0.2450`** and `CER` from `0.1689` to **`0.1492`**.
- **Utterance Boundary Stability (`PASS`):**
  - Despite lexical homophones on rapid colloquial Vietnamese, Whisper segment boundaries closely track acoustic speech onsets/offsets (`median = 0.06 s <= 1.0 s`, `p95 = 0.20 s <= 3.0 s` across `106` boundaries; `N`-vs-`K` inter-annotator boundary median diff = `0.04 s`, `p95 = 0.158 s`), qualifying `audio_derived` timestamps as bounded playback estimates (`never exact word-level speech timing`).
