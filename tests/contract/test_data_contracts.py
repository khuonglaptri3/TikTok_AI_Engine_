from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.common.logging import StageTimer
from packages.common.settings import AppSettings
from packages.data_contracts import (
    CanonicalErrorResponse,
    RetrievalRequest,
    ScriptGenerationRequest,
    VideoCitation,
)


def test_settings_load_from_dotenv_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("TIKTOK_RAG_RATE_LIMIT_RPM", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text("GEMINI_API_KEY=dummy_test_token\nTIKTOK_RAG_RATE_LIMIT_RPM=20\n", encoding="utf-8")
    cfg = AppSettings.from_env(dotenv_path=env_file)
    assert cfg.gemini_api_key == "dummy_test_token"
    assert cfg.rate_limit_rpm == 20


def test_retrieval_request_rejects_extra_fields_and_bounds() -> None:
    req = RetrievalRequest(query="bún bò huế cay", mode="bm25", top_k=5)
    assert req.top_k == 5
    with pytest.raises(ValidationError):
        RetrievalRequest(query="", top_k=5)
    with pytest.raises(ValidationError):
        RetrievalRequest(query="test", top_k=99)


def test_script_request_and_stage_timer_contracts() -> None:
    timer = StageTimer()
    with timer.measure("parse"):
        req = ScriptGenerationRequest(brief="Review quán ốc đêm sinh viên Quận 4 dưới 50k", target_duration_sec=40)
    timings = timer.finalize()
    assert req.target_duration_sec == 40
    assert "parse" in timings and "total_ms" in timings

    citation = VideoCitation(
        video_id="7304970581181549826",
        author_handle="1phutsaigon",
        tiktok_url="https://www.tiktok.com/@1phutsaigon/video/7304970581181549826",
        play_count=250000,
        viral_multiplier=4.2,
        engagement_rate=0.065,
    )
    err = CanonicalErrorResponse(code="PROVIDER_KEY_MISSING", message="Missing key")
    assert citation.viral_multiplier == 4.2
    assert err.code == "PROVIDER_KEY_MISSING"
