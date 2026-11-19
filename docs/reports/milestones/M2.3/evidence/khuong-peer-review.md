# M2.3 — Peer Review & 30-Draft Full-Source Claim Audit (`K`)

- **Task ID:** `M2.3`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer:** Trần Đình Khương (`K`)
- **Review Date:** `2026-11-19` (`Asia/Ho_Chi_Minh`)
- **Evaluated Corpus & Index:** `data/corpus/20261118_taxonomy_fix_v1` + `artifacts/indexes/bm25-v3`
- **Review Verdict:** `CONDITIONAL_PASS_PENDING_N_HUMAN_CLAIM_AUDIT` (`K`'s code review, TDD regression fixes, `15` held-out briefs, and `30`-draft `K`-side full-transcript claim-entailment audit are complete; `N`'s human claim-entailment columns across the `30` drafts remain blank for independent annotation before `M2.3` can transition to `COMPLETE`).

---

## 1. Independent Code Review of `N`'s Baseline Implementation

### Verified Strengths in `N`'s `M2.3` Deliverables
1. **Bounded provider budget & deadline enforcement (`packages/llm/clients/gemini.py`):**
   - Correctly enforces `turn_calls_used < max_llm_calls_per_turn` (`<= 2` calls/turn), configures `HttpOptions(timeout=timeout_ms)` from `llm_deadline_seconds`, redacts API keys/exception strings, and maps missing keys, timeouts, and quota errors to `ProviderKeyMissingError` / `QuotaBlockedError` with zero fallback to paid models (`USD 0`).
2. **Deterministic timeline & source-membership guardrails (`packages/llm/guardrails/verifier.py`):**
   - Strips foreign/hallucinated `cited_video_ids`, reports `valid_citations_ratio` (membership) separately from `citation_coverage_ratio` (beat coverage), enforces `abs(delta_sec) <= max(2.0, target_duration_sec * 0.05)`, and preserves `grounding_verified = False` so structural pass is never misrepresented as semantic entailment.
3. **Immutable historical baseline preservation:**
   - `N`'s original 15-draft baseline (`docs/reports/milestones/M2.3/evidence/nguyen_15_drafts_audit.csv`, SHA256 `70640bc8471c5061599df51f282f5b1c8922c8c67b05b2f5cea4a1fac4b41f6a`) was preserved untouched on disk.

### Defects Discovered & Fixed by `K` via Three TDD Cycles (`RED -> GREEN`)
Inspection of `packages/script_engine/service.py` and `N`'s baseline `nguyen_15_drafts_audit.csv` revealed seven concrete defects that caused location fabrication, mid-sentence truncation, retrieval starvation on `20261118_taxonomy_fix_v1`, dish hijacking, and non-culinary quote selection. All seven were resolved via TDD in `tests/unit/test_offline_draft.py` (`20` tests) + `tests/unit/test_script_guardrails.py` (`13` tests, `33/33` passing):

1. **Cross-city location fabrication & dish-origin city confusion:**
   - *Problem:* `_build_offline_grounded_draft` fell back to `c0.city_norm` (`"Đà Nẵng"`) or `"tại Địa Phương"` when a brief had no city (`n07` Mukbang), and `_infer_effective_filters` treated dish-origin names (`"bún bò Huế tại nhà"`, `"chuẩn vị Hà Nội"`) as venue filters.
   - *Fix:* Stripped `_DISH_ORIGIN_CITY_PHRASES` prior to location inference and restricted draft location clauses strictly to `effective_filters.city_norm` when present.
2. **Dish-focus hijacking from `c0.dishes`:**
   - *Problem:* When `extract_dishes_from_text(brief)` had no match (e.g., `"canh chua cá hồi"` or `"quán ăn gia đình món Việt truyền thống"`), falling back to `c0.dishes[:2]` injected unrelated dishes (`"vây cá hồi chiên giòn, lòng heo luộc"`, `"gỏi tôm thịt"`, `"kẹo mạch nha dâu tây"`) into the creator's planning lines.
   - *Fix:* Removed `c0.dishes` fallback; `dish_focus` uses only extracted brief dishes or the non-generic `food_category` / `"món ăn theo chủ đề đã chọn"`.
3. **Soft heuristic pre-filter starvation in `GroundedScriptEngine.generate()`:**
   - *Problem:* Passing auto-inferred soft facets (`price_tier`, `occasion`, `duration_bucket`, `food_category`, `video_format`) into `HybridRetrievalService.search()` locked `_resolve_candidate_pool` onto small `>= 5` generic pools that lacked the specific dish anchor, starving `n02`, `n11`, `k01`, and `k11` to `0` results on `20261118_taxonomy_fix_v1`.
   - *Fix:* Added `_build_retrieval_filters(explicit, effective)` so `analytics.compute_benchmark` still uses full `effective_filters`, while `retrieval.search` keeps 100% of explicit caller `request.filters` plus inferred geographic scope (`city_norm`, `region`) strict and lets `BM25 + query_intent + bge-reranker-v2-m3` rank dish matches across the city/corpus pool.
4. **Mid-sentence word-slice truncation & `wps`-sensitive timing drift:**
   - *Problem:* Word slicing (`words[:budget]`) truncated `35s` drafts mid-clause (`n10`, `n11`), while fixed 3-sentence ladders undershot `50–55s` high-`wps` slices (`n03`, `n04`, `n09`) and overshot slow-`wps` slices (`k10`).
   - *Fix:* Replaced word slicing with complete-sentence combinatorial selection (`beat_compact` + 5-sentence `beat_sentence_ladder`) optimizing exact guardrail duration against `target_duration_sec` and `benchmark.median_word_per_second` (`30/30` `timing_valid`, `0` truncated sentences).
5. **Music-summary, prompt-placeholder, and trivial sign-off excerpt filtering:**
   - *Problem:* Legacy Gemini audio summaries (`"Bài hát..."`, `"Ca khúc..."`, `"Âm nhạc tạo..."`, `"[Please insert the Vietnamese transcript here]"`) and `< 3`-word sign-off `cta_text`s (`"Bye bye."`, `"Haha."`) were selected as `Nguồn cũ:` quotes even when culinary `body_beats` existed on the same card.
   - *Fix:* Added `_NON_CULINARY_SPAN_MARKERS` and `_TRIVIAL_SIGNOFF_RE` in `_is_usable_culinary_span` so beats skip marked music/placeholder/sign-off spans and fall back to culinary spans.

---

## 2. 30-Draft Offline Run & `K`'s Full-Transcript Claim-Entailment Audit

`K` authored `15` disjoint Vietnamese F&B briefs (`k01..k15` in [khuong_15_queries.jsonl](khuong_15_queries.jsonl)) and executed `GroundedScriptEngine` in `offline_grounded` mode (`0` LLM calls) across all `30` briefs (`n01..n15` + `k01..k15`) via [run_m2_3_30_drafts_audit.py](run_m2_3_30_drafts_audit.py). `K` then read the full untruncated `caption`, `hook_text`, `body_beats`, `cta_text`, and `transcript` of every cited video across all `30` drafts (`120` beats):

| Metric (`30` drafts = `15` `N` + `15` `K`, `120` beats) | Automated / `K`-Audited Result | Acceptance Target | Status |
| --- | --- | --- | --- |
| Provider / LLM calls (`offline_grounded`) | `0` (`USD 0`) | `0` offline calls | PASS |
| Fabricated / foreign `video_id` count | `0 / 120` (`0.0%`) | `0` fabricated IDs | PASS |
| Structural `valid_citations_ratio == 1.0` | `30 / 30` (`100.0%`) | Reported separately | PASS |
| Structural `citation_coverage_ratio == 1.0` | `30 / 30` (`100.0%`) | `>= 90%` | PASS |
| Timeline tolerance `±max(2s, 5%)` (`timing_valid`) | `30 / 30` (`100.0%`) | Within `max(2s, 5%)` | PASS |
| Literal verbatim presence of `Nguồn cũ: "..."` in cited record | `120 / 120` (`100.0%`) | — | Verified |
| **`K`-audited culinary claim support (`K_supported_factual_claims / K_total_factual_claims`)** | **`108 / 120` (`90.00%`)** (`54/60` on `N`, `54/60` on `K`) | **`>= 90%`** | **Met on `K` side (`N` pending)** |
| **`K` strict whole-draft editorial pass (`K_review_ok`)** | **`20 / 30` (`66.67%`)** | Diagnostic quality indicator | Recorded honestly |

### Remaining Semantic Limitations Surfaced by `K`'s Full-Transcript Audit
Even with `100%` structural pass and `100%` verbatim substring presence, `K`'s manual reading identified four real corpus/retrieval limitations (detailed in [khuong_c1_c5_adjudication.json](khuong_c1_c5_adjudication.json) and [khuong_30_drafts_claim_audit.jsonl](khuong_30_drafts_claim_audit.jsonl)):

1. **Unmarked song lyrics / poetic music summaries in corpus (`C1` — `9 / 120` beats across `n01, n04, k02, k05, k06, k08`):**
   - Six cited videos carry food captions (`#ocbinhthanh`, `#banhcanhcuaquan3`, `#suonnuongmatong`, etc.) while their ASR `transcript` / `body_beats` capture background music without using explicit `"bài hát"` keywords (`7357939713132580103`, `7406631345100721425`, `7421397039306624276`, `7334299969131793672`, `7419586889218395399`, `7444556348412415248`). All `9` beats were strictly scored **Unsupported** by `K`.
2. **Upstream corpus location mislabel & themed-vibe venue (`C2` — `3 / 120` beats across `n05, n11`):**
   - In `n11` Beat 3, `7387712842968943880` is labeled `city_norm = "hà nội"` in `fact_videos.parquet`, whereas its full transcript explicitly locates the buffet at `56 Thiên Chủ, phường Bình Thọ, thành phố Thủ Đức` (TP.HCM). In `n05` Beats 1–2, `7306523711614487810` describes a `"vibe Đà Lạt"` cafe rather than a verified Đà Lạt address. All `3` beats were strictly scored **Unsupported** by `K`.
3. **Corpus ingredient / secondary-dish sparsity (`C3` — `k12, n07, n12, n15`):**
   - For `k12` (*canh chua cá hồi*), the corpus lacks a salmon sour-soup tutorial, so retrieval surfaces home-cooked sour fish soup recipes using `cá chuồn`, `cá ngát`, and `cá lóc` (the draft text honestly states `"Cơm & Bữa chính"` rather than claiming salmon, and `k12` is marked `K_review_ok = False`).
4. **Intra-city district fallback & foreign convenience store (`C4` — `n14, n01, k01, k10, k14`):**
   - Because `district_norm` is sparsely populated in historical metadata, retrieval enforces `city_norm` strictly while allowing neighboring districts within the same city when exact-district transcripts are absent; `n14` matches a convenience-store snack haul filmed in China (`7447910275665120520`, marked `K_review_ok = False`).

---

## 3. Handoff to `N` to Close `M2.3`
1. Independently audit the `30` drafts in [combined_30_drafts_audit.csv](combined_30_drafts_audit.csv) against [combined_30_drafts_detailed.jsonl](combined_30_drafts_detailed.jsonl) and populate `N_total_factual_claims`, `N_supported_factual_claims`, and `N_citation_coverage_ok` (left untouched/blank by `K`).
2. Review `K`'s TDD fixes in `packages/script_engine/service.py` and `tests/unit/test_offline_draft.py`, adjudicate any claim-level disagreements between `K` and `N`, and update `M2.3` status for Gate `G2` (`M2.G`).
