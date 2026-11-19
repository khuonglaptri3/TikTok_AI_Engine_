# M2.2 — Blinded Pooled Relevance Judgment Guidelines (`v2_pilot`)

## 1. Blinded Evaluation Setup
- Candidates in `blinded_pool.csv` are the deduplicated union of top-10 results from `bm25` (`rerank=False`) and `bm25_reranked` (`rerank=True`) over `data/corpus/20261118_taxonomy_fix_v1` + `artifacts/indexes/bm25-v3`, shuffled deterministically per query (`seed=20261119`) with all ranks, scores, and system origins stripped prior to judging.
- Annotators inspect **only** the query (`query`, `filters`, `phenomenon`) and the candidate video's observed fields (`city_norm`, `district_norm`, `video_format`, `food_category`, `poi_name`, `caption`, `transcript`). Machine-inferred `dishes` tags alone do **not** establish relevance when `caption` and `transcript` are about a different food or non-culinary topic.

## 2. Ternary Relevance Scale (`1` / `0` / `U`)
- **`1` (Relevant):**
  - The video's spoken `transcript` and/or `caption` genuinely features, reviews, mukbangs, or teaches the requested dish, cuisine, or dining occasion.
  - **Synonyms (`synonym`):** Regional/colloquial equivalents count as `1` (e.g., `tàu hũ` = `đậu hũ` / `tào phớ`; `Sài Gòn` = `Hồ Chí Minh`; `nước lèo` = `nước dùng`; `chả giò` = `nem rán`; `bánh flan` = `caramen`; `xiên bẩn` = `cá viên chiên` / street skewers; `ăn kiêng` / `ít calo` = `healthy` / `eat clean`).
  - **Unicode (`unicode_nfd`):** Judge semantic relevance identically regardless of decomposed `NFD` vs precomposed `NFC` query encoding.
  - **Negation (`negation`):** If the query excludes an ingredient/attribute (e.g., `không mắm tôm`, `không cay`, `không trà sữa`, `không hành`, `không dầu mỡ`), mark `1` **only** if the video satisfies the positive dish/drink request **and** does not center on or heavily promote the excluded ingredient/attribute (unless explicitly offering a non-excluded alternative). If the video heavily features `"siêu cay"` or `"mắm tôm đậm đặc"` when `"không cay"` or `"không mắm tôm"` was requested, mark `0`.
  - **Filters (`filtered`):** When `filters` specifies `city_norm`, `video_format`, or `food_category`, the candidate must satisfy the requested culinary topic **and** be consistent with the filter (`city_norm` must match when specified; cooking tutorial queries with `video_format="Hướng dẫn nấu ăn"` must actually explain preparation/ingredients rather than pure restaurant dining).
- **`0` (Non-Relevant):**
  - Different dish/topic (e.g., `xôi thịt kho` for `bún đậu`), non-F&B lifestyle/tech vlog, background song lyrics without relevant food content, wrong city on a city-filtered query, or direct violation of a negated constraint.
- **`U` (Uncertain / Insufficient Text Evidence):**
  - Transcript/caption is too fragmentary, music-only, or ambiguous on a required constraint (e.g., cannot tell whether a soup contains a negated garnish when the dish matches) to verify `1` vs `0`. `U` items are tracked in completeness/uncertainty statistics and are **not** counted as verified positives (`1`).

## 3. Provenance & Human Sign-Off Rule
- Initial blinded passes (`K_rel_draft`, `N_rel_draft`) and `adjudicated_rel` are recorded as AI-assisted blinded draft judgments (`K_human_verified=False`, `N_human_verified=False`) so human contributors Trần Đình Khương (`K`) and Nguyễn Việt Nguyên (`N`) can audit, override, and sign off every row in `data/evaluation/v2_pilot/blinded_pool.csv` before closing `M2.2`.
