# M1.2 — Immutable Historical Gold Snapshot (`20261118_taxonomy_fix_v1`)

- Status: IN_PROGRESS (Primary owner build, parent-lineage TDD, collision/byte-preservation, and taxonomy-delta verification complete; awaiting independent receipt/build check by Nguyễn Việt Nguyên)
- Execution date: 2026-11-18 (Asia/Saigon)
- Requirement source: [TikTok_AI_Engine_Milestone.md](../../../planning/TikTok_AI_Engine_Milestone.md) (`M1.2`)
- Repository version: `main` (incorporating `M1.1` taxonomy fixes + `M1.2` `--parent-corpus` provenance)
- Primary owner: Trần Đình Khương (`K`) · Peer reviewer: Nguyễn Việt Nguyên (`N`)
- Specification: [spec.md](superpowers/spec.md)
- Execution plan: [plan.md](superpowers/plan.md)

## Conclusion

Built and verified a new immutable Gold Parquet snapshot **`data/corpus/20261118_taxonomy_fix_v1`** (`manifest.json` SHA256 `49f23739f9e2ea8f1f66fe1b299fe636c19965c99fcadf2bdd6eef7dc18c27de`, elapsed `637.32s`) from the preserved historical inputs without overwriting or mutating `data/corpus/20261117_recovered_v1` or `data/corpus/20261116_v1`. Via TDD (`20/20` tests in `test_snapshot_continuity.py`), `pipelines.build_gold_corpus` now validates optional `--parent-corpus` snapshots fail-closed and binds `parent_snapshot_id="20261117_recovered_v1"` and `parent_manifest_sha256="10ed9c666707319f0a67c688e77d79ddc409e11c1f57ff075a01a3d718b714f4"`.

Across the unchanged cohort (**`264` creators, `70,996` unique videos across `49` columns, `21,748` accepted transcripts, `23,448` POI rows, `5,798` `is_ec_video` rows**; dates `2023-11-25` to `2025-03-19`), `20261118_taxonomy_fix_v1` realizes the `M1.1` disambiguation fixes: `city_norm` coverage rises from `17,014` to **`23,478` (`+6,464`)**, `district_norm` rises from `4,670` to **`13,151` (`+8,481`)**, known `region` rises from `15,931` to **`22,986` (`+7,055`)**, spurious `"ốc"` dish tags drop from `5,391` to **`1,606` (`-3,785`)**, and forced `"an_vat_xe_chieu"` occasions drop from `59,765` (`84.18%`) to **`1,365` (`1.92%`, `-58,400` converted to neutral `[]`)**. Under the two-person review rule, `M1.2` remains `IN_PROGRESS` pending independent verification by Nguyễn Việt Nguyên (`N`) before `M1.G` (`G1`).

## Work performed

- Extended `pipelines/build_gold_corpus/builder.py` and `pipelines/build_gold_corpus/__main__.py` via TDD with `parent_corpus_dir` (`--parent-corpus`), verifying parent checksums via `load_verified_corpus` before staging and recording `parent_snapshot_id` + `parent_manifest_sha256`.
- Built `data/corpus/20261118_taxonomy_fix_v1` atomically via `snapshot_workspace` (`dim_creators.parquet`: `264x15`, `35,285` B, SHA256 `0a704391...`; `fact_videos.parquet`: `70,996x49`, `58,851,557` B, SHA256 `9684c438...`).
- Verified collision rejection on a repeat `--output data/corpus/20261118_taxonomy_fix_v1` call (`FileExistsError`, `0` byte changes) and verified `100%` byte identity across all input tables and `20261117_recovered_v1` before and after the build.

## Measured deltas (`20261117_recovered_v1` -> `20261118_taxonomy_fix_v1`)

| Metric / field | `20261117_recovered_v1` | `20261118_taxonomy_fix_v1` | Delta | Cause |
| --- | ---: | ---: | ---: | --- |
| Creators / Videos / Transcripts / POIs / EC | `264` / `70,996` / `21,748` / `23,448` / `5,798` | `264` / `70,996` / `21,748` / `23,448` / `5,798` | `0` | Identical preserved historical inputs |
| `city_norm` non-null | `17,014` (`23.96%`) | `23,478` (`33.07%`) | **`+6,464`** | `poi_name` fallback + English city/district aliases |
| `district_norm` non-null | `4,670` (`6.58%`) | `13,151` (`18.52%`) | **`+8,481`** | `District 1..12` aliases + longest-first boundary matching |
| `region != "unknown"` | `15,931` (`22.44%`) | `22,986` (`32.38%`) | **`+7,055`** | Expanded `CITY_TO_REGION` & recovered cities |
| Videos tagged with dish `"ốc"` | `5,391` (`7.59%`) | `1,606` (`2.26%`) | **`-3,785`** | Word-boundary regex removing `"Quốc"`, `"tốc"`, `"dốc"`, `"gốc"` hits |
| Videos with occasion `"an_vat_xe_chieu"` | `59,765` (`84.18%`) | `1,365` (`1.92%`) | **`-58,400`** | Removed forced default fallback; `58,400` rows now neutral `[]` |

## Outputs

| File | Purpose |
| --- | --- |
| [workflow.md](evidence/workflow.md) | Superpowers TDD workflow, runtime-compatibility decision, and command ledger |
| [m1.2-build-receipt.json](evidence/m1.2-build-receipt.json) | Machine-readable manifest, collision check, input/parent/code SHA256s, and before/after taxonomy deltas |
| [gold-build.log](evidence/gold-build.log) | CLI output of `python -m pipelines.build_gold_corpus --output data/corpus/20261118_taxonomy_fix_v1` |
| [red-m1_2-tests.log](evidence/red-m1_2-tests.log) / [green-m1_2-tests.log](evidence/green-m1_2-tests.log) | TDD RED (`2 failed`) and GREEN (`20 passed`) logs for `test_snapshot_continuity.py` |
| [manifest.json](../../../../data/corpus/20261118_taxonomy_fix_v1/manifest.json) | Published immutable snapshot manifest (`49f23739...`) |

## Verification

| Check | Result | Scope / evidence |
| --- | --- | --- |
| `pytest tests/unit/test_snapshot_continuity.py -v` | PASS (`20 passed`) | Collision rejection, atomic staging, parent provenance & corrupted-parent fail-closed; [green-m1_2-tests.log](evidence/green-m1_2-tests.log) |
| `pipelines.build_gold_corpus` (`20261118_taxonomy_fix_v1`) + collision & byte-preservation audit | PASS (`0` input/parent diffs) | Schema (`264x15`, `70,996x49`), unique keys, creator joins, SHA256 & collision check; [m1.2-build-receipt.json](evidence/m1.2-build-receipt.json) |
| Full project `mypy` & `pytest` | PASS (`76` files, `74 passed`) | Full static typecheck and contract/unit/eval/smoke suite |
| `python scripts/check_secrets.py` | PASS (`0` leaks) | Zero secret leaks across workspace |

## Open issues

| Issue | Impact | Follow-up / responsible task |
| --- | --- | --- |
| Default `AppSettings.corpus_dir` remains pointed at `20261117_recovered_v1` until a paired BM25 index is built for `20261118_taxonomy_fix_v1` | Switching default corpus without rebuilding BM25 (`rag_document` changed with cleaner dishes/locations) would mismatch `bm25-v2` & `retrieval_v2.json` | Build paired `bm25-v3` index and human-judged benchmark in `M2.2` before switching runtime defaults |
| Independent build/receipt verification by Nguyễn Việt Nguyên (`N`) pending | Two-person plan requires `N` to verify `20261118_taxonomy_fix_v1` receipt before `M1.G` (`G1`) | Hand off [m1.2-build-receipt.json](evidence/m1.2-build-receipt.json) to `N` |

## Acceptance and handoff

| Task criterion | Result | Evidence |
| --- | --- | --- |
| New snapshot ID built via `pipelines/build_gold_corpus/` without overwriting existing snapshots | Met | `data/corpus/20261118_taxonomy_fix_v1/`, [m1.2-build-receipt.json](evidence/m1.2-build-receipt.json) |
| Reject collisions, stage & verify all tables, fail closed on corruption, preserve all original bytes | Met | [test_snapshot_continuity.py](../../../../tests/unit/test_snapshot_continuity.py), [m1.2-build-receipt.json](evidence/m1.2-build-receipt.json) |
| Retain source/parent/code provenance and publish actual counts with discrepancies | Met | `parent_snapshot_id="20261117_recovered_v1"`, [m1.2-build-receipt.json](evidence/m1.2-build-receipt.json) |
| Independent verification by `N` | Pending peer review | Hand off to Nguyễn Việt Nguyên prior to `M1.G` (`G1`) |

Final task status: **IN_PROGRESS** (all primary-owner `M1.2` build, provenance, integrity, and delta checks complete; awaiting independent peer check by Nguyễn Việt Nguyên before `M1.G`).
