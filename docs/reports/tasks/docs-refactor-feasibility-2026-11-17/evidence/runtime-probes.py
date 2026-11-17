"""Bounded audit reproductions; no providers, crawls, or corpus writes."""

from __future__ import annotations

import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(ROOT))


def guardrail_probes() -> dict:
    from packages.llm.guardrails.verifier import recalculate_timeline_and_verify
    from packages.common.settings import AppSettings

    beats, report = recalculate_timeline_and_verify(
        raw_beats=[{"dialogue": "Unsupported factual statement without a supplied citation."}],
        hook_options=[],
        target_duration_sec=300,
        niche_wps=3,
        valid_evidence_ids={"unrelated_retrieved_video"},
    )
    _, empty_report = recalculate_timeline_and_verify(
        raw_beats=[], hook_options=[], target_duration_sec=45,
        niche_wps=3, valid_evidence_ids={"unrelated_retrieved_video"},
    )
    return {
        "uncited_input": {"output_citations": beats[0].cited_video_ids, "report": report.model_dump()},
        "empty_script": empty_report.model_dump(),
        "max_calls_setting_accepts_5": AppSettings(max_llm_calls_per_turn=5).max_llm_calls_per_turn,
        "scope": "Controlled function calls using synthetic text; no semantic entailment or live synthesis measured.",
    }


def incremental_probes() -> dict:
    import hashlib
    import tempfile
    import pandas as pd
    from packages.data_contracts.multimodal import RawIncrementalVideoRecord, RawCommentInput, RawWhisperSegment
    from pipelines.ingest_incremental_to_gold.converter import ingest_incremental_batch_to_gold

    # The converter preserves the base video columns; use every field in its canonical new row.
    fields = [
        "video_id", "author_id", "author_handle", "author_nickname", "follower_count", "follower_tier",
        "create_time", "create_hour", "create_weekday", "caption", "hashtags", "duration_sec", "duration_bucket",
        "play_count", "digg_count", "comment_count", "share_count", "collect_count", "engagement_rate",
        "creator_median_play_count", "viral_multiplier", "is_ad", "is_ec_video", "poi_name", "poi_address",
        "poi_city", "poi_category_tiny", "city_norm", "district_norm", "region", "location_source",
        "legacy_llm_city", "legacy_llm_district", "legacy_category", "legacy_food_category", "video_format",
        "food_category", "dishes", "price_tier", "occasions", "hook_text", "body_beats", "cta_text",
        "transcript", "transcript_word_count", "words_per_second", "has_transcript", "rag_document", "tiktok_url",
    ]
    # Read the row literal keys from the actual converter instead of assuming an older schema spelling.
    import ast
    tree = ast.parse((ROOT / "pipelines/ingest_incremental_to_gold/converter.py").read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            keys = [k.value for k in node.keys if isinstance(k, ast.Constant) and isinstance(k.value, str)]
            if "video_id" in keys and "rag_document" in keys:
                fields = keys
                break

    with tempfile.TemporaryDirectory(prefix="tiktok-audit-") as tmp:
        tmpdir = Path(tmp)
        base = tmpdir / "base"
        base.mkdir()
        creators = pd.DataFrame([{"author_id": "audit_author", "median_play_count": 1000.0}])
        seed = dict.fromkeys(fields)
        seed.update(video_id="audit_base_video", author_id="audit_author", has_transcript=False,
                    is_ec_video=False, poi_name=None)
        videos = pd.DataFrame([seed], columns=fields)
        files = []
        for name, frame in [("dim_creators.parquet", creators), ("fact_videos.parquet", videos)]:
            path = base / name
            frame.to_parquet(path, index=False)
            files.append({"filename": name, "rows": len(frame), "columns": len(frame.columns),
                          "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size})
        (base / "manifest.json").write_text(json.dumps({
            "snapshot_id": "audit_base", "created_at": "2026-11-17T00:00:00+00:00",
            "date_window_start": "2026-11-01", "date_window_end": "2026-11-17",
            "total_creators": 1, "total_videos": 1, "transcribed_videos": 0,
            "poi_tagged_videos": 0, "ec_tagged_videos": 0, "files": files,
            "caveats": ["Controlled audit fixture, not original corpus."],
        }), encoding="utf-8")

        def batch(vid: str) -> Path:
            record = RawIncrementalVideoRecord(
                video_id=vid, author_id="audit_author", author_handle="audit_creator",
                create_time="2026-11-10T00:00:00+00:00", caption="Audit fixture",
                transcript="Synthetic audit transcript.", duration_sec=5, play_count=1000,
                comments=[RawCommentInput(comment_id=f"{vid}_c", text="Synthetic comment")],
                whisper_segments=[RawWhisperSegment(start_sec=0, end_sec=5, text="Synthetic audit transcript.")],
            )
            path = tmpdir / f"{vid}.jsonl"
            path.write_text(record.model_dump_json() + "\n", encoding="utf-8")
            return path

        a, b = batch("audit_A"), batch("audit_B")
        v2, v3, replay = tmpdir / "v2", tmpdir / "v3", tmpdir / "replay"
        ingest_incremental_batch_to_gold(base, a, v2)
        ingest_incremental_batch_to_gold(v2, b, v3)
        ingest_incremental_batch_to_gold(v2, a, replay)

        def counts(folder: Path) -> dict:
            return {name: len(pd.read_parquet(folder / name)) for name in [
                "fact_videos.parquet", "fact_voice_segments.parquet", "fact_comments.parquet", "fact_absa_reviews.parquet"]}

        result = {"after_A": counts(v2), "after_A_then_B": counts(v3), "after_A_then_replay_A": counts(replay)}
        before = hashlib.sha256((v2 / "manifest.json").read_bytes()).hexdigest()
        ingest_incremental_batch_to_gold(v2, b, v2)
        result["same_output_as_base_accepted"] = True
        result["same_output_manifest_changed"] = before != hashlib.sha256((v2 / "manifest.json").read_bytes()).hexdigest()
        result["scope"] = "Synthetic temporary snapshots only; original project data was not modified."
        return result


if __name__ == "__main__":
    result = {"python": sys.version, "guardrails": guardrail_probes()}
    if "--incremental" in sys.argv:
        result["incremental"] = incremental_probes()
    result["versions"] = {}
    for name in ["pydantic", "pandas", "pyarrow", "numpy", "scipy", "fastapi", "gradio", "pytest"]:
        try:
            result["versions"][name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    output = Path(__file__).with_name("runtime-probes.json")
    output.write_text(json.dumps(result, indent=2, ensure_ascii=True), encoding="utf-8")
    print(json.dumps(result, indent=2, ensure_ascii=True))
