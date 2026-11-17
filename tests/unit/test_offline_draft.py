from __future__ import annotations

import pytest

from packages.data_contracts.analytics import NicheBenchmarkSummary
from packages.data_contracts.query import NicheQueryFilter
from packages.data_contracts.retrieval import EvidenceCard, VideoCitation
from packages.llm import recalculate_timeline_and_verify
from packages.script_engine.service import GroundedScriptEngine


@pytest.fixture
def draft_inputs() -> tuple[NicheBenchmarkSummary, EvidenceCard]:
    benchmark = NicheBenchmarkSummary(
        matched_videos=10, transcribed_videos=10, poi_tagged_videos=0, median_plays=1000, p75_plays=2000,
        median_engagement_rate=0.1, duration_q25_sec=30, duration_median_sec=45, duration_q75_sec=60,
        median_word_per_second=3, hashtag_q25=2, hashtag_q75=5, top_hashtags=[], top_posting_hours=[],
        top_poi_venues=[], applied_filters={}, timings_ms={},
    )
    card = EvidenceCard(
        rank=1, score=1, lexical_score=1, citation=VideoCitation(
            video_id="v1", author_handle="fixture", tiktok_url="https://www.tiktok.com/@fixture/video/v1",
            play_count=1000, viral_multiplier=1, engagement_rate=0.1,
        ), video_format="Review món ăn", food_category="Ẩm thực Tổng hợp", dishes=["phở"], price_tier="unspecified",
        occasions=[], duration_sec=45, duration_bucket="short_20_45s", hook_text="Một đoạn mở đầu tham khảo.",
        body_beats=["Người dẫn giới thiệu món ăn."], cta_text="", transcript_excerpt="Một đoạn mở đầu tham khảo.",
    )
    return benchmark, card


def test_offline_draft_uses_reference_as_inspiration_without_inventing_firsthand_facts(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, card = draft_inputs
    engine = object.__new__(GroundedScriptEngine)
    draft = engine._build_offline_grounded_draft("Review phở", 45, benchmark, [card], NicheQueryFilter())
    assert draft["draft_status"] == "creative_draft"
    assert draft["grounding_verified"] is False
    assert "nguồn tham khảo" in draft["caption_draft"].lower()
    dialogue = " ".join(beat["dialogue"] for beat in draft["beats"])
    assert "nguyên liệu được chuẩn bị rất tươi" not in dialogue
    assert "mức giá này hoàn toàn hợp lý" not in dialogue
    assert "mình ghé trải nghiệm" not in dialogue


def test_empty_source_text_cannot_supply_offline_citations(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, card = draft_inputs
    card = card.model_copy(update={"body_beats": [], "hook_text": "", "cta_text": "", "transcript_excerpt": ""})
    draft = object.__new__(GroundedScriptEngine)._build_offline_grounded_draft(
        "Review phở", 45, benchmark, [card], NicheQueryFilter(),
    )
    assert all(beat["cited_video_ids"] == [] for beat in draft["beats"])
    _, report = recalculate_timeline_and_verify(draft["beats"], draft["hook_options"], 45, 3, {"v1"})
    assert report.passed is False


@pytest.mark.parametrize("duration", [10, 45, 120])
def test_each_offline_citation_has_a_visible_source_excerpt(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard], duration: int,
) -> None:
    benchmark, template = draft_inputs
    excerpts = {"v1": "first_source_span", "v2": "second_source_span", "v3": "third_source_span"}
    cards = [template.model_copy(update={
        "citation": template.citation.model_copy(update={"video_id": video_id}),
        "body_beats": [text], "hook_text": "", "cta_text": "", "transcript_excerpt": text,
    }) for video_id, text in excerpts.items()]
    draft = object.__new__(GroundedScriptEngine)._build_offline_grounded_draft(
        "Review phở", duration, benchmark, cards, NicheQueryFilter(),
    )
    for beat in draft["beats"]:
        assert len(beat["cited_video_ids"]) == 1
        for video_id in beat["cited_video_ids"]:
            assert excerpts[video_id] in beat["dialogue"]
