# M5.2 — Four-Aspect Sentiment & Source-Span Human Annotation Guidelines (`K` & `N`)

- **Task ID:** `M5.2` ([TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md))
- **Specification & Plan:** [spec.md](../superpowers/spec.md), [plan.md](../superpowers/plan.md)
- **Contributors:** Trần Đình Khương (`K`, primary owner) & Nguyễn Việt Nguyên (`N`, independent co-annotator & peer reviewer)
- **Target Scope:** `120`–`200` blinded real pilot text units across `>= 10` videos captured in `M3.3` (`creator_utterance`, `creator_caption`, and `viewer_comment` modalities)

---

## 1. Purpose and Epistemic Scope

`M5.2` evaluates deterministic 4-aspect Vietnamese F&B Aspect-Based Sentiment Analysis (ABSA) with exact character-indexed `source_spans`. Annotators label **only what is observable in the text unit** (`creator_utterance`, `creator_caption`, or `viewer_comment`):

1. **Never infer unmentioned aspects from general praise or restaurant reputation.** Generic statements such as `"Quán đỉnh của chóp!"` or `"Check in 100k views"` leave all 4 aspects as `absent_unknown`.
2. **Never conflate `absent_unknown` with `neutral`.** `absent_unknown` means the aspect is not discussed in the unit (`0` spans); `neutral` means the aspect **is** explicitly discussed with factual, balanced, or hedged/litotes framing (`>= 1` span).
3. **Creator-vs-viewer deltas are strictly `sentiment_discrepancy`.** Even when `>= 3` distinct non-seeding viewer comments overlap a creator-mentioned aspect, any score difference measures an observed text-level sentiment discrepancy—never proof of creator deception, objective food-safety truth, or verified diner consensus.

---

## 2. Unit Identification & Blinded Sheet Format

 Blinding is enforced by [evaluation.py](../../../../../packages/absa/evaluation.py) (`build_m5_2_annotation_pool(..., include_predictions=False)`) and [run_baseline_checks.py](../../../../../pipelines/audit_m5_2_absa/run_baseline_checks.py) (`--mode real_pool`):

- **Collision-free `unit_id` format:**
  - `f"{video_id}::utt::{segment_id}"` — ASR voice segment from `fact_voice_segments.parquet` (`source_kind = "creator_utterance"`).
  - `f"{video_id}::cap"` — video caption from `fact_videos.parquet` (`source_kind = "creator_caption"`).
  - `f"{video_id}::cmt::{comment_id}"` — viewer comment from `fact_comments.parquet` (`source_kind = "viewer_comment"`, preserving unstripped `original_text` when non-blank so leading whitespace offsets match stored bytes).
- **Pool bounds & video coverage:** `120 <= total_units <= 200` across `>= 10` distinct `M3.3` pilot videos, ordered contiguously by `video_id` so annotators see full thread context while labeling each unit independently.
- **Locked system predictions:** System `pred_aspects` and `pred_spans` are written to a separate `*_locked_predictions.jsonl` file and omitted from the human JSONL sheet until both `K_human_verified` and `N_human_verified` are signed off.

---

## 3. Four-Aspect Definitions & Vietnamese False-Positive Guards

Label each unit across all four keys in `ASPECT_NAMES = ("taste", "price", "hygiene", "service")`:

| Aspect | Included Observable Mentions | Excluded False-Positive Traps (`absent_unknown` unless paired with real aspect cue) |
| --- | --- | --- |
| `taste` | Flavor, broth/seasoning, meat/ingredient texture, aroma, freshness, temperature of food/drink (`"nước dùng đậm đà"`, `"thịt bò khô"`, `"hơi mặn"`, `"nguội ngắt"`). | Generic hype without food/flavor reference (`"đỉnh của chóp"`, `"xuất sắc luôn mọi người"` without dish/flavor head); social metrics (`"100k views"`). |
| `price` | Monetary price, bill/portion value, affordability, explicit VND figures (`"giá 45k"`, `"hạt dẻ"`, `"đắt xắt ra miếng"`, `"khẩu phần quá ít so với mức giá 80k"`). | Bean-sprout noun compounds (`"giá đỗ"`, `"giá trụng"`, `"rau giá sống"`); counterfactual wishes (`"giá như quán mở gần nhà"`, `"giá mà biết sớm hơn"`). Note: demonstrative `"Giá như vậy là bình thường"` **is** `price` (`neutral`). |
| `hygiene` | Table/floor/utensil cleanliness, dining space sanitation, ventilation, food-handling cleanliness (`"bàn ghế hơi bẩn"`, `"quán ăn sạch sẽ"`, `"đồ ăn sạch"`, `"thoáng mát"`). | Consumption/depletion idioms (`"ăn sạch cả tô"`, `"húp sạch"`, `"uống sạch"`, `"bán sạch từ sớm"`, `"hết sạch"`). |
| `service` | Staff attitude, ordering/serving speed, attentiveness, owner behavior (`"nhân viên nhiệt tình"`, `"phục vụ quá chậm"`, `"lên món lâu lắm"`, `"chủ quán cọc"`). | Restaurant age/nostalgia (`"quán phở lâu đời"`, `"bán lâu năm"`, `"lâu lắm rồi mới ăn lại"`). |

---

## 4. Four-State Polarity Decision Rules (`VALID_ASPECT_STATES`)

Every `(unit, aspect)` pair receives exactly one state in `("absent_unknown", "negative", "neutral", "positive")`:

1. **`absent_unknown`:** The unit contains no observable mention of the aspect (`0` spans for that aspect).
2. **`positive`:** The aspect is mentioned with net favorable evaluation (`"nước dùng đậm đà"`, `"giá 50k hợp lý"`, `"không gian sạch sẽ"`, `"xứng đáng với giá tiền"`).
3. **`negative`:** The aspect is mentioned with net unfavorable evaluation, including:
   - Direct complaints (`"hơi mặn"`, `"bàn ghế dơ"`, `"phục vụ chậm"`).
   - Negated positive cues (`"thịt bò không ngon"`, `"vệ sinh chưa sạch"`).
   - Negated neutral acceptability phrases (`"thái độ nhân viên không chấp nhận được"`, `"phục vụ không ổn"`, `"giá tiền chưa ổn áp"`).
4. **`neutral`:** The aspect **is** explicitly mentioned, and its net evaluation is factual, middling, softened by litotes, or evenly mixed across clauses in the same unit:
   - Bare factual or middling statements (`"giá 45k một tô"`, `"giá 45k bình thường"`, `"mức giá tầm trung"`).
   - Softened litotes (`"giá không quá đắt"`, `"phục vụ cũng không tệ"`).
   - Opposing clauses on the **same** aspect within one unit (`"Nước dùng rất thơm nhưng vị lại hơi mặn"` -> two `taste` spans `+1` and `-1`, unit-level `taste = "neutral"`).

---

## 5. Exact Unicode `NFC` Character-Span Rules (`source_spans`)

Every aspect labeled `positive`, `neutral`, or `negative` in a unit must be backed by `>= 1` character-indexed span satisfying the strict verifier in `audit_source_span_validity`:

1. **Unicode normalization:** Normalize `unit["text"]` via `unicodedata.normalize("NFC", text)` **without** calling `.strip()` on the unit text. Leading spaces or tabs in `viewer_comment` (`CommentRecord.original_text`) shift `start_char` and `end_char` accordingly.
2. **Exact slice equality:** `0 <= start_char < end_char <= len(nfc_text)`, `span_text` must be non-blank (`bool(span_text.strip())`), have no leading/trailing whitespace, and satisfy `nfc_text[start_char:end_char] == span_text` character-for-character.
3. **Multi-aspect clause partitioning:** When a sentence evaluates multiple aspects across contrastive (`nhưng`, `tuy nhiên`, `, mà`) or coordinated (`,`, `và`, `còn`) clauses—for example, `"Nước dùng hơi mặn nhưng giá 45k bình thường"`—mark separate minimal clause spans for each aspect (`"Nước dùng hơi mặn"` for `taste` and `"giá 45k bình thường"` for `price`) so local polarity cues do not bleed across aspects.

---

## 6. Double-Annotation, Adjudication & Acceptance Gate Protocol

1. **Export blinded pool (`M3.3` prerequisite):**
   ```bash
   python3 -m pipelines.audit_m5_2_absa.run_baseline_checks \
     --mode real_pool \
     --corpus-dir data/corpus/<m3_3_snapshot_id> \
     --output-pool data/annotations/m5_2_pilot_pool.jsonl \
     --output-locked-predictions data/annotations/m5_2_pilot_locked_predictions.jsonl \
     --max-units 180 \
     --double-overlap 50
   ```
2. **Independent annotation (`K` & `N`):**
   - Units with `review_assignment == "double_review_N_K"` (`>= 50` units balanced across videos) are labeled independently by both `K` (`K_aspects`, `K_spans`, `K_human_verified = true`) and `N` (`N_aspects`, `N_spans`, `N_human_verified = true`) before viewing each other's labels or `m5_2_pilot_locked_predictions.jsonl`.
   - Single-assigned units (`N_only`, `K_only`) are labeled by their assigned contributor and spot-checked during adjudication.
3. **IAA & Adjudication:**
   - Compute pre-adjudication agreement via `compute_m5_2_annotator_agreement` (binary presence raw agreement + Cohen's $\kappa$, 4-state raw agreement + Cohen's $\kappa$, and per-aspect breakdown).
   - Resolve disagreements jointly into `adjudicated_aspects` and `adjudicated_spans`, recording brief rationale in `K_note` / `N_note`.
4. **Video-disjoint evaluation & `M5.2` pilot gate (`evaluate_m5_2_aspect_sentiment`):**
   - Partition annotated units strictly by `video_id` (`split_units_by_video(..., dev_ratio=0.5, seed=42)`, `0` video overlap between `dev` and `held_out`).
   - `m5_2_pilot_gate_eligible` turns `True` **iff** all conditions hold simultaneously on the `held_out` split:
     - `is_real_pilot_data is True` and `human_signoff_complete is True`;
     - `120 <= total_annotated_units <= 200` across `>= 10` unique real pilot videos (`>= 40` held-out units);
     - Held-out `aspect_detection_macro_f1 >= 0.65` (with 300-resample video-cluster bootstrap 95% CI);
     - Held-out `observed_sentiment_macro_f1 >= 0.60` across 3 polarities (`positive`, `neutral`, `negative`) on gold-observed `(unit, aspect)` pairs (treating `pred == "absent_unknown"` on a gold-observed aspect as a missed recall);
     - Audited `source_spans` exact `NFC` slice validity `>= 95%` (`meets_95pct_gate is True`).
