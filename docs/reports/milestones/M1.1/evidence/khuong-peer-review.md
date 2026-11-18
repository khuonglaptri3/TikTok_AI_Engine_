# M1.1 — Blinded 30-Record `K_*` Audit & Peer Review by Trần Đình Khương (`K`)

- **Review date:** 2026-11-18 (Asia/Saigon)
- **Task ID:** `M1.1`
- **Primary Owner:** Nguyễn Việt Nguyên (`N`)
- **Peer Reviewer & Overlap Annotator:** Trần Đình Khương (`K`)
- **Reviewed merge:** `origin/feat/m1.1-taxonomy-audit` (`f3dd0a84`) merged into local `main`

## 1. Review Verdict

1. **Taxonomy & Disambiguation Code Fixes (`packages/taxonomy/`, `pipelines/`):** **PASS.** Verified longest-first word-boundary district matching (`quận 1` vs. `quận 10..12`), `poi_name` city fallback, English/unaccented city/district aliases, word-boundary dish/category regexes (eliminating substring `"ốc"` collisions), and neutral `[]` unknown occasion handling (`7/7` unit tests in `test_taxonomy_and_corpus.py` + full suite `PASS`).
2. **Lineage, Safe Ratios & Qualified Data Card:** **PASS.** Per-column lineage across `49` video and `15` creator fields ([field_coverage.csv](field_coverage.csv), [field_lineage_and_coverage.json](field_lineage_and_coverage.json)) and [tiktok_fnb_corpus_v1.md](../../../../data-cards/tiktok_fnb_corpus_v1.md) accurately state denominators, safe zero-division guards (`duration_sec == 0` on `5,646` rows -> `wps = 0.0`; `play_count == 0` on `1` row -> `er = 0.0`), and explicit non-ground-truth / non-attendance caveats.
3. **30-Record Overlap Annotation (`K_*` Manual Human vs. `N_*` `gemini-3.1-flash-lite`):** **COMPLETED BY `K`; HUMAN `N_*` CONFIRMATION OPEN BEFORE `M1.G` (`G1`).**
   - `K` manually annotated all `30` `shared_K_N` records (`sample_no = 1..30`) blinded to `N_*` values, populated `K_*` in [audit_sample_120.csv](audit_sample_120.csv), and computed exact agreement in [khuong_m1_1_review_and_agreement.json](khuong_m1_1_review_and_agreement.json).
   - Because `N_*` was populated via `gemini-3.1-flash-lite` rather than manual human coding by `N`, `M1.1` remains `IN_PROGRESS` until `N` performs human confirmation/adjudication on `N_*` prior to `M1.G` (`G1`).

## 2. Overlap Agreement & Sampled Error Rates (`n = 30` `shared_K_N`)

| Dimension | `K` Human Counts (`1` / `0` / `U`) | `K` Human Error Rate (`0 / 30`) | `N_*` (`gemini-3.1-flash-lite`) Counts | Raw Agreement (`n=30`) | Cohen's $\kappa$ | Interpretation |
| --- | --- | --- | --- | ---: | ---: | --- |
| `city_correct` | `20` / `10` / `0` | `33.33%` (`10/30` missed explicit POI/caption city) | `21` / `9` / `0` | `96.67%` (`29/30`) | `0.9231` | Near-perfect agreement; sole diff `#5` (`poi_name="Ho Chi Minh City"` missed by LLM). |
| `dishes_false_positive` | `5` (`FP=1`) / `25` (`FP=0`) / `0` | `16.67%` (`5/30` rows with spurious dish tags) | `6` (`FP=1`) / `24` (`FP=0`) / `0` | `90.00%` (`27/30`) | `0.6667` | Substantial agreement; confirms `"ốc"` substring bug (`#3` `dốc`, `#11` `Hát đốc`, `#21` `#mocviquan`, `#29` `Hàn Quốc`). |
| `format_correct` | `20` / `9` / `1` | `30.00%` (`9/30` wrong format, `1` `U`) | `29` / `1` / `0` | `70.00%` (`21/30`) | `0.1318` | LLM leniency bias: `gemini-3.1-flash-lite` marked `29/30` correct, missing restaurant visits labeled `Review món ăn` (`#8,#10,#16,#17`) and an out-of-domain Samsung phone vlog (`#25`). |
| `category_correct` | `17` / `13` / `0` | `43.33%` (`13/30` wrong/over-general category) | `22` / `8` / `0` | `63.33%` (`19/30`) | `0.2180` | Moderate-low agreement: human `K` caught additional lexical collisions (`#24` `cắt sợi` -> `Món nước & Sợi`, `#1` `beefsteak`, `#6` `#banhmi`). |

## 3. Additional Real-Data Findings Logged for Downstream Tasks

1. **Word-collision outside `"ốc"` (`#24`):** `"cắt sợi sợi nhỏ"` triggered `"sợi"` -> `Món nước & Sợi` on a salad recipe (`Gỏi chả bò dưa leo`).
2. **Non-F&B brand posts on F&B channels (`#25`):** Tracked F&B creators occasionally upload tech/lifestyle sponsor vlogs (`Samsung Galaxy A56/A36`) that remain in the creator-centric historical cohort.
3. **Background music lyrics in historical transcripts (`#28`):** Transcript contains song lyrics (`"Trong một ai như anh biết rõ gu nhạc em thích..."`), making `hook_text` / `cta_text` unusable for spoken culinary structure.
