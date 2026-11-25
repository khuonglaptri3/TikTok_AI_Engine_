# Milestone task reports

Each started task has exactly two directories, `evidence/` and `superpowers/`, and one current results report, `README.md`. Open the report to review conclusions, the spec/plan links, actual verification, and outstanding work. `superpowers/` contains exactly `spec.md` and `plan.md`; all supporting data and workflow logs stay in `evidence/`. All authored documentation is in English; preserve original Vietnamese source queries and raw logs when required for evidence integrity.

| Task | Description | Status | Report |
| --- | --- | --- | --- |
| M0.1 | Historical asset preservation, pinned recovery (`37,840` files), Gold `20261117_recovered_v1` & `bm25-v2` provenance baseline | COMPLETE | [Read results](M0.1/README.md) |
| M0.2 | Contracts, bounded settings, finite ms timings, and error/log credential redaction | COMPLETE | [Read results](M0.2/README.md) |
| M0.3 | Installable API/demo foundation and real-corpus `offline_grounded` `/demo/` verification | COMPLETE | [Read results](M0.3/README.md) |
| M0.G | G0 foundation gate decision (`PASS` on merged `main`: `120` tests, `81`-file `mypy`, clean wheel & ASGI `/demo/`) | COMPLETE | [Read results](M0.G/README.md) |
| M1.1 | Taxonomy, per-field lineage/coverage audit, disambiguation fixes, and 120-record sample (`K_*` 30-row human overlap + `N` review) | COMPLETE | [Read results](M1.1/README.md) |
| M1.2 | Immutable taxonomy-corrected historical Gold snapshot (`20261118_taxonomy_fix_v1`) with verified parent lineage | COMPLETE | [Read results](M1.2/README.md) |
| M1.G | G1 corpus gate decision (`PASS` local-only scope; dual-snapshot SHA256/lineage & data card verified; public redistribution `BLOCKED`) | COMPLETE | [Read results](M1.G/README.md) |
| M2.1 | Descriptive niche benchmarks, cohort/missingness provenance, sparse abstention, and 100-request latency verification | COMPLETE | [Read results](M2.1/README.md) |
| M2.2 | `bm25-v3`, query-intent/no-answer guardrails, `K` full-transcript sign-off & `N` 120-disagreement concurrence + peer review (`MRR@10=0.8571`, `p95=32.44 ms`) | COMPLETE | [Read results](M2.2/README.md) |
| M2.3 | Qualified scripts, structural guardrails, `K` peer-review TDD fixes, and 30-draft two-contributor full-transcript audit (`108/120 = 90.0%` supported, `30/30` cited, `0` fabricated IDs) | COMPLETE | [Read results](M2.3/README.md) |
| M2.G | G2 historical core gate decision (`PASS` on `main` @ `dc595f04`: `177` pytest, `95`-file `mypy`, `sdist+whl` build, real-corpus ASGI `/demo/`; confirmed by `N` & `K`) | COMPLETE | [Read results](M2.G/README.md) |
| M3.1 | Repeated Dual-Sink ingestion repair, missing-modality schemas, interrupted recovery & `K` real-snapshot reproduction | COMPLETE | [Read results](M3.1/README.md) |
| M3.2 | Bounded 120-day collector worker, `70,996`-ID protection, crash-safe resume, 64 kbps audio receipts, offline `M3.1` round-trip & `N` peer review | COMPLETE | [Read results](M3.2/README.md) |
| M3.3 | Live capture->CPU ASR (`small`, `10/10` searchable `RTF=0.1971`)->`TikTokApi` comments (`454` raw / `452` Gold `fact_comments` across `28/30` vids, `93.33%` coverage)->Gold (`m3_3_pilot_snapshot_v2`)->BM25 `PASS` (`30/30` `N`+`K` verified, `221` tests, `105`-file `mypy`) | COMPLETE | [Read results](M3.3/README.md) |
| M3.G | G3 preparation: `M3.3` `30/30` complete, `M3.1` repeated-ingest replay (`5.64 s`/`6.14 s`, `0` duplicates, SHA256 preserved) & `29`-`.mp3` (`46.683` min) throughput projections (`N ~15.0 min`); `G3=NOT_RUN` awaiting `K` timing & joint sign-off | IN_PROGRESS | [Read results](M3.G/README.md) |
| M4.2 | Observed `is_ad`/EC flags separated from promo lexicon (`PR-AUC=0.8915` / `0.8728` no-MCN, cluster CI), `100/100` `N`+`K` full-transcript audit (`kappa=0.6364`) & `K` peer review (`194` tests) | COMPLETE | [Read results](M4.2/README.md) |
| M5.1 | Observable duplicate/contact/noise indicators, `K` baseline code/leakage/sensitivity peer review & TDD fixes (`194` tests); awaiting `M3.3` real pilot comments | IN_PROGRESS | [Read results](M5.1/README.md) |
| M5.2 | 4-aspect (`taste`/`price`/`hygiene`/`service`) NFC-exact `source_spans`, `absent_unknown` vs `observed neutral`, `>=3`-comment `sentiment_discrepancy`, `3x3` sensitivity, video-disjoint evaluator, fixture dry-run & `N` Phase 1 peer review + TDD fixes (`219` tests, `106`-file `mypy`; awaiting `M3.3` comments for `K`+`N` double-annotation) | IN_PROGRESS | [Read results](M5.2/README.md) |
| M6.1 | `5,000`-doc `restrict_to_df=True` parity on finalized `M2.2` human qrels across `tfidf_svd` & `fastembed` `MiniLM` vs `bm25-v3` + `N`/`K` sign-off (`bm25-v3` default confirmed; multimodal awaits `M4.G`/`M5.G`) | IN_PROGRESS | [Read results](M6.1/README.md) |

Independent cross-project assessments are listed in [task reports](../tasks/README.md). Their conclusions do not change milestone status or pass a gate.

Apply the exact layout defined in [AGENTS.md](../../../AGENTS.md) to all subsequent tasks (`M0.G`, `M1.G`, `M2.2`, `M3.1`, etc.):

```text
milestones/
├── README.md
└── <TASK-ID>/
    ├── README.md       # Results, verification, open issues, and next steps
    ├── evidence/       # JSON, CSV, logs, workflow.md, and supporting documentation
    └── superpowers/
        ├── spec.md     # Task specification and acceptance
        └── plan.md     # Execution steps and verification plan
```
