# M1.2 — Specification: Immutable Taxonomy-Corrected Historical Gold Snapshot (`20261118_taxonomy_fix_v1`)

- **Date:** 2026-11-18
- **Task ID:** `M1.2`
- **Primary Owner:** Trần Đình Khương (`K`)
- **Peer Reviewer:** Nguyễn Việt Nguyên (`N`)
- **Requirement Source:** [TikTok_AI_Engine_Milestone.md](../../../../planning/TikTok_AI_Engine_Milestone.md) (`M1.2`)

## Scope & Requirements
1. **Immutable Snapshot Publication & Collision Safety:**
   - Build a new immutable Gold snapshot `data/corpus/20261118_taxonomy_fix_v1` using `pipelines/build_gold_corpus/` incorporating the verified `M1.1` taxonomy/disambiguation fixes (`packages/taxonomy/location_poi.py`, `food_hierarchy.py`, `rule_extractor.py`).
   - Never overwrite `data/corpus/20261117_recovered_v1` or `data/corpus/20261116_v1`; enforce atomic staging via `snapshot_workspace` (`packages/common/snapshots.py`), rejecting existing destination collisions and failing closed on corrupted or missing table/manifest validation (`load_verified_corpus`).
2. **Parent, Source & Code Provenance Retention:**
   - Extend `build_gold_corpus` (and `pipelines.build_gold_corpus.__main__`) via TDD with optional `parent_corpus_dir: Path | None = None` (`--parent-corpus`) so `data/corpus/20261118_taxonomy_fix_v1/manifest.json` records `parent_snapshot_id="20261117_recovered_v1"` and `parent_manifest_sha256="10ed9c666707319f0a67c688e77d79ddc409e11c1f57ff075a01a3d718b714f4"`, validating the parent corpus via `load_verified_corpus` before building.
   - Record input-source manifest SHA256, builder/taxonomy code SHA256 digests, and table SHA256 digests in `docs/reports/milestones/M1.2/evidence/m1.2-build-receipt.json`.
3. **Byte Preservation & Before/After Delta Verification:**
   - Verify that 100% of pre-existing historical input files consumed by the builder (`cleaned_user_info.parquet`, `cleaned_video_info.parquet`, `final_raw_videos.csv`, `final_location_food_data.parquet`, `content_analysis_data.parquet`, and `20261117_recovered_v1` tables/manifest) remain byte-identical before and after the build.
   - Publish exact creator/video/transcript/POI/EC counts and quantify discrepancies/improvements between `20261117_recovered_v1` and `20261118_taxonomy_fix_v1` (`city_norm` recovery, `"ốc"` false-positive elimination, neutral `occasions` unknown handling).

## Acceptance Criteria
- TDD unit tests verify `--parent-corpus` provenance linkage, collision rejection (`FileExistsError`), and fail-closed verification on corrupted parent/staged snapshots (`RED -> GREEN`).
- `data/corpus/20261118_taxonomy_fix_v1` passes `load_verified_corpus`, key uniqueness, creator-join completeness, 49-column `fact_videos` schema, 15-column `dim_creators` schema, and SHA256 manifest checks; all original input and parent-snapshot bytes remain unchanged.
- `scripts/check_secrets.py`, `mypy packages apps pipelines`, and full `pytest` pass with `0` errors; task remains `IN_PROGRESS` pending independent build/receipt verification by Nguyễn Việt Nguyên (`N`) before `M1.G` (`G1`).
