from __future__ import annotations

import pytest

from packages.data_contracts.analytics import NicheBenchmarkSummary
from packages.data_contracts.query import (
    NicheQueryFilter,
    RetrievalRequest,
    ScriptGenerationRequest,
)
from packages.data_contracts.retrieval import EvidenceCard, RetrievalResponse, VideoCitation
from packages.llm import BoundedGeminiClient, recalculate_timeline_and_verify
from packages.common.settings import AppSettings
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


def test_offline_draft_selects_role_specific_source_excerpts_per_beat(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, template = draft_inputs
    cards = [
        template.model_copy(
            update={
                "citation": template.citation.model_copy(update={"video_id": vid}),
                "hook_text": f"Hook_{vid}",
                "body_beats": [f"Body1_{vid}", f"Body2_{vid}"],
                "cta_text": f"CTA_{vid}",
                "transcript_excerpt": f"Excerpt_{vid}",
            }
        )
        for vid in ("v1", "v2", "v3")
    ]
    draft = object.__new__(GroundedScriptEngine)._build_offline_grounded_draft(
        "Review phở bò Hà Nội",
        60,
        benchmark,
        cards,
        NicheQueryFilter(),
    )
    assert "Hook_v1" in draft["beats"][0]["dialogue"]
    assert "Body1_v1" in draft["beats"][1]["dialogue"]
    assert "Hook_v1" not in draft["beats"][1]["dialogue"]
    assert "Body2_v2" in draft["beats"][2]["dialogue"] or "Body1_v2" in draft["beats"][2]["dialogue"]
    assert "CTA_v3" in draft["beats"][3]["dialogue"]


def test_offline_draft_does_not_fabricate_city_from_evidence_card_or_dish_name(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, card = draft_inputs
    card_danang = card.model_copy(update={"city_norm": "đà nẵng", "dishes": ["mì cay"]})
    engine = object.__new__(GroundedScriptEngine)

    # 1. Dish-origin city inside "bún bò Huế tại nhà" must not become a venue city filter
    inferred = engine._infer_effective_filters(
        brief="Hướng dẫn nấu bún bò Huế tại nhà đơn giản tiết kiệm",
        explicit=NicheQueryFilter(),
        target_duration_sec=50,
    )
    assert inferred.city_norm is None

    # 2. Brief with no city must not claim filming in card.city_norm ("Đà Nẵng")
    draft = engine._build_offline_grounded_draft(
        "Mukbang mì cay hải sản cấp độ 7",
        45,
        benchmark,
        [card_danang],
        NicheQueryFilter(video_format="Mukbang"),
    )
    assert "đà nẵng" not in draft["beats"][0]["dialogue"].lower()
    assert "đà nẵng" not in draft["caption_draft"].lower()


def test_offline_draft_never_truncates_mid_sentence_on_35s_target(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, card = draft_inputs
    card_long = card.model_copy(
        update={
            "hook_text": "Quán trà sữa gần cổng trường đông học sinh mỗi buổi chiều tan học.",
            "body_beats": [
                "Trà sữa matcha kem cheese có vị béo nhẹ và thơm mùi trà xanh.",
                "Mức giá niêm yết từ hai mươi lăm nghìn đồng một ly cỡ vừa.",
            ],
            "cta_text": "Các bạn học sinh quanh khu vực này có thể ghé thử sau giờ học.",
        }
    )
    draft = object.__new__(GroundedScriptEngine)._build_offline_grounded_draft(
        "Review quán trà sữa matcha kem cheese gần cổng trường cho học sinh",
        35,
        benchmark,
        [card_long],
        NicheQueryFilter(video_format="Review quán ăn"),
    )
    for beat in draft["beats"]:
        text = beat["dialogue"].strip()
        assert text.endswith((".", "?", "!")), f"Mid-sentence truncation: {text!r}"
    _, report = recalculate_timeline_and_verify(
        draft["beats"], draft["hook_options"], 35.0, benchmark.median_word_per_second, {"v1"}
    )
    assert report.timing_valid is True


def test_offline_draft_skips_music_lyric_summaries_when_selecting_source_excerpt(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, card = draft_inputs
    card_music = card.model_copy(
        update={
            "hook_text": "Bài hát thể hiện niềm khát khao yêu đương và mong muốn gắn bó.",
            "body_beats": [
                "Lời bài hát cho thấy sự sẵn sàng hy sinh vì người mình yêu.",
                "Ốc hương xào bơ tỏi giá 35k một dĩa bán từ chiều tới khuya.",
            ],
            "cta_text": "Ca khúc có giai điệu nhẹ nhàng, dễ thương.",
            "transcript_excerpt": "Ốc hương xào bơ tỏi giá 35k một dĩa bán từ chiều tới khuya.",
        }
    )
    draft = object.__new__(GroundedScriptEngine)._build_offline_grounded_draft(
        "Review quán ốc sinh viên bình dân 35k",
        45,
        benchmark,
        [card_music],
        NicheQueryFilter(video_format="Review quán ăn"),
    )
    joined = " ".join(b["dialogue"].lower() for b in draft["beats"])
    assert "bài hát thể hiện" not in joined
    assert "lời bài hát" not in joined
    assert "ca khúc có giai điệu" not in joined
    assert "ốc hương xào bơ tỏi" in joined


def test_generate_keeps_explicit_and_geo_filters_without_soft_heuristic_retrieval_starvation(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, card = draft_inputs
    captured_retrieval_requests: list[RetrievalRequest] = []
    captured_benchmark_filters: list[NicheQueryFilter] = []

    class _FakeAnalytics:
        def compute_benchmark(self, filters: NicheQueryFilter) -> NicheBenchmarkSummary:
            captured_benchmark_filters.append(filters)
            return benchmark

    class _FakeRetrieval:
        def search(self, req: RetrievalRequest) -> RetrievalResponse:
            captured_retrieval_requests.append(req)
            return RetrievalResponse(
                query=req.query,
                mode=req.mode,
                reranked=True,
                total_candidates=1,
                relaxed_filters=[],
                items=[card],
                timings_ms={},
            )

    engine = GroundedScriptEngine(
        analytics_engine=_FakeAnalytics(),  # type: ignore[arg-type]
        retrieval_service=_FakeRetrieval(),  # type: ignore[arg-type]
        gemini_client=BoundedGeminiClient(settings=AppSettings(gemini_api_key="")),
    )
    engine.generate(
        ScriptGenerationRequest(
            brief="Review bún chả nướng than hoa buổi trưa bình dân ở Ba Đình Hà Nội",
            target_duration_sec=45,
            generation_mode="offline_grounded",
            filters=NicheQueryFilter(price_tier="budget"),
        )
    )
    assert len(captured_benchmark_filters) == 1
    assert captured_benchmark_filters[0].city_norm == "hà nội"
    assert captured_benchmark_filters[0].food_category == "Lẩu & Nướng"

    assert len(captured_retrieval_requests) == 1
    ret_filters = captured_retrieval_requests[0].filters
    # Explicit caller filter + inferred geographic scope stay strict
    assert ret_filters.city_norm == "hà nội"
    assert ret_filters.region == "north"
    assert ret_filters.price_tier == "budget"
    # Unspecified soft heuristic facets must not lock allowed_ids before BM25 + anchor matching
    assert ret_filters.duration_bucket is None
    assert ret_filters.food_category is None
    assert ret_filters.video_format is None


@pytest.mark.parametrize(
    ("target_dur", "wps"),
    [(35, 2.4), (35, 3.0), (40, 2.5), (45, 3.3), (50, 2.5), (50, 3.8), (55, 3.9)],
)
def test_offline_draft_matches_timing_tolerance_across_35s_to_55s_and_varying_wps(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
    target_dur: int,
    wps: float,
) -> None:
    benchmark, card = draft_inputs
    card_realistic = card.model_copy(
        update={
            "hook_text": "Tô phở bò tái lăn nóng hổi nước dùng thơm mùi gừng nướng buổi sáng.",
            "body_beats": [
                "Thịt bò xào nhanh trên chảo gang lửa lớn giữ được độ mềm ngọt.",
                "Nước hầm xương trong veo chan ngập bánh phở mềm kèm hành lá.",
            ],
            "cta_text": "Mọi người đi ngang khu phố này buổi sáng nhớ ghé ăn thử nha.",
        }
    )
    benchmark_var = benchmark.model_copy(update={"median_word_per_second": wps})
    draft = object.__new__(GroundedScriptEngine)._build_offline_grounded_draft(
        "Review phở bò tái lăn buổi sáng",
        target_dur,
        benchmark_var,
        [card_realistic],
        NicheQueryFilter(video_format="Review quán ăn"),
    )
    for beat in draft["beats"]:
        text = beat["dialogue"].strip()
        assert text.endswith((".", "?", "!")), f"Mid-sentence truncation: {text!r}"
    _, report = recalculate_timeline_and_verify(
        draft["beats"], draft["hook_options"], float(target_dur), wps, {"v1"}
    )
    assert report.timing_valid is True, (
        f"target={target_dur}s wps={wps} -> estimated={report.estimated_duration_sec}s delta={report.duration_delta_sec}s"
    )
    assert report.passed is True


def test_offline_draft_filters_extended_music_summaries_and_prompt_placeholders(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, card = draft_inputs
    card_noisy = card.model_copy(
        update={
            "hook_text": "Bài hát mang đến thông điệp về sự lạc quan.",
            "body_beats": [
                "[Please insert the Vietnamese transcript here]",
                "Âm nhạc tạo cảm giác nhẹ nhàng, sâu lắng.",
                "Trà mãng cầu tươi pha chua ngọt vừa miệng giá 25k.",
            ],
            "cta_text": "Bài hát kể về một chàng trai thất tình.",
            "transcript_excerpt": "Trà mãng cầu tươi pha chua ngọt vừa miệng giá 25k.",
        }
    )
    draft = object.__new__(GroundedScriptEngine)._build_offline_grounded_draft(
        "Review trà mãng cầu tươi chua ngọt giải nhiệt buổi trưa",
        40,
        benchmark,
        [card_noisy],
        NicheQueryFilter(video_format="Review quán ăn"),
    )
    joined = " ".join(b["dialogue"].lower() for b in draft["beats"])
    assert "bài hát" not in joined
    assert "âm nhạc tạo" not in joined
    assert "please insert" not in joined
    assert "trà mãng cầu tươi" in joined


def test_offline_draft_does_not_hijack_dish_focus_from_evidence_card_dishes_when_brief_dish_unlisted(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, card = draft_inputs
    card_other = card.model_copy(
        update={"dishes": ["vây cá hồi chiên giòn", "lòng heo luộc"]}
    )
    draft = object.__new__(GroundedScriptEngine)._build_offline_grounded_draft(
        "Hướng dẫn nấu canh chua cá hồi thanh mát không tanh cho bữa cơm nhà",
        45,
        benchmark,
        [card_other],
        NicheQueryFilter(video_format="Hướng dẫn nấu ăn", food_category="Cơm & Món mặn"),
    )
    joined = (draft["caption_draft"] + " " + " ".join(b["dialogue"] for b in draft["beats"])).lower()
    assert "lòng heo luộc" not in joined
    assert "vây cá hồi chiên giòn" not in joined


def test_offline_draft_skips_trivial_signoff_cta_and_falls_back_to_culinary_body_beat(
    draft_inputs: tuple[NicheBenchmarkSummary, EvidenceCard],
) -> None:
    benchmark, card = draft_inputs
    card_signoff = card.model_copy(
        update={
            "hook_text": "Bánh cuốn tráng tay mỏng mướt nóng hổi buổi sáng.",
            "body_beats": [
                "Quán bánh cuốn 83 Đặng Tiến Đông mở cả ngày có chả quế và gà tần.",
                "Nước chấm bánh cuốn pha vừa miệng ăn kèm hành khô tự chiên thơm giòn.",
            ],
            "cta_text": "Haha.",
            "transcript_excerpt": "Bánh cuốn tráng tay mỏng mướt nóng hổi buổi sáng.",
        }
    )
    card_bye = card_signoff.model_copy(
        update={
            "citation": card.citation.model_copy(update={"video_id": "v2"}),
            "cta_text": "Bye bye.",
        }
    )
    draft = object.__new__(GroundedScriptEngine)._build_offline_grounded_draft(
        "Review bánh cuốn nóng nhân thịt mộc nhĩ ăn sáng ở Đống Đa Hà Nội",
        45,
        benchmark,
        [card_signoff, card_bye],
        NicheQueryFilter(video_format="Review quán ăn", city_norm="hà nội"),
    )
    beat4_lower = draft["beats"][3]["dialogue"].lower()
    assert '"haha."' not in beat4_lower
    assert '"bye bye."' not in beat4_lower
    assert "83 đặng tiến đông" in beat4_lower or "nước chấm bánh cuốn" in beat4_lower
