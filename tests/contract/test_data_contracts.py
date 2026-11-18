from __future__ import annotations

import logging
import math
from pathlib import Path

import pytest
from pydantic import ValidationError

from packages.common.exceptions import (
    CorpusNotReadyError,
    IndexNotReadyError,
    ProviderKeyMissingError,
    QuotaBlockedError,
    UnsupportedDomainError,
)
from packages.common.logging import SecretRedactingFilter, StageTimer, redact_secrets
from packages.common.settings import AppSettings
from packages.data_contracts import (
    AbsaComparisonRecord,
    AspectSentimentScores,
    CanonicalErrorResponse,
    CorpusFileChecksum,
    CorpusManifest,
    EvidenceCard,
    GuardrailReport,
    NicheBenchmarkSummary,
    NicheQueryFilter,
    RawCommentInput,
    RawWhisperSegment,
    RetrievalRequest,
    RetrievalResponse,
    ScriptGenerationRequest,
    TrustAuditRequest,
    TrustAuditResponse,
    VideoCitation,
    VoiceSegmentRecord,
)


def _valid_citation() -> VideoCitation:
    return VideoCitation(
        video_id="7304970581181549826",
        author_handle="1phutsaigon",
        tiktok_url="https://www.tiktok.com/@1phutsaigon/video/7304970581181549826",
        play_count=250000,
        viral_multiplier=4.2,
        engagement_rate=0.065,
    )


def _valid_benchmark() -> NicheBenchmarkSummary:
    return NicheBenchmarkSummary(
        matched_videos=10,
        transcribed_videos=8,
        poi_tagged_videos=5,
        median_plays=10000.0,
        p75_plays=20000.0,
        median_engagement_rate=0.05,
        duration_q25_sec=25.0,
        duration_median_sec=40.0,
        duration_q75_sec=60.0,
        median_word_per_second=3.2,
        hashtag_q25=3,
        hashtag_q75=6,
        top_hashtags=["saigonfood"],
        top_posting_hours=[],
        top_poi_venues=[],
        applied_filters={},
        timings_ms={"filter_ms": 1.2, "total_ms": 2.5},
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

    citation = _valid_citation()
    err = CanonicalErrorResponse(code="PROVIDER_KEY_MISSING", message="Missing key")
    assert citation.viral_multiplier == 4.2
    assert err.code == "PROVIDER_KEY_MISSING"


@pytest.mark.parametrize("bad_float", [math.nan, math.inf, -math.inf])
def test_contracts_and_settings_reject_nan_and_inf(bad_float: float) -> None:
    with pytest.raises(ValidationError):
        VideoCitation(
            video_id="v1",
            author_handle="u1",
            tiktok_url="https://tiktok.com/@u1/video/1",
            play_count=100,
            viral_multiplier=bad_float,
            engagement_rate=0.05,
        )
    with pytest.raises(ValidationError):
        EvidenceCard(
            rank=1,
            score=bad_float,
            citation=_valid_citation(),
            video_format="Review quán ăn",
            food_category="Món nước & Sợi",
            dishes=["phở"],
            price_tier="mid_50_150k",
            occasions=["an_sang_trua_nhanh"],
            duration_sec=40,
            duration_bucket="short_20_45s",
            hook_text="Hook",
            body_beats=["Beat 1"],
            cta_text="CTA",
            transcript_excerpt="Excerpt",
        )
    with pytest.raises(ValidationError):
        AspectSentimentScores(taste=bad_float, price=0.0, hygiene=0.0, service=0.0)
    with pytest.raises(ValidationError):
        RawWhisperSegment(start_sec=0.0, end_sec=bad_float, text="Xin chào")
    with pytest.raises(ValidationError):
        VoiceSegmentRecord(
            segment_id="s1",
            video_id="v1",
            seq_no=0,
            start_sec=0.0,
            end_sec=1.0,
            timestamp_source="whisper_exact",
            text="Xin chào",
            words_per_sec=2.0,
            pitch_std=bad_float,
        )
    with pytest.raises(ValidationError):
        GuardrailReport(
            passed=False,
            estimated_duration_sec=10.0,
            target_duration_sec=10.0,
            duration_delta_sec=bad_float,
            total_words=20,
            valid_citations_ratio=1.0,
            cliche_phrases_detected=[],
            warnings=[],
        )
    with pytest.raises(ValidationError):
        NicheBenchmarkSummary(
            **{**_valid_benchmark().model_dump(), "timings_ms": {"total_ms": bad_float}},
        )
    with pytest.raises(ValidationError):
        AppSettings(llm_deadline_seconds=bad_float)


def test_contracts_reject_unknown_and_malformed_boundary_inputs() -> None:
    # Unknown extra fields rejected
    with pytest.raises(ValidationError):
        NicheQueryFilter.model_validate({"city_norm": "hà nội", "unexpected_field": 123})
    with pytest.raises(ValidationError):
        RetrievalRequest.model_validate({"query": "phở bò", "unknown": True})
    with pytest.raises(ValidationError):
        ScriptGenerationRequest.model_validate({"brief": "Review bún bò ở Huế", "unknown": "x"})
    with pytest.raises(ValidationError):
        TrustAuditRequest.model_validate({"transcript": "Quán ăn sạch sẽ lắm", "extra_key": 1})
    with pytest.raises(ValidationError):
        CanonicalErrorResponse.model_validate({"code": "ERR", "message": "oops", "extra": "bad"})

    # Blank / whitespace-only inputs rejected
    with pytest.raises(ValidationError):
        RetrievalRequest(query="   ")
    with pytest.raises(ValidationError):
        ScriptGenerationRequest(brief="     ")
    with pytest.raises(ValidationError):
        TrustAuditRequest(video_id="   ", transcript="Quán bún bò rất ngon")
    with pytest.raises(ValidationError):
        TrustAuditRequest(video_id="v1", transcript="     ")
    with pytest.raises(ValidationError):
        RawCommentInput(comment_id="   ", text="ngon")
    with pytest.raises(ValidationError):
        NicheQueryFilter(city_norm="   ")
    with pytest.raises(ValidationError):
        CanonicalErrorResponse(code="   ", message="msg")
    with pytest.raises(ValidationError):
        CanonicalErrorResponse(code="ERR", message="   ")

    # Inverted durations rejected
    with pytest.raises(ValidationError):
        RawWhisperSegment(start_sec=5.0, end_sec=2.0, text="Xin chào")
    with pytest.raises(ValidationError):
        VoiceSegmentRecord(
            segment_id="s1",
            video_id="v1",
            seq_no=0,
            start_sec=10.0,
            end_sec=4.0,
            timestamp_source="wps_estimated",
            text="Xin chào",
            words_per_sec=3.0,
        )

    # Quantile ordering & corpus checksum invariants
    with pytest.raises(ValidationError):
        NicheBenchmarkSummary(
            **{**_valid_benchmark().model_dump(), "duration_q25_sec": 70.0, "duration_median_sec": 40.0}
        )
    with pytest.raises(ValidationError):
        NicheBenchmarkSummary(**{**_valid_benchmark().model_dump(), "hashtag_q25": 8, "hashtag_q75": 4})
    with pytest.raises(ValidationError):
        CorpusFileChecksum(
            filename="../escape.parquet",
            rows=1,
            columns=1,
            sha256="a" * 64,
            size_bytes=10,
        )
    with pytest.raises(ValidationError):
        CorpusFileChecksum(
            filename="fact_videos.parquet",
            rows=1,
            columns=1,
            sha256="z" * 64,
            size_bytes=10,
        )
    with pytest.raises(ValidationError):
        CorpusManifest(
            snapshot_id="snap_1",
            created_at="2026-11-17T00:00:00+00:00",
            date_window_start="2024-01-01",
            date_window_end="2025-01-01",
            total_creators=1,
            total_videos=10,
            transcribed_videos=11,
            poi_tagged_videos=0,
            ec_tagged_videos=0,
            files=[],
            caveats=[],
        )


def test_timings_ms_enforces_ms_units_and_non_negative_values() -> None:
    timer = StageTimer()
    with pytest.raises(ValueError):
        with timer.measure("   "):
            pass
    with timer.measure("step_ms"):
        pass
    measured = timer.finalize()
    assert measured["step_ms"] >= 0.0
    assert measured["total_ms"] >= 0.0
    assert math.isfinite(measured["total_ms"])

    with pytest.raises(ValidationError):
        RetrievalResponse(
            query="phở",
            mode="bm25",
            reranked=False,
            total_candidates=0,
            relaxed_filters=[],
            items=[],
            timings_ms={"total_ms": -0.5},
        )
    with pytest.raises(ValidationError):
        TrustAuditResponse(
            comparison=AbsaComparisonRecord(
                video_id="v1",
                koc_scores=AspectSentimentScores(taste=0.5, price=0.0, hygiene=0.0, service=0.0),
                viewer_clean_scores=AspectSentimentScores(taste=0.2, price=0.0, hygiene=0.0, service=0.0),
                pr_hype_gap=0.075,
                undisclosed_pr_risk=0.2,
                viewer_pain_points=[],
                clean_comment_count=1,
                seeding_comment_count=0,
            ),
            comments=[],
            timings_ms={"latency_seconds": 1.2},
        )


def test_explicit_error_payloads_and_no_credentials_in_logs() -> None:
    fake_google_key = "AIzaSy" + "DummyKeyValue1234567890"
    fake_bearer = "Bearer " + "secret_token_xyz_987"
    fake_redis_url = "redis://user:supersecretpass@127.0.0.1:6379/0"

    assert (ProviderKeyMissingError().code, ProviderKeyMissingError().status_code) == (
        "PROVIDER_KEY_MISSING",
        503,
    )
    assert (QuotaBlockedError("quota").code, QuotaBlockedError("quota").status_code) == (
        "QUOTA_BLOCKED",
        429,
    )
    assert (CorpusNotReadyError("missing").code, CorpusNotReadyError("missing").status_code) == (
        "CORPUS_NOT_READY",
        503,
    )
    assert (IndexNotReadyError("missing").code, IndexNotReadyError("missing").status_code) == (
        "INDEX_NOT_READY",
        503,
    )
    assert (UnsupportedDomainError("ood").code, UnsupportedDomainError("ood").status_code) == (
        "UNSUPPORTED_DOMAIN",
        422,
    )

    settings = AppSettings(gemini_api_key=fake_google_key, redis_url=fake_redis_url)
    assert fake_google_key not in repr(settings)
    assert fake_google_key not in str(settings)
    assert "supersecretpass" not in repr(settings)
    assert "supersecretpass" not in str(settings)
    assert fake_google_key not in str(settings.safe_summary())
    assert "supersecretpass" not in str(settings.safe_summary())

    err = QuotaBlockedError(f"Failed request https://example.com?key={fake_google_key} with {fake_bearer}")
    assert fake_google_key not in err.message
    assert "secret_token_xyz_987" not in err.message
    assert "[REDACTED]" in err.message

    redacted = redact_secrets(f"GEMINI_API_KEY={fake_google_key} {fake_bearer} {fake_redis_url}")
    assert fake_google_key not in redacted
    assert "secret_token_xyz_987" not in redacted
    assert "supersecretpass" not in redacted

    # Standard Python logger with SecretRedactingFilter never emits raw credentials
    records: list[str] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(self.format(record))

    logger = logging.getLogger("tiktok_rag.test_secret_filter")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    handler = _ListHandler()
    handler.addFilter(SecretRedactingFilter())
    logger.addHandler(handler)

    logger.info("Connecting with key=%s auth=%s url=%s", fake_google_key, fake_bearer, fake_redis_url)
    assert len(records) == 1
    assert fake_google_key not in records[0]
    assert "secret_token_xyz_987" not in records[0]
    assert "supersecretpass" not in records[0]


def test_redaction_covers_json_payloads_exceptions_and_stack_info() -> None:
    json_secret_payload = (
        '{"api_key": "json_secret_key_001", "password": "json_secret_pass_002", '
        '"token": "json secret tok 003"}'
    )
    redacted_json = redact_secrets(json_secret_payload)
    assert "json_secret_key_001" not in redacted_json
    assert "json_secret_pass_002" not in redacted_json
    assert "json secret tok 003" not in redacted_json
    assert "[REDACTED]" in redacted_json

    domain_err = QuotaBlockedError(json_secret_payload)
    assert "json_secret_key_001" not in domain_err.message
    assert "json_secret_pass_002" not in domain_err.message
    assert "json secret tok 003" not in domain_err.message

    canonical_err = CanonicalErrorResponse(code="ERR", message=json_secret_payload)
    assert "json_secret_key_001" not in canonical_err.message
    assert "json_secret_pass_002" not in canonical_err.message
    assert "json secret tok 003" not in canonical_err.message

    records: list[str] = []

    class _ListHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            records.append(self.format(record))

    logger = logging.getLogger("tiktok_rag.test_traceback_filter")
    logger.handlers.clear()
    logger.propagate = False
    logger.setLevel(logging.INFO)
    handler = _ListHandler()
    handler.addFilter(SecretRedactingFilter())
    logger.addHandler(handler)

    try:
        raise RuntimeError(f"boom secret=trace_secret_004 {json_secret_payload}")
    except RuntimeError:
        logger.exception("Unhandled error", stack_info=True)

    assert len(records) == 1
    emitted = records[0]
    assert "trace_secret_004" not in emitted
    assert "json_secret_key_001" not in emitted
    assert "json_secret_pass_002" not in emitted
    assert "json secret tok 003" not in emitted
    assert "[REDACTED]" in emitted

    # Single-quoted dict literals also redact cleanly
    dict_secret_payload = "{'api-key': 'single_key_006', 'password': 'single_pass_007'}"
    redacted_dict = redact_secrets(dict_secret_payload)
    assert "single_key_006" not in redacted_dict
    assert "single_pass_007" not in redacted_dict

    # Direct stack_info secret redaction check
    records.clear()
    record_with_secret_stack = logging.LogRecord(
        name="tiktok_rag.test_traceback_filter",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="Stack payload",
        args=(),
        exc_info=None,
        sinfo='Stack frame local {"password": "stack_secret_005"}',
    )
    handler.handle(record_with_secret_stack)
    assert "stack_secret_005" not in records[-1]
    assert "[REDACTED]" in records[-1]
