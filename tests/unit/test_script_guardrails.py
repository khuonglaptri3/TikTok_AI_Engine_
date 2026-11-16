from __future__ import annotations

import pytest

from packages.common.exceptions import (
    ProviderKeyMissingError,
    QuotaBlockedError,
    UnsupportedDomainError,
)
from packages.common.settings import AppSettings
from packages.llm import (
    BoundedGeminiClient,
    SlidingWindowRateLimiter,
    check_fnb_domain_relevance,
    recalculate_timeline_and_verify,
)


def test_sliding_window_rate_limiter_blocks_excess_rpm() -> None:
    limiter = SlidingWindowRateLimiter(max_rpm=2, redis_url=None)
    limiter.acquire("test")
    limiter.acquire("test")
    with pytest.raises(QuotaBlockedError):
        limiter.acquire("test")


def test_bounded_gemini_client_fails_closed_when_key_missing() -> None:
    settings = AppSettings(gemini_api_key="")
    client = BoundedGeminiClient(settings=settings)
    assert client.is_configured is False
    with pytest.raises(ProviderKeyMissingError):
        client.generate_structured_json('{"test": 1}')


def test_domain_gate_rejects_non_fnb_queries() -> None:
    with pytest.raises(UnsupportedDomainError):
        check_fnb_domain_relevance("Hướng dẫn phân tích kỹ thuật đầu tư chứng khoán và tiền ảo")
    # Valid F&B brief passes cleanly
    check_fnb_domain_relevance("Review quán bún bò Huế đậm đà ở Quận 3")


def test_timeline_recalculator_and_anti_cliche_citation_guardrail() -> None:
    raw_beats = [
        {
            "section_title": "1. Hook",
            "time_range": "99:99-99:99",  # LLM hallucinated timestamp must be overwritten
            "visual_angle": "Cận cảnh tô phở",
            "dialogue": "Một hai ba bốn năm sáu bảy tám chín mười mười một mười hai",
            "cited_video_ids": ["valid_vid_1", "hallucinated_vid_999"],
        },
        {
            "section_title": "2. Thân bài",
            "visual_angle": "Góc nghiêng 45 độ",
            "dialogue": "Món này ta nói ngon gì đâu luôn á mọi người ơi cứu cái nách tôi",
            "cited_video_ids": ["valid_vid_2"],
        },
    ]

    beats, report = recalculate_timeline_and_verify(
        raw_beats=raw_beats,
        hook_options=["Hook sạch không sáo rỗng"],
        target_duration_sec=10.0,
        niche_wps=3.0,
        valid_evidence_ids={"valid_vid_1", "valid_vid_2"},
    )

    assert beats[0].time_range != "99:99-99:99"
    assert beats[0].time_range.startswith("00:00-")
    # Hallucinated video_id must be stripped from output beat
    assert beats[0].cited_video_ids == ["valid_vid_1"]
    assert report.valid_citations_ratio < 1.0
    assert "ngon gì đâu luôn á" in report.cliche_phrases_detected
    assert report.passed is False
