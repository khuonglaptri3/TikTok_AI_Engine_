# M0.1 — Legacy Repository Audit, Secret Sanitization & Gold RAG Baseline

- Status: COMPLETE
- Execution date: 2026-11-16 (Asia/Ho_Chi_Minh)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M0.1`–`M3.2` baseline initialization)
- Repository version: `main` (`khuonglaptri3/TikTok_AI_Engine_`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

The legacy `21KHDL-TikTok-Analytics` coursework repository was audited, sanitized of all 149 hardcoded API keys, and restructured into the SenticRAG-aligned `TikTok_AI_Engine_` monorepo while preserving 100% of the `1.50 GB` (`37,840` files) local dataset untouched. Historical assets were unified into an immutable SHA256-verified Gold Parquet snapshot (`70,996` videos, `264` creators, `23,448` recovered official TikTok GPS POIs, and `21,748` clean Vietnamese transcripts), powering a sub-25ms Vietnamese NFC BM25 + Reranking engine (`Recall@10 = 0.7094`, `MRR@10 = 0.8127`, `nDCG@10 = 0.7083`), a Citation-Grounded Script Engine, and Dual-Sink 4-month incremental + Seeding/ABSA foundations.

## Work performed

- Purged 148 Gemini keys and 1 third-party key across 16 legacy files; added automated pre-commit enforcement in `scripts/check_secrets.py` and `tests/unit/test_secret_hygiene.py`.
- Archived legacy notebooks, LaTeX reports, and Streamlit pages under `archive/legacy_coursework/` and copied legacy app Parquet files to `data/legacy_app_data/` without deleting any original file.
- Built `pipelines.build_gold_corpus` recovering `23,448` dropped GPS POI records and `5,798` `is_ec_video` flags from `final_raw_videos.csv`, resolving dish-origin vs. district collisions (`packages/taxonomy/location_poi.py`), and parsing `23,122` raw transcript JSONs with `strict=False` + LLM-refusal filtering (`21,748` speech transcripts).
- Implemented `NicheAnalyticsEngine`, pickle-free CSR `BM25Index` (`391,042` NFC Vietnamese unigrams/bigrams), `EvidenceReranker`, `BoundedGeminiClient`, `GroundedScriptEngine`, `SeedingDetector`, `AbsaAnalyzer`, 4-month incremental crawler/converter pipelines, FastAPI endpoints, and ASGI-mounted Gradio `/demo/`.

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Superpowers skill provenance, decisions, and verification record |
| [manifest.json](../../../../data/corpus/20261116_v1/manifest.json) | SHA256 checksums and exact row/column counts for `20261116_v1` Gold corpus |
| [retrieval_v1.json](../../../../artifacts/benchmarks/retrieval_v1.json) | Frozen retrieval benchmark (`BM25` vs `BM25 + Reranker` over 16 F&B queries) |
| [01_LIMITATIONS_AND_BUGS_AUDIT.md](../../../../ReFactor_structure/01_LIMITATIONS_AND_BUGS_AUDIT.md) | Detailed audit of legacy data fragmentation and static template defects |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `python3 scripts/check_secrets.py` | PASS | Zero secret leaks detected across entire workspace |
| `python3 -m mypy packages apps pipelines` | PASS | Strict static type checking across all Python packages, pipelines, and FastAPI/Gradio apps |
| `python3 -m pytest -v` | PASS | Contract, secret hygiene, Gold corpus SHA256, retrieval benchmark, guardrails, incremental dual-sink, and `/demo/` ASGI smoke suites |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Historical transcripts lack word-level Whisper timestamps and viewer comments | Exact sub-sentence audio playback and KOC-vs-Viewer comment gap apply fully to freshly crawled 4-month videos; historical videos use `wps_estimated` timestamps | `M3.3`, `M4.1`, `M5.2` |
| Docker Qdrant dense embeddings not yet populated | `mode="bm25"` and `hybrid_rrf` lexical fallback operate at `p95 = 21.0 ms`; explicit `mode="dense"` returns bounded `503 INDEX_NOT_READY` until Qdrant is populated | `M6.1` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| Zero hardcoded API keys in tracked files and clean Git history | Met | `scripts/check_secrets.py` + clean root commit on `khuonglaptri3/TikTok_AI_Engine_` |
| 100% preservation of `37,840` original local dataset files (`1.50 GB`) | Met | Local `data/` verified intact; heavy binaries gitignored |
| SHA256-verified Gold Corpus + Hybrid RAG + FastAPI/Gradio `/demo/` operational | Met | `data/corpus/20261116_v1/manifest.json` + `tests/smoke/test_api_and_demo.py` |

Task `M0.1` is `COMPLETE`. Formal gate `M0.G` (`G0`) remains `NOT_RUN` pending dedicated gate review; engineering handoff proceeds to `M3.3` (live 4-month incremental capture).
