#!/usr/bin/env python3
"""End-to-end offline fixture verification for M3.2 against the real 70,996-video 20261118_taxonomy_fix_v1 Gold snapshot."""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[5]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from pipelines.crawl_incremental.__main__ import _load_protected_corpus_ids  # noqa: E402
from pipelines.crawl_incremental.models import CollectorBounds  # noqa: E402
from pipelines.crawl_incremental.providers import (  # noqa: E402
    LiveNetworkDisabledError,
    LiveTikTokCollectorProvider,
    OfflineFixtureAudioConverter,
    OfflineFixtureCollectorProvider,
    TransientCollectorError,
)
from pipelines.crawl_incremental.worker import BoundedIncrementalCollector  # noqa: E402
from pipelines.ingest_incremental_to_gold import ingest_incremental_batch_to_gold  # noqa: E402

BASE_CORPUS = _REPO_ROOT / "data/corpus/20261118_taxonomy_fix_v1"
RECEIPT_OUT = Path(__file__).resolve().parent / "m3_2_fixture_verification_receipt.json"


def _hash_dir(folder: Path) -> dict[str, str]:
    return {
        p.name: hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(folder.iterdir())
        if p.is_file()
    }


def main() -> None:
    before_hashes = _hash_dir(BASE_CORPUS)
    protected_ids, snapshot_id = _load_protected_corpus_ids(BASE_CORPUS)
    assert len(protected_ids) == 70996, f"Expected 70,996 historical IDs, got {len(protected_ids)}"

    sampled_hist_ids = sorted(protected_ids)[:5]
    as_of = datetime(2026, 11, 19, 12, 0, 0, tzinfo=UTC)
    cutoff = as_of - timedelta(days=120)

    def _cand(vid: str, ct: str | None, *, with_audio: bool = False, with_comments: bool = True) -> dict[str, Any]:
        return {
            "video_id": vid,
            "author_id": f"aid_{vid}",
            "author_handle": "fnb_fixture_creator",
            "author_nickname": "FnB Fixture",
            "follower_count": 25000,
            "create_time": ct,
            "caption": f"Synthetic M3.2 offline fixture {vid} #ancungtiktok",
            "hashtags": ["ancungtiktok"],
            "duration_sec": 45,
            "play_count": 12000,
            "digg_count": 600,
            "comment_count": 1 if with_comments else 0,
            "share_count": 10,
            "collect_count": 30,
            "transcript": "Quán bún bò nước dùng đậm đà giá bình dân." if with_comments else "",
            "audio_fixture_payload": "ID3-SYNTHETIC-64K-MP3-BYTES" if with_audio else None,
            "comments": (
                [{"comment_id": f"{vid}_c1", "author_handle": "viewer_1", "text": "Nước dùng ngon!", "like_count": 3}]
                if with_comments
                else []
            ),
        }

    candidates = [
        *[_cand(hid, (as_of - timedelta(days=2)).isoformat(), with_audio=True) for hid in sampled_hist_ids],
        _cand("syn_old_121d", (as_of - timedelta(days=121)).isoformat()),
        _cand("syn_old_cutoff_minus_1s", (cutoff - timedelta(seconds=1)).isoformat()),
        _cand("syn_bad_timestamp", "not-an-iso-timestamp"),
        _cand("syn_exact_cutoff", cutoff.isoformat(), with_audio=True),
        _cand("syn_fresh_missing_mod", (as_of - timedelta(days=7)).isoformat(), with_audio=False, with_comments=False),
        _cand("syn_retry_once", (as_of - timedelta(days=4)).isoformat(), with_audio=True),
        _cand("syn_outage_then_resume", (as_of - timedelta(days=3)).isoformat(), with_audio=False),
    ]

    class _ProbeProvider(OfflineFixtureCollectorProvider):
        def __init__(self, path: Path) -> None:
            super().__init__(path)
            self.block_outage = True
            self._retry_hits = 0

        def fetch_video_detail(self, candidate: dict[str, Any]) -> dict[str, Any]:
            vid = str(candidate.get("video_id") or "")
            if vid == "syn_retry_once":
                self._retry_hits += 1
                if self._retry_hits == 1:
                    raise TransientCollectorError("temporary upstream timeout")
            if vid == "syn_outage_then_resume" and self.block_outage:
                raise TransientCollectorError("upstream 503 ms_token=redact_me_probe_tok")
            return super().fetch_video_detail(candidate)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        fx_path = tmp_dir / "probe_candidates.jsonl"
        fx_path.write_text(
            "\n".join(json.dumps(c, ensure_ascii=False) for c in candidates) + "\n",
            encoding="utf-8",
        )
        batch_dir = tmp_dir / "batch_probe"
        provider = _ProbeProvider(fx_path)
        collector = BoundedIncrementalCollector(
            provider=provider,
            audio_converter=OfflineFixtureAudioConverter(),
            bounds=CollectorBounds(max_retries=2),
            sleep_fn=lambda _: None,
        )

        # Run 1: initial run with 1 transient recovery and 1 exhausted failure
        m_run1 = collector.run(
            output_dir=batch_dir,
            as_of_utc=as_of,
            historical_video_ids=protected_ids,
            base_corpus_snapshot_id=snapshot_id,
            resume=False,
        )
        assert not (set(sampled_hist_ids) & set(provider.detail_called_ids))
        assert m_run1.requested_count == 12
        assert m_run1.succeeded_count == 3
        assert m_run1.failed_count == 2  # syn_bad_timestamp + syn_outage_then_resume
        assert m_run1.skipped_count == 7  # 5 historical + 2 outside 120d window

        # Run 2: resume=True after outage clears
        provider.detail_called_ids.clear()
        provider.block_outage = False
        m_run2 = collector.run(
            output_dir=batch_dir,
            as_of_utc=as_of,
            historical_video_ids=protected_ids,
            base_corpus_snapshot_id=snapshot_id,
            resume=True,
        )
        assert provider.detail_called_ids == ["syn_outage_then_resume"]
        assert m_run2.requested_count == 12
        assert m_run2.succeeded_count == 1
        assert m_run2.failed_count == 1  # syn_bad_timestamp still invalid
        assert m_run2.skipped_count == 10  # 5 historical + 2 outside window + 3 already_succeeded_in_checkpoint

        written_rows = [
            json.loads(line)
            for line in (batch_dir / "videos_4m.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(written_rows) == 4

        # Round-trip ingest of the 4 fresh synthetic rows onto the real 70,996-video snapshot in temp dir
        gold_out_dir = tmp_dir / "gold_roundtrip_v1"
        gold_manifest = ingest_incremental_batch_to_gold(
            base_corpus_dir=BASE_CORPUS,
            incremental_jsonl=batch_dir / "videos_4m.jsonl",
            output_corpus_dir=gold_out_dir,
        )
        assert gold_manifest.total_videos == 70996 + 4
        assert len(gold_manifest.files) == 5

    # Verify live provider fail-closed gate
    live_blocked = False
    try:
        LiveTikTokCollectorProvider(allow_live_network=False, ms_token="dummy")
    except LiveNetworkDisabledError:
        live_blocked = True
    assert live_blocked is True

    after_hashes = _hash_dir(BASE_CORPUS)
    assert after_hashes == before_hashes, "Historical Gold snapshot bytes mutated!"

    receipt = {
        "task_id": "M3.2",
        "verified_at_utc": datetime.now(UTC).isoformat(),
        "base_corpus_snapshot_id": snapshot_id,
        "historical_protected_count": len(protected_ids),
        "base_snapshot_byte_identical": (after_hashes == before_hashes),
        "base_snapshot_sha256": before_hashes,
        "live_provider_fail_closed_verified": live_blocked,
        "run1_summary": {
            "source_mode": m_run1.source_mode,
            "is_synthetic_fixture": m_run1.is_synthetic_fixture,
            "requested_count": m_run1.requested_count,
            "succeeded_count": m_run1.succeeded_count,
            "failed_count": m_run1.failed_count,
            "skipped_count": m_run1.skipped_count,
            "converted_audio_count": m_run1.converted_audio_count,
        },
        "run2_resume_summary": {
            "requested_count": m_run2.requested_count,
            "succeeded_count": m_run2.succeeded_count,
            "failed_count": m_run2.failed_count,
            "skipped_count": m_run2.skipped_count,
            "persisted_records_count": m_run2.persisted_records_count,
            "total_deduplicated_jsonl_rows": len(written_rows),
        },
        "m3_1_gold_roundtrip": {
            "parent_snapshot_id": gold_manifest.parent_snapshot_id,
            "resulting_total_videos": gold_manifest.total_videos,
            "published_tables_count": len(gold_manifest.files),
        },
    }
    RECEIPT_OUT.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
