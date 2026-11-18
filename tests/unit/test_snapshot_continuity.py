from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from packages.analytics import load_verified_corpus
from packages.common.exceptions import CorpusNotReadyError
from packages.data_contracts.multimodal import (
    RawCommentInput,
    RawIncrementalVideoRecord,
    RawWhisperSegment,
)
from pipelines.build_gold_corpus.builder import build_gold_corpus
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold


def _hashes(folder: Path) -> dict[str, str]:
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir() if p.is_file()}


@pytest.fixture
def base_snapshot(tmp_path: Path) -> Path:
    base = tmp_path / "base"
    base.mkdir()
    creators = pd.DataFrame([{
        "author_id": "a1", "unique_id": "fixture_creator", "nickname": "Fixture", "verified": False,
        "commerce_user": False, "tt_seller": False, "follower_count": 1000, "follower_tier": "micro",
        "heart_count": 1000, "lifetime_video_count": 1, "sample_video_count": 1, "median_play_count": 1000.0,
        "median_engagement_rate": 0.1, "median_duration_sec": 30.0, "avg_videos_per_week": 1.0,
    }])
    videos = pd.DataFrame([{
        "video_id": "base_video", "author_id": "a1", "author_handle": "fixture_creator", "author_nickname": "Fixture",
        "tiktok_url": "https://www.tiktok.com/@fixture_creator/video/base_video", "follower_count": 1000,
        "follower_tier": "micro", "create_time": "2026-11-01T00:00:00+00:00", "create_hour": 0,
        "year_week": "Y2026_W44", "play_count": 1000, "digg_count": 100, "comment_count": 0,
        "share_count": 0, "collect_count": 0, "engagement_rate": 0.1, "viral_multiplier": 1.0,
        "is_ad": False, "is_ec_video": False, "playlist_id": None, "duration_sec": 30,
        "duration_bucket": "short_20_45s", "caption": "Synthetic fixture", "hashtags": [], "hashtag_count": 0,
        "has_transcript": False, "transcript": "", "word_count": 0, "word_per_second": 0.0,
        "has_cta": False, "has_curiosity_gap": False, "poi_id": None, "poi_name": None,
        "poi_address": None, "poi_city": None, "poi_category_tiny": None, "city_norm": None,
        "district_norm": None, "region": "unknown", "location_source": "unknown", "video_format": "Review món ăn",
        "food_category": "Ẩm thực Tổng hợp", "dishes": [], "price_tier": "unspecified", "occasions": [],
        "hook_text": "", "body_beats": [], "cta_text": "", "rag_document": "",
    }])
    files = []
    for name, frame in [("dim_creators.parquet", creators), ("fact_videos.parquet", videos)]:
        path = base / name
        frame.to_parquet(path, index=False)
        files.append({"filename": name, "rows": len(frame), "columns": len(frame.columns),
                      "sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "size_bytes": path.stat().st_size})
    (base / "manifest.json").write_text(json.dumps({
        "snapshot_id": "base", "created_at": "2026-11-17T00:00:00+00:00",
        "date_window_start": "2026-11-01", "date_window_end": "2026-11-01", "total_creators": 1,
        "total_videos": 1, "transcribed_videos": 0, "poi_tagged_videos": 0, "ec_tagged_videos": 0,
        "files": files, "caveats": ["Independent synthetic fixture."],
    }), encoding="utf-8")
    return base


def _batch(tmp_path: Path, video_id: str, *, text: str = "Phở bò thơm ngon giá hợp lý.", comment_id: str | None = None,
           comment: RawCommentInput | None = None) -> Path:
    rec = RawIncrementalVideoRecord(
        video_id=video_id, author_id="a1", author_handle="fixture_creator", create_time="2026-11-10T00:00:00+00:00",
        caption="Synthetic phở bò fixture", duration_sec=30, play_count=2000,
        transcript=text, whisper_segments=[RawWhisperSegment(start_sec=0, end_sec=4, text=text)],
        comments=[comment or RawCommentInput(comment_id=comment_id or f"{video_id}_comment", text="Giá hợp lý")],
    )
    path = tmp_path / f"{video_id}_{comment_id or 'initial'}.jsonl"
    path.write_text(rec.model_dump_json(exclude_unset=True) + "\n", encoding="utf-8")
    return path


def test_second_batch_preserves_every_sink_and_base_bytes(base_snapshot: Path, tmp_path: Path) -> None:
    before = _hashes(base_snapshot)
    v2, v3 = tmp_path / "v2", tmp_path / "v3"
    ingest_incremental_batch_to_gold(base_snapshot, _batch(tmp_path, "A"), v2)
    ingest_incremental_batch_to_gold(v2, _batch(tmp_path, "B"), v3)
    assert set(pd.read_parquet(v3 / "fact_videos.parquet")["video_id"]) == {"base_video", "A", "B"}
    for name in ["fact_voice_segments.parquet", "fact_comments.parquet", "fact_absa_reviews.parquet"]:
        assert set(pd.read_parquet(v3 / name)["video_id"]) == {"A", "B"}
    assert _hashes(base_snapshot) == before


@pytest.mark.parametrize("replay", [False, True], ids=["empty", "replay"])
def test_replay_or_empty_batch_retains_multimodal_rows(base_snapshot: Path, tmp_path: Path, replay: bool) -> None:
    first = _batch(tmp_path, "A")
    v2, out = tmp_path / "v2", tmp_path / "next"
    ingest_incremental_batch_to_gold(base_snapshot, first, v2)
    empty = tmp_path / "empty.jsonl"
    empty.write_text("", encoding="utf-8")
    ingest_incremental_batch_to_gold(v2, first if replay else empty, out)
    for name in ["fact_voice_segments.parquet", "fact_comments.parquet", "fact_absa_reviews.parquet"]:
        assert set(pd.read_parquet(out / name)["video_id"]) == {"A"}
    assert len(pd.read_parquet(out / "fact_videos.parquet")) == 2


def test_explicit_enrichment_updates_existing_transcript_and_preserves_old_comments(base_snapshot: Path, tmp_path: Path) -> None:
    v2, out = tmp_path / "v2", tmp_path / "enriched"
    ingest_incremental_batch_to_gold(base_snapshot, _batch(tmp_path, "A"), v2)
    ingest_incremental_batch_to_gold(
        v2, _batch(tmp_path, "A", text="Phở bò có nước dùng thơm và thịt mềm.", comment_id="A_second"), out,
        update_existing=True,
    )
    videos = pd.read_parquet(out / "fact_videos.parquet")
    assert len(videos) == 2
    assert videos.loc[videos["video_id"] == "A", "transcript"].iloc[0] == "Phở bò có nước dùng thơm và thịt mềm."
    assert set(pd.read_parquet(out / "fact_comments.parquet")["comment_id"]) == {"A_comment", "A_second"}
    assert len(pd.read_parquet(out / "fact_absa_reviews.parquet")) == 1


def test_converter_rejects_existing_output_without_changing_it(base_snapshot: Path, tmp_path: Path) -> None:
    before = _hashes(base_snapshot)
    with pytest.raises(FileExistsError):
        ingest_incremental_batch_to_gold(base_snapshot, _batch(tmp_path, "A"), base_snapshot)
    assert _hashes(base_snapshot) == before


def test_historical_builder_rejects_published_output_before_loading_inputs(base_snapshot: Path, tmp_path: Path) -> None:
    before = _hashes(base_snapshot)
    with pytest.raises(FileExistsError):
        build_gold_corpus(tmp_path / "missing_sources", base_snapshot)
    assert _hashes(base_snapshot) == before


def test_failed_historical_build_does_not_publish_partial_snapshot(tmp_path: Path) -> None:
    out = tmp_path / "failed_snapshot"
    with pytest.raises(FileNotFoundError):
        build_gold_corpus(tmp_path / "missing_sources", out)
    assert not out.exists()


def test_failed_build_releases_publication_lock_for_retry(tmp_path: Path) -> None:
    out = tmp_path / "retry_snapshot"
    for _ in range(2):
        with pytest.raises(FileNotFoundError):
            build_gold_corpus(tmp_path / "missing_sources", out)


@pytest.mark.parametrize("coverage", ["empty", "partial", "duplicate"])
def test_loader_rejects_uncovered_or_ambiguous_required_tables(base_snapshot: Path, coverage: str) -> None:
    path = base_snapshot / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if coverage == "empty":
        manifest["files"] = []
    elif coverage == "partial":
        manifest["files"] = manifest["files"][:1]
    else:
        manifest["files"].append(manifest["files"][0])
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(CorpusNotReadyError):
        load_verified_corpus(base_snapshot)


def test_comment_only_enrichment_preserves_curated_text_and_exact_voice(base_snapshot: Path, tmp_path: Path) -> None:
    v2, out = tmp_path / "v2", tmp_path / "comments_only"
    ingest_incremental_batch_to_gold(base_snapshot, _batch(tmp_path, "A"), v2)
    videos = pd.read_parquet(v2 / "fact_videos.parquet")
    row = videos.index[videos["video_id"] == "A"][0]
    videos.at[row, "hook_text"] = "Previously audited opening."
    videos.at[row, "body_beats"] = ["Previously audited body."]
    videos.at[row, "cta_text"] = "Previously audited ending."
    videos.at[row, "rag_document"] = "Previously audited search document."
    video_file = v2 / "fact_videos.parquet"
    videos.to_parquet(video_file, index=False)
    manifest_file = v2 / "manifest.json"
    manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        if entry["filename"] == "fact_videos.parquet":
            entry["sha256"] = hashlib.sha256(video_file.read_bytes()).hexdigest()
            entry["size_bytes"] = video_file.stat().st_size
    manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
    voice = pd.read_parquet(v2 / "fact_voice_segments.parquet")
    payload = tmp_path / "comments_only.jsonl"
    payload.write_text(RawIncrementalVideoRecord(
        video_id="A", author_id="a1", author_handle="fixture_creator", create_time="2026-11-10T00:00:00+00:00",
        comments=[RawCommentInput(comment_id="A_new", text="Một ý kiến khác")],
    ).model_dump_json(exclude_unset=True) + "\n", encoding="utf-8")
    ingest_incremental_batch_to_gold(v2, payload, out, update_existing=True)
    pd.testing.assert_frame_equal(videos, pd.read_parquet(out / "fact_videos.parquet"))
    pd.testing.assert_frame_equal(voice, pd.read_parquet(out / "fact_voice_segments.parquet"))


@pytest.mark.parametrize("explicit_zero,want_likes", [(False, 57), (True, 0)])
def test_sparse_comment_update_retains_omitted_metadata(base_snapshot: Path, tmp_path: Path,
                                                       explicit_zero: bool, want_likes: int) -> None:
    v2, out = tmp_path / "v2", tmp_path / "comment_update"
    first = _batch(tmp_path, "A", comment=RawCommentInput(
        comment_id="A_comment", author_handle="original_commenter", text="Giá hợp lý", like_count=57,
    ))
    ingest_incremental_batch_to_gold(base_snapshot, first, v2)
    comment = (RawCommentInput(comment_id="A_comment", text="Updated text", like_count=0) if explicit_zero
               else RawCommentInput(comment_id="A_comment", text="Updated text"))
    update = tmp_path / "update.jsonl"
    update.write_text(RawIncrementalVideoRecord(
        video_id="A", author_id="a1", author_handle="fixture_creator", create_time="2026-11-10T00:00:00+00:00",
        comments=[comment],
    ).model_dump_json(exclude_unset=True) + "\n", encoding="utf-8")
    ingest_incremental_batch_to_gold(v2, update, out, update_existing=True)
    comments = pd.read_parquet(out / "fact_comments.parquet")
    assert len(comments) == 1
    assert comments.iloc[0]["text"] == "Updated text"
    assert comments.iloc[0]["author_handle"] == "original_commenter"
    assert comments.iloc[0]["like_count"] == want_likes


def test_incremental_manifest_binds_parent_snapshot_bytes(base_snapshot: Path, tmp_path: Path) -> None:
    manifest = ingest_incremental_batch_to_gold(base_snapshot, _batch(tmp_path, "A"), tmp_path / "lineage")
    saved = json.loads((tmp_path / "lineage/manifest.json").read_text(encoding="utf-8"))
    assert saved["parent_snapshot_id"] == "base"
    assert saved["parent_manifest_sha256"] == hashlib.sha256((base_snapshot / "manifest.json").read_bytes()).hexdigest()
    assert manifest.snapshot_id == "lineage"


@pytest.mark.parametrize("update_existing", [False, True])
def test_repeated_video_records_preserve_distinct_comments_and_supplied_fields(
    base_snapshot: Path, tmp_path: Path, update_existing: bool,
) -> None:
    first = RawIncrementalVideoRecord.model_validate_json(_batch(tmp_path, "A", comment_id="c1").read_text(encoding="utf-8").strip())
    second = RawIncrementalVideoRecord(
        video_id="A", author_id="a1", author_handle="fixture_creator", create_time="2026-11-10T00:00:00+00:00",
        caption="Later supplied caption", comments=[RawCommentInput(comment_id="c2", text="Một bình luận khác")],
    )
    payload = tmp_path / "repeated_video.jsonl"
    payload.write_text(first.model_dump_json(exclude_unset=True) + "\n" + second.model_dump_json(exclude_unset=True) + "\n", encoding="utf-8")
    out = tmp_path / "repeated_video"
    ingest_incremental_batch_to_gold(base_snapshot, payload, out, update_existing=update_existing)
    comments = pd.read_parquet(out / "fact_comments.parquet")
    assert set(comments.comment_id) == {"c1", "c2"}
    videos = pd.read_parquet(out / "fact_videos.parquet")
    added = videos[videos.video_id == "A"].iloc[0]
    assert added.caption == "Later supplied caption"
    assert added.transcript == first.transcript
    assert set(pd.read_parquet(out / "fact_voice_segments.parquet").text) == {first.transcript}


def test_initial_duplicate_comment_ids_merge_before_diagnostics(base_snapshot: Path, tmp_path: Path) -> None:
    record = RawIncrementalVideoRecord.model_validate_json(_batch(tmp_path, "A").read_text(encoding="utf-8").strip())
    record = record.model_copy(update={"comments": [
        RawCommentInput(comment_id="c1", text="Giá hợp lý", author_handle="observed", like_count=57, reply_count=4),
        RawCommentInput(comment_id="c1", text="Updated text", like_count=0),
    ]})
    payload = tmp_path / "duplicate_comments.jsonl"
    payload.write_text(record.model_dump_json(exclude_unset=True) + "\n", encoding="utf-8")
    out = tmp_path / "deduplicated"
    ingest_incremental_batch_to_gold(base_snapshot, payload, out)
    comments = pd.read_parquet(out / "fact_comments.parquet")
    assert len(comments) == 1
    comment = comments.iloc[0]
    assert comment["text"] == "Updated text"
    assert comment.author_handle == "observed"
    assert comment.like_count == 0 and comment.reply_count == 4
    diagnostic = pd.read_parquet(out / "fact_absa_reviews.parquet").iloc[0]
    assert diagnostic.clean_comment_count + diagnostic.seeding_comment_count == 1


def _minimal_raw_root(tmp_path: Path) -> Path:
    root = tmp_path / "raw_workspace"
    (root / "data/processed").mkdir(parents=True)
    (root / "data/interim").mkdir(parents=True)
    (root / "data/transcripts").mkdir(parents=True)

    pd.DataFrame(
        [
            {
                "user.id": "a1",
                "user.uniqueId": "creator_1",
                "user.nickname": "Creator One",
                "user.verified": False,
                "user.commerceUserInfo.commerceUser": False,
                "user.ttSeller": False,
                "stats.followerCount": 12000,
                "stats.heartCount": 50000,
                "stats.videoCount": 10,
                "avg_videos_per_week": 2.0,
            }
        ]
    ).to_parquet(root / "data/processed/cleaned_user_info.parquet", index=False)

    pd.DataFrame(
        [
            {
                "video.id": "v100",
                "author.id": "a1",
                "author.uniqueId": "creator_1",
                "author.nickname": "Creator One",
                "authorStats.followerCount": 12000,
                "createTime": pd.Timestamp("2025-02-10T12:00:00Z"),
                "year_week": "2025-W06",
                "statsV2.playCount": 15000,
                "statsV2.diggCount": 900,
                "statsV2.commentCount": 25,
                "statsV2.shareCount": 10,
                "statsV2.collectCount": 40,
                "video.duration": 35,
                "desc": "Nhà hàng Hàn Quốc ngon rẻ #ancungtiktok",
                "hashtags": ["ancungtiktok"],
                "isAd": False,
            }
        ]
    ).to_parquet(root / "data/processed/cleaned_video_info.parquet", index=False)

    pd.DataFrame(
        [
            {
                "video.id": "v100",
                "poi.id": "p1",
                "poi.name": "Ho Chi Minh City",
                "poi.address": "Vietnam",
                "poi.city": "",
                "poi.ttTypeNameTiny": "Restaurant",
                "isECVideo": "False",
                "playlistId": "",
            }
        ]
    ).to_csv(root / "data/interim/final_raw_videos.csv", index=False)
    return root


def test_historical_builder_records_verified_parent_provenance(
    base_snapshot: Path, tmp_path: Path
) -> None:
    raw_root = _minimal_raw_root(tmp_path)
    parent_before = _hashes(base_snapshot)
    expected_parent_sha = hashlib.sha256((base_snapshot / "manifest.json").read_bytes()).hexdigest()

    out = tmp_path / "rebuilt_v2"
    manifest = build_gold_corpus(
        root_dir=raw_root,
        output_dir=out,
        parent_corpus_dir=base_snapshot,
    )
    assert manifest.parent_snapshot_id == "base"
    assert manifest.parent_manifest_sha256 == expected_parent_sha
    assert _hashes(base_snapshot) == parent_before

    df_v = pd.read_parquet(out / "fact_videos.parquet")
    assert df_v.iloc[0]["city_norm"] == "hồ chí minh"
    assert "ốc" not in list(df_v.iloc[0]["dishes"])


def test_historical_builder_fails_closed_on_corrupted_parent_snapshot(
    base_snapshot: Path, tmp_path: Path
) -> None:
    raw_root = _minimal_raw_root(tmp_path)
    (base_snapshot / "fact_videos.parquet").write_bytes(b"corrupted_parquet_bytes")
    out = tmp_path / "should_not_publish"
    with pytest.raises(CorpusNotReadyError):
        build_gold_corpus(
            root_dir=raw_root,
            output_dir=out,
            parent_corpus_dir=base_snapshot,
        )
    assert not out.exists()
