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


def test_guardrail_does_not_assign_retrieved_ids_to_uncited_text() -> None:
    beats, report = recalculate_timeline_and_verify(
        [{"dialogue": "Một bản nháp chưa có nguồn hỗ trợ."}], [], 10, 3.0, {"available_but_unrelated"},
    )
    assert beats[0].cited_video_ids == []
    assert report.valid_citations_ratio == 0.0
    assert report.passed is False


def test_empty_script_cannot_pass_even_when_sources_exist() -> None:
    _, report = recalculate_timeline_and_verify([], [], 45, 3.0, {"v1"})
    assert report.passed is False
    assert report.total_words == 0


def test_duration_mismatch_prevents_structural_pass() -> None:
    _, report = recalculate_timeline_and_verify(
        [{"dialogue": "Một lời thoại ngắn.", "cited_video_ids": ["v1"]}], [], 300, 3.0, {"v1"},
    )
    assert report.passed is False


def test_duration_tolerance_matches_two_seconds_or_five_percent() -> None:
    _, report = recalculate_timeline_and_verify(
        [{"dialogue": " ".join(["món"] * 100), "cited_video_ids": ["v1"]}], [], 45, 2.0, {"v1"},
    )
    assert report.estimated_duration_sec == 50.0
    assert report.timing_valid is False
    assert report.passed is False


def test_each_beat_requires_nonempty_dialogue_and_citation() -> None:
    _, report = recalculate_timeline_and_verify(
        [{"dialogue": "", "cited_video_ids": ["v1"]}], [], 10, 3.0, {"v1"},
    )
    assert report.passed is False


def test_valid_structural_pass_does_not_claim_factual_grounding() -> None:
    beats, report = recalculate_timeline_and_verify(
        [{"dialogue": "Một hai ba bốn năm sáu bảy tám chín mười", "cited_video_ids": ["v1"]}], [], 5, 2.0, {"v1"},
    )
    assert beats[0].time_range == "00:00-00:05"
    assert report.passed is True
    assert report.model_dump()["grounding_verified"] is False


def test_one_uncited_beat_cannot_hide_behind_other_valid_beats() -> None:
    _, report = recalculate_timeline_and_verify(
        [{"dialogue": "Một hai ba bốn năm sáu", "cited_video_ids": ["v1"]},
         {"dialogue": "Bảy tám chín mười mười một"}], [], 10, 2.0, {"v1"},
    )
    assert report.passed is False


def test_no_evidence_pool_fails_cleanly_with_explicit_warning() -> None:
    beats, report = recalculate_timeline_and_verify(
        [{"dialogue": "Bản nháp khi kho chưa có bằng chứng.", "cited_video_ids": ["v1"]}],
        [],
        10,
        3.0,
        set(),
    )
    assert beats[0].cited_video_ids == []
    assert report.passed is False
    assert report.citation_coverage_ratio == 0.0
    assert report.valid_citations_ratio == 0.0
    assert any("bằng chứng" in w.lower() for w in report.warnings)


def test_bounded_gemini_client_enforces_turn_call_budget_and_deadline_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = AppSettings(gemini_api_key="dummy_test_key_for_unit_test", max_llm_calls_per_turn=2, llm_deadline_seconds=12.5)
    client = BoundedGeminiClient(settings=settings, rate_limiter=SlidingWindowRateLimiter(max_rpm=100, redis_url=None))

    # Exceeding max_llm_calls_per_turn must fail closed with QuotaBlockedError
    with pytest.raises(QuotaBlockedError):
        client.generate_structured_json("prompt", turn_calls_used=2)

    # Timeout from underlying SDK call must map cleanly to QuotaBlockedError with configured timeout_ms
    captured: dict[str, object] = {}

    def _fake_call(prompt: str, timeout_ms: int) -> str:
        captured["timeout_ms"] = timeout_ms
        raise TimeoutError("deadline exceeded")

    monkeypatch.setattr(client, "_call_gemini_sdk", _fake_call)
    with pytest.raises(QuotaBlockedError, match="timeout|deadline"):
        client.generate_structured_json("prompt", turn_calls_used=0)
    assert captured["timeout_ms"] == 12500
