# M1.1 — Human Annotation Guidelines (120-Record Stratified Taxonomy Audit)

- **Sample file:** `audit_sample_120.csv` (`120` videos stratified across `city_bucket × food_category × has_transcript`)
- **Split:**
  - `sample_no` `1–30` (`annotator_split = shared_K_N`): Annotated **independently** by both Nguyễn (`N`) and Khương (`K`) without viewing each other's labels first; used to compute inter-annotator agreement and resolve disagreements.
  - `sample_no` `31–120` (`annotator_split = N_primary`): Annotated by Nguyễn (`N`) and reviewed by Khương (`K`).

## Column Coding Rules (`1` = correct/acceptable, `0` = error, `U` = cannot tell from text/POI)

1. **`city_correct` (`1` / `0` / `U`):**
   - Look only at `caption`, `poi_name`, `poi_address`, `poi_city`, and `transcript_excerpt`.
   - Mark `1` if `city_norm` matches explicit evidence (or `city_norm` is empty when no city is stated).
   - Mark `0` if `city_norm` is wrong (e.g., dish-origin city confusion) OR an explicit Vietnamese city/district in `poi_name`/`poi_address`/`caption` was missed (`unknown`).
   - Do **not** treat a platform POI tag as proof that the creator physically visited the restaurant.
2. **`format_correct` (`1` / `0` / `U`):**
   - Compare `video_format` against `caption`, `poi_name`, `transcript_excerpt` (`Review quán ăn`, `Review món ăn`, `Review sản phẩm ăn uống`, `Hướng dẫn nấu ăn`, `Mukbang`).
3. **`category_correct` (`1` / `0` / `U`):**
   - Check if `food_category` accurately reflects the main dish/subject; mark `0` if a clearly identifiable dish fell into `Ẩm thực Tổng hợp` or the wrong food category.
4. **`dishes_false_positive` (`0` = no false dish, `1` = contains spurious dish token, `U`):**
   - Mark `1` when `dishes` contains substring artifacts (e.g., `ốc` triggered by `Trung Quốc` / `tốc độ`) or unrelated dishes not present in the video text.
5. **`price_correct` (`1` / `0` / `U`) & `occasion_correct` (`1` / `0` / `U`):**
   - Mark `0` if `price_tier` misreads a non-price number as price or if `occasions` assigns a specific occasion (e.g. `an_vat_xe_chieu`) when no occasion evidence exists.
6. **`anatomy_usable` (`1` / `0` / `NA`):**
   - For `has_transcript = True` only (`NA` when `has_transcript = False`): mark `1` if `hook_text` and `cta_text` cleanly reflect opening/closing text without garbled/refusal artifacts.
