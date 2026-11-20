# M5.1 Comment Indicator Annotation Guidelines

- **Purpose:** Independently double-annotate up to **300** real pilot comments (minimum **150** required for a quality gate; at least **60** overlapping items double-annotated by both `N` and `K`) collected under `M3.3`.
- **Core Rule:** Label **only observable textual/thread properties**. **Never** label or assert bots, payment, coordinated seeding campaigns, or verified diner identity. Preserve original text verbatim.

## Label Definitions

1. `contact_or_link`
   - Explicit URLs (`http://`, `https://`, `www.`), phone numbers (`0xxxxxxxxx`), Zalo/Telegram/Facebook handles, recruitment pitches (`tuyển ctv`), or sales DMs (`inbox em`, `ib nhận`).
2. `noise_or_empty`
   - Zero lexical content words (emoji-only, punctuation-only, whitespace, or unintelligible character repetition).
3. `observable_duplicate`
   - Near-identical multi-word comment (`>= 5` tokens) repeated across distinct `author_handle` accounts **strictly within the same video thread** (`Jaccard >= 0.72` or clear copy-paste duplicate).
   - **Organic-duplicate exclusion:** Short ordinary diner expressions (`< 5` tokens, e.g., `"ngon quá"`, `"xin địa chỉ"`, `"quán ở đâu"`, `"nhìn hấp dẫn quá"`) and ordinary 5–8 syllable Vietnamese venue/price inquiries (`"cho mình xin địa chỉ"`, `"quán này ở đâu vậy"`, `"cho mình xin địa chỉ quán với/ạ"`) repeated by different users MUST be labeled `no_indicator_observed`, **not** `observable_duplicate`, unless paired with suspicious external contact links.
4. `template_phrase_match`
   - Recognizable verbatim promotional canned template wording shared without personal menu/visit detail.
5. `no_indicator_observed`
   - Normal food/venue/price/service reaction, question, taste opinion, or complaint with none of the observable indicators above. (Still does **not** prove verified real-diner visit!)
6. `unknown_ambiguous`
   - Insufficient context, sarcasm, unclear slang, or borderline partial repetition where reviewers cannot assign a clear class. **Keep `unknown_ambiguous` explicitly; do not force into `no_indicator_observed`.**

## Splitting & Quality Gate

- Partition annotated comments **strictly by `video_id`/thread** (`dev`, `calibration`, `held_out_third`) before any threshold tuning. Never split comments from the same video across train/dev and held-out test.
- Compute Cohen's kappa on double-annotated items, adjudicate disagreements jointly, and evaluate on the frozen `held_out_third`.
- Automated comment filtering in UI/ABSA is unlocked **only** if `N >= 150` real annotated comments pass human sign-off **and** held-out `macro_precision >= 0.85` and `macro_recall >= 0.60` across observable positive indicator classes. Otherwise, keep **`diagnostic_only_without_filtering`** active.
