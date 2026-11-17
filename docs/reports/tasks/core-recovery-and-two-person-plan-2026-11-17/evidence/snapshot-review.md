# Independent snapshot review — 2026-11-17

## Verdict

**Specification: changes required. Quality: changes required.** The reviewed patch repairs output collisions, staged publication, batch Sink B continuity, explicit same-video updates, and exception-time lock release. Three integrity gaps remain before this task can claim the required preservation and verified-base behavior.

Scope: exact `snapshot-review-package.diff`, relevant source in the isolated worktree at baseline `cdbc6ed`, and `snapshot-red.log`, `snapshot-intermediate.log`, `snapshot-green.log`. The supplied evidence records 7 failures, then 7 passes plus the new lock regression failing, then 8 passes. The eight tests were not rerun. This review excludes unrelated ongoing guardrail edits and future model work.

## Findings

### Important — comment-only enrichment destroys historical text annotations

Location: `pipelines/ingest_incremental_to_gold/converter.py:286-292` (recomputation originates at lines 198-236).

A historical row may contain legacy curated hook/body/CTA and curiosity annotations and a RAG document built with legacy location/taxonomy evidence. `update_existing=True` with only comments retains its transcript, but unconditionally replaces all listed derived columns with heuristic reconstruction. A temp-only probe confirmed `has_cta=True` and `has_curiosity_gap=True` become false, the curated hook becomes the first transcript sentence, the CTA disappears, and the curated RAG document becomes a newly inferred document. This happens without any transcript change.

Required regression: start from a verified historical row with curated text annotations and legacy normalized geography; ingest a sparse comment-only record. Assert all 49 video columns are unchanged, comments/ABSA update, and exact voice rows remain equal. Recompute transcript-derived fields only when the transcript is actually changed; preserve historical annotations otherwise.

### Important — required Sink A tables need not be covered by the manifest

Location: `packages/analytics/engine.py:54-65`, relied on by `pipelines/ingest_incremental_to_gold/converter.py:123-138`.

The existing loader verifies declared entries, then reads `dim_creators.parquet` and `fact_videos.parquet` regardless of whether either is declared. The new converter correctly restricts optional multimodal reads to declared entries, but inherits this required-table trust gap. A temp-only probe removed the fact-video manifest entry, modified its play count to `123456789`, and performed empty ingestion. The unverified value was accepted and republished under a fresh valid checksum. This is an inherited loader defect exposed by the required verified-base contract, not a claim that these loader lines were newly introduced by this patch.

Required regression: reject empty/partial required-table manifests and duplicate required filenames before consuming or publishing data. Both required names must appear exactly once and pass verification. Continue excluding undeclared optional Sink B files from consumption. Failed verification must leave no output or stale publication lock.

### Important — sparse same-comment updates reset observed metadata

Location: `pipelines/ingest_incremental_to_gold/converter.py:173-180`, especially line 179.

The per-comment dictionary prevents duplicate IDs during existing-video enrichment, but an incoming `RawCommentInput` fully replaces its previous value, including defaults for omitted fields. A temp-only probe started with `comment_id=A_comment`, `author_handle=historical_commenter`, and `like_count=57`. An incoming same-ID record containing only ID and updated text published one row with handle empty and likes zero. Omitted reply counts behave likewise. The default handle can also change same-author seeding diagnostics.

Required regression: sparse same-ID text updates retain observed author/like/reply metadata; explicitly supplied values, including zero, are honored. Merge supplied fields with the old comment before rebuilding seeding/ABSA diagnostics. New comment IDs may still use normal defaults.

## Focused checks and limits

- A temp-only comment-enrichment probe changed a verified existing exact voice start to `0.123456789`, then used `pandas.testing.assert_frame_equal` on before/after voice tables. **PASS**, including all column values and pandas dtypes. Exact voice data is retained when no transcript or Whisper segments change.
- Existing-video enrichment merges comments by comment ID and emits one updated fact-video/ABSA identity. No extra video identity was observed in the reviewed path.
- The final snapshot helper closes its owned lock handle before unlink, including failures. Temporary staging is removed after failed builds; final-directory rename occurs after manifest creation. The supplied Windows retry regression supports the lock cleanup repair. No additional Windows handle defect was identified by source inspection.
- Existing output and same-base destinations are rejected before source loading. No original historical corpus was used or modified in these probes; all data were synthetic under `TemporaryDirectory`.
- The helper prevents replacing a named snapshot through this API; it does not provide filesystem-enforced immutability against arbitrary writers. Documentation should retain that distinction.
- No claim is made that hashes alone validate arbitrary manifest row/schema/identity semantics. No live providers, crawling, commits, or publication were invoked.

## Review execution provenance

The reviewer read installed `superpowers/7.0.1/skills/using-superpowers/SKILL.md`; its explicit dispatched-subagent exemption applies. The task-level specification and execution plan were read before source review. This is an independent review within the existing authorized task bundle, not a separate implementation phase.

The successful targeted probe used the already cached Python 3.12 environment and exited `0`. Its observed output was:

```text
COMMENT_ONLY_CHANGED: has_cta True -> False; has_curiosity_gap True -> False;
curated hook/CTA/rag_document replaced
UNDECLARED_FACT_VIDEOS_ACCEPTED 123456789
EXACT_VOICE_VALUES_AND_DTYPES_PRESERVED True
SAME_COMMENT_ENRICHMENT [{comment_id: A_comment, author_handle: '', like_count: 0}]
```

An initial probe attempt started uv wheel resolution and was cancelled before execution; two subsequent probe-print attempts exited nonzero because of Windows stdout encoding / NumPy boolean JSON serialization. The final probe corrected only output formatting, then executed all checks successfully. These attempts did not change production source or historical data.

The implementer owns RED/GREEN regressions and final verification for the three findings. This review does not change milestone or gate status.
