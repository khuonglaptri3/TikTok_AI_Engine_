from __future__ import annotations

import re
from itertools import product
from typing import Any

from packages.analytics import NicheAnalyticsEngine
from packages.common.logging import StageTimer
from packages.data_contracts.analytics import NicheBenchmarkSummary
from packages.data_contracts.query import (
    NicheQueryFilter,
    RetrievalRequest,
    ScriptGenerationRequest,
)
from packages.data_contracts.retrieval import EvidenceCard
from packages.data_contracts.script import GroundedScriptResponse, ShootingAdvice
from packages.llm import (
    BoundedGeminiClient,
    build_grounded_script_prompt,
    check_fnb_domain_relevance,
    recalculate_timeline_and_verify,
)
from packages.retrieval import HybridRetrievalService
from packages.taxonomy import (
    classify_duration_bucket,
    extract_dishes_from_text,
    extract_occasions,
    extract_price_tier,
    infer_video_format,
    map_food_category,
    resolve_location,
)

_DISH_ORIGIN_CITY_PHRASES: re.Pattern[str] = re.compile(
    r"(?i)\b(?:"
    r"bún\s+bò\s+huế|nem\s+nướng\s+nha\s+trang|bánh\s+mì\s+(?:cay\s+)?hải\s+phòng|"
    r"cơm\s+gà\s+hội\s+an|cao\s+lầu\s+hội\s+an|hủ\s+tiếu\s+mỹ\s+tho|"
    r"(?:xôi\s+cua|bánh\s+tầm(?:\s+cay)?|cua)\s+cà\s+mau|"
    r"(?:chuẩn\s+vị|hương\s+vị|phong\s+cách|kiểu)\s+(?:hà\s+nội|sài\s+gòn|huế|đà\s+nẵng|nha\s+trang|cà\s+mau)"
    r")\b"
)

_NON_CULINARY_SPAN_MARKERS: tuple[str, ...] = (
    "bài hát ",
    "bài hát thể hiện",
    "lời bài hát",
    "ca khúc ",
    "giai điệu nhẹ nhàng",
    "giai điệu sôi động",
    "âm nhạc tạo",
    "không tìm thấy transcript",
    "[please insert",
    "insert the vietnamese transcript",
)


_TRIVIAL_SIGNOFF_RE: re.Pattern[str] = re.compile(
    r"(?i)^[\s.,!?;:\-–—]*(?:bye(?:\s+bye)?|bái\s+bai|tạm\s+biệt|haha+|hihi+|hehe+|ok(?:ay)?)(?:\s+(?:nha|nhé|mọi\s+người|cả\s+nhà))?[\s.,!?;:\-–—]*$"
)


def _is_usable_culinary_span(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    if _TRIVIAL_SIGNOFF_RE.match(cleaned):
        return False
    lowered = cleaned.lower()
    return not any(marker in lowered for marker in _NON_CULINARY_SPAN_MARKERS)


class GroundedScriptEngine:
    """Orchestrates Niche Micro-Benchmarking + Hybrid Evidence Retrieval + Grounded Script Synthesis."""

    def __init__(
        self,
        analytics_engine: NicheAnalyticsEngine,
        retrieval_service: HybridRetrievalService,
        gemini_client: BoundedGeminiClient,
    ) -> None:
        self.analytics = analytics_engine
        self.retrieval = retrieval_service
        self.gemini = gemini_client

    def _infer_effective_filters(
        self,
        brief: str,
        explicit: NicheQueryFilter,
        target_duration_sec: int | None,
    ) -> NicheQueryFilter:
        inferred_fmt = explicit.video_format or infer_video_format(
            legacy_cat=None,
            desc=brief,
            transcript="",
            poi_name=None,
            is_ec_video=("giỏ hàng" in brief.lower()),
        )
        dishes = extract_dishes_from_text(brief)
        inferred_cat = explicit.food_category or map_food_category(dishes, brief, None)
        inferred_price = explicit.price_tier or extract_price_tier(brief, inferred_fmt)
        if inferred_price == "unspecified":
            inferred_price = None  # type: ignore[assignment]

        occ_list = extract_occasions(brief, inferred_fmt)
        inferred_occ = explicit.occasion or (occ_list[0] if occ_list else None)

        brief_for_location = _DISH_ORIGIN_CITY_PHRASES.sub(" ", brief)
        city_auto, _, region_auto, _ = resolve_location(
            poi_city=None,
            poi_address=brief_for_location,
            llm_city=None,
            llm_district=None,
        )
        inferred_city = explicit.city_norm or city_auto
        inferred_region = explicit.region or (region_auto if region_auto != "unknown" else None)
        inferred_dur = explicit.duration_bucket or (
            classify_duration_bucket(target_duration_sec) if target_duration_sec else None
        )

        return NicheQueryFilter(
            video_format=inferred_fmt,
            food_category=inferred_cat if inferred_cat != "Ẩm thực Tổng hợp" else explicit.food_category,
            price_tier=inferred_price,
            occasion=inferred_occ,
            duration_bucket=inferred_dur,
            city_norm=inferred_city,
            region=inferred_region,
        )

    @staticmethod
    def _build_retrieval_filters(
        explicit: NicheQueryFilter,
        effective: NicheQueryFilter,
    ) -> NicheQueryFilter:
        """Keep explicit caller filters + inferred geographic scope strict without soft-facet starvation."""
        return NicheQueryFilter(
            video_format=explicit.video_format,
            food_category=explicit.food_category,
            price_tier=explicit.price_tier,
            occasion=explicit.occasion,
            duration_bucket=explicit.duration_bucket,
            city_norm=explicit.city_norm or effective.city_norm,
            region=explicit.region or effective.region,
        )

    def _build_offline_grounded_draft(
        self,
        brief: str,
        target_duration_sec: int,
        benchmark: NicheBenchmarkSummary,
        evidence_cards: list[EvidenceCard],
        effective_filters: NicheQueryFilter,
    ) -> dict[str, Any]:
        c0 = evidence_cards[0] if len(evidence_cards) > 0 else None
        c1 = evidence_cards[1] if len(evidence_cards) > 1 else c0
        c2 = evidence_cards[2] if len(evidence_cards) > 2 else c0

        dishes = extract_dishes_from_text(brief)
        fallback_cat = (
            effective_filters.food_category
            if effective_filters.food_category and effective_filters.food_category != "Ẩm thực Tổng hợp"
            else "món ăn theo chủ đề đã chọn"
        )
        dish_focus = ", ".join(dishes[:2]) if dishes else fallback_cat
        explicit_city = (effective_filters.city_norm or "").strip()
        city_focus = explicit_city.title() if explicit_city else ""
        loc_clause = f" tại {city_focus}" if city_focus else ""
        setting_loc = f" tại {city_focus}" if city_focus else ""
        fmt = effective_filters.video_format or "Review quán ăn"

        usable_hook_0 = (
            c0.hook_text[:110]
            if (c0 and _is_usable_culinary_span(c0.hook_text))
            else f"Tìm hiểu {dish_focus}{loc_clause}"
        )
        hook_options = [
            f"Nếu quay về {dish_focus}{loc_clause}, bạn muốn kiểm tra hương vị hay mức giá trước?",
            f"Cùng lên ý tưởng tìm hiểu {dish_focus}: cần ghi lại điều gì để người xem tự đánh giá?",
            (
                f"Mở đầu tham khảo từ kho @{c0.citation.author_handle}: '{usable_hook_0}'"
                if (c0 and _is_usable_culinary_span(c0.hook_text))
                else f"Gợi ý mở đầu sáng tạo: '{usable_hook_0}'"
            ),
        ]

        # Whitespace-token pacing is an estimate, not measured acoustic alignment.
        wps = max(2.0, min(float(benchmark.median_word_per_second or 3.3), 5.0))
        raw_target_words = max(12, int(round(target_duration_sec * wps)))
        target_words = max(55, raw_target_words)

        beat_compact: list[str] = [
            "Cần kiểm chứng thêm khi quay.",
            "Chi tiết cần đối chiếu trực tiếp.",
            "Nhận xét cần trải nghiệm thực tế.",
            "Tổng kết sau khi kiểm tra món.",
        ]
        beat_sentence_ladder: list[list[str]] = [
            [
                f"Mình đang lên ý tưởng tìm hiểu {dish_focus}{loc_clause}.",
                "Khi quay thực tế, mình sẽ ghi lại món ăn và bảng giá trước khi nhận xét.",
                "Khung giờ phục vụ và bối cảnh thực tế cũng cần xác minh tại chỗ.",
                "Mình ưu tiên nêu rõ điều kiện ghi hình để người xem dễ đối chiếu.",
                "Bạn muốn biết thêm điều gì về món này?",
            ],
            [
                "Đây là chi tiết từ nguồn cũ, cần kiểm tra lại khi đến quay.",
                "Mình sẽ ghi hình phần chế biến nếu được phép và mô tả đúng quan sát.",
                "Nguyên liệu và định lượng cần đối chiếu trực tiếp tại chỗ.",
                "Các bước chuẩn bị hoặc cách phục vụ sẽ được ghi chú rõ ràng theo thực tế.",
                "Mọi thông tin chưa rõ sẽ được đánh dấu cần kiểm chứng thêm.",
            ],
            [
                "Khi thử món, mình sẽ tách nhận xét về hương vị, khẩu phần và giá niêm yết.",
                "Những nhận định này cần trải nghiệm thực tế trước khi đưa vào bản cuối.",
                "Có thể bổ sung cảnh bảng giá và phần chia sẻ của người bán nếu được đồng ý.",
                "Độ đậm nhạt và kết cấu món ăn nên mô tả cụ thể thay vì khen chung chung.",
                "Người xem có thể đối chiếu hình ảnh cận cảnh để tự đánh giá.",
            ],
            [
                f"Sau khi kiểm tra, mình sẽ tổng kết điểm phù hợp của {dish_focus}.",
                "Phần kết sẽ nêu rõ thời điểm trải nghiệm và điều còn chưa xác minh.",
                "Nếu mức giá hoặc thực đơn thay đổi, bản quay thực tế sẽ cập nhật lại.",
                "Các thông tin tham khảo lịch sử chỉ đóng vai trò gợi ý ban đầu.",
                "Bạn muốn mình tìm hiểu thêm chi tiết nào?",
            ],
        ]

        budgets = [max(1, target_words // 4)] * 3
        budgets.append(max(1, target_words - sum(budgets)))

        def _candidate_spans(card: EvidenceCard, beat_idx: int) -> list[str]:
            if beat_idx == 0:
                raw = [card.hook_text, *card.body_beats, card.transcript_excerpt, card.cta_text]
            elif beat_idx == 1:
                raw = [*card.body_beats, card.transcript_excerpt, card.hook_text, card.cta_text]
            elif beat_idx == 2:
                raw = [*card.body_beats[1:], *card.body_beats[:1], card.transcript_excerpt, card.hook_text, card.cta_text]
            else:
                raw = [card.cta_text, *card.body_beats, card.transcript_excerpt, card.hook_text]
            return [s for s in raw if _is_usable_culinary_span(s)]

        prefixes: list[str] = []
        citation_ids: list[list[str]] = []
        excerpt_cap = 8 if raw_target_words <= 115 else 10
        for idx, (preferred_card, budget) in enumerate(zip([c0, c0, c1, c2], budgets)):
            chosen_card: EvidenceCard | None = None
            excerpt = ""
            search_order = (
                [preferred_card, *[c for c in evidence_cards if c is not preferred_card]]
                if preferred_card is not None
                else []
            )
            for candidate_card in search_order:
                if candidate_card is None:
                    continue
                spans = _candidate_spans(candidate_card, idx)
                if spans:
                    chosen_card = candidate_card
                    excerpt = spans[0]
                    break
            max_excerpt_words = min(excerpt_cap, max(1, budget - 6))
            excerpt = " ".join(excerpt.split()[:max_excerpt_words]).rstrip(",;:")
            if chosen_card and excerpt:
                prefixes.append(f'Nguồn cũ: "{excerpt}". ')
                citation_ids.append([chosen_card.citation.video_id])
            else:
                prefixes.append("")
                citation_ids.append([])

        # Assemble complete sentences per beat (never truncating mid-sentence) to match target_duration_sec at wps
        beat_options: list[list[str]] = []
        beat_durs: list[list[float]] = []
        for i in range(4):
            opts_i = [beat_compact[i]] + [
                " ".join(beat_sentence_ladder[i][:k]) for k in range(1, len(beat_sentence_ladder[i]) + 1)
            ]
            beat_options.append(opts_i)
            beat_durs.append(
                [max(3.0, len((prefixes[i] + body).split()) / wps) for body in opts_i]
            )

        tol_sec = max(2.0, float(target_duration_sec) * 0.05)
        best_choice: tuple[int, int, int, int] = (1, 1, 1, 1)
        best_key: tuple[int, float, int, float] | None = None
        for choice in product(range(len(beat_options[0])), repeat=4):
            est_sec = round(sum(beat_durs[i][choice[i]] for i in range(4)), 1)
            abs_delta = round(abs(est_sec - float(target_duration_sec)), 3)
            outside_tol = 0 if abs_delta <= tol_sec else 1
            compact_count = sum(1 for k in choice if k == 0)
            spread = float(max(choice) - min(choice))
            # Prefer within-tolerance combinations that avoid compact tier-0 unless needed for short/slow slices
            key = (outside_tol, abs_delta if outside_tol else 0.0, compact_count, abs_delta + 0.05 * spread)
            if best_key is None or key < best_key:
                best_key = key
                best_choice = choice  # type: ignore[assignment]

        dialogue_texts = [
            (prefixes[i] + beat_options[i][best_choice[i]]).strip()
            for i in range(4)
        ]

        beat1_text, beat2_text, beat3_text, beat4_text = dialogue_texts

        if fmt == "Hướng dẫn nấu ăn":
            setting = "Gian bếp gia đình gọn gàng, ánh sáng chếch 45 độ chiếu rõ thớt sơ chế và chảo nấu."
            cam_angles = [
                "Góc top-down 90 độ trên bàn sơ chế nguyên liệu trong 4 giây mở đầu",
                "Góc cận 45 độ bắt trọn khoảnh khắc áp chảo / nước sốt sôi sệt lại",
                "Cận cảnh gắp thành phẩm ra đĩa trắng ăn kèm cơm nóng ở cuối video",
            ]
        else:
            setting = f"Không gian trải nghiệm thực tế{setting_loc}, ưu tiên bàn gần nguồn sáng tự nhiên."
            cam_angles = [
                "3 giây đầu: cận cảnh 45 độ món chính vừa bốc khói đặt xuống bàn trước khi quay mặt người",
                "Góc POV gắp/cắt đôi món ăn để lộ nhân hoặc kết cấu bên trong và chấm ngập nước sốt",
                "Cảnh trung (medium shot) toàn bàn ăn kèm bảng giá hoặc không gian quán làm bằng chứng thực tế",
            ]

        hashtags = benchmark.top_hashtags[:6] or ["ancungtiktok", "reviewanngon", "foodtiktok"]
        caption_loc = f" tại {city_focus}" if city_focus else ""
        return {
            "draft_status": "creative_draft",
            "grounding_verified": False,
            "hook_options": hook_options,
            "caption_draft": f"Bản nháp về {dish_focus}{caption_loc}, lấy ý tưởng từ nguồn tham khảo lịch sử; cần kiểm chứng trước khi quay.",
            "recommended_hashtags": hashtags,
            "setting": setting,
            "persona_tone": "Bản nháp sáng tạo; tách nguồn tham khảo và nhận xét cần trải nghiệm thực tế",
            "beats": [
                {
                    "section_title": "1. Hook mở đầu (0-5s giữ chân)",
                    "visual_angle": cam_angles[0],
                    "dialogue": beat1_text,
                    "cited_video_ids": citation_ids[0],
                },
                {
                    "section_title": "2. Bối cảnh & Cận cảnh chế biến",
                    "visual_angle": cam_angles[1],
                    "dialogue": beat2_text,
                    "cited_video_ids": citation_ids[1],
                },
                {
                    "section_title": "3. Trải nghiệm hương vị & Giá trị thực",
                    "visual_angle": cam_angles[2],
                    "dialogue": beat3_text,
                    "cited_video_ids": citation_ids[2],
                },
                {
                    "section_title": "4. Tổng kết & Kêu gọi tương tác (CTA)",
                    "visual_angle": "Góc cận biểu cảm gật đầu xác nhận kèm text tóm tắt điểm cộng trên màn hình",
                    "dialogue": beat4_text,
                    "cited_video_ids": citation_ids[3],
                },
            ],
            "shooting_advice": {
                "camera_angles": cam_angles,
                "lighting_and_audio": [
                    "Dùng micro cài áo thu rõ giọng nói, giữ lại 15-20% âm thanh ASMR tự nhiên khi cắt/nhai giòn hoặc xèo xèo",
                    "Tránh đèn vàng gắt chiếu thẳng từ đỉnh đầu làm xỉn màu nước dùng và rau sống",
                ],
                "pacing_and_editing": [
                    f"Tốc độ thoại mục tiêu của ngách: ~{benchmark.median_word_per_second} từ/giây; cắt bỏ toàn bộ khoảng nghỉ thở thừa >0.3s",
                    f"Phân bố thời lượng lịch sử của lát cắt: {benchmark.duration_q25_sec:.0f}s - {benchmark.duration_q75_sec:.0f}s (trung vị {benchmark.duration_median_sec:.0f}s); không chứng minh thời lượng tối ưu",
                ],
            },
        }

    def generate(self, request: ScriptGenerationRequest) -> GroundedScriptResponse:
        timer = StageTimer()

        with timer.measure("domain_gate_ms"):
            check_fnb_domain_relevance(request.brief)
            effective_filters = self._infer_effective_filters(
                brief=request.brief,
                explicit=request.filters,
                target_duration_sec=request.target_duration_sec,
            )

        with timer.measure("benchmark_ms"):
            benchmark = self.analytics.compute_benchmark(effective_filters)

        with timer.measure("retrieval_ms"):
            retrieval_filters = self._build_retrieval_filters(
                explicit=request.filters,
                effective=effective_filters,
            )
            ret_resp = self.retrieval.search(
                RetrievalRequest(
                    query=request.brief,
                    mode="hybrid_rrf",
                    top_k=request.top_k_evidence,
                    rerank=True,
                    filters=retrieval_filters,
                )
            )
            evidence_cards = ret_resp.items

        target_dur = request.target_duration_sec or int(
            max(20, min(90, round(benchmark.duration_median_sec or 45.0)))
        )

        if request.generation_mode == "gemini_free":
            with timer.measure("llm_synthesis_ms"):
                prompt = build_grounded_script_prompt(
                    brief=request.brief,
                    target_duration_sec=target_dur,
                    benchmark=benchmark,
                    evidence_cards=evidence_cards,
                )
                draft = self.gemini.generate_structured_json(prompt, turn_calls_used=0)
                model_used = self.gemini.settings.gemini_fast_model
        else:
            with timer.measure("blueprint_synthesis_ms"):
                draft = self._build_offline_grounded_draft(
                    brief=request.brief,
                    target_duration_sec=target_dur,
                    benchmark=benchmark,
                    evidence_cards=evidence_cards,
                    effective_filters=effective_filters,
                )
                model_used = "offline_evidence_blueprint_v1"

        with timer.measure("guardrail_ms"):
            valid_ids = {card.citation.video_id for card in evidence_cards}
            beats_obj = draft.get("beats")
            raw_beats: list[dict[str, Any]] = (
                [b for b in beats_obj if isinstance(b, dict)] if isinstance(beats_obj, list) else []
            )
            hook_opts = [str(h) for h in (draft.get("hook_options") or []) if str(h).strip()]
            verified_beats, guardrail_report = recalculate_timeline_and_verify(
                raw_beats=raw_beats,
                hook_options=hook_opts,
                target_duration_sec=float(target_dur),
                niche_wps=benchmark.median_word_per_second,
                valid_evidence_ids=valid_ids,
            )

            sa_obj = draft.get("shooting_advice")
            sa_raw: dict[str, Any] = sa_obj if isinstance(sa_obj, dict) else {}
            shooting = ShootingAdvice(
                camera_angles=[str(x) for x in (sa_raw.get("camera_angles") or ["Cận cảnh 45 độ món ăn"])],
                lighting_and_audio=[str(x) for x in (sa_raw.get("lighting_and_audio") or ["Ánh sáng tự nhiên, thu âm rõ"])],
                pacing_and_editing=[str(x) for x in (sa_raw.get("pacing_and_editing") or ["Cắt nhịp nhanh 2s/cảnh đầu"])],
            )
            rec_tags = [
                str(t).lstrip("#").lower()
                for t in (draft.get("recommended_hashtags") or benchmark.top_hashtags[:6])
                if str(t).strip()
            ]

        return GroundedScriptResponse(
            generation_mode=request.generation_mode,
            model_used=model_used,
            hook_options=hook_opts or ["Khám phá món ngon thực tế hôm nay!"],
            caption_draft=str(draft.get("caption_draft") or request.brief[:140]),
            recommended_hashtags=rec_tags[:8],
            setting=str(draft.get("setting") or "Không gian quán ăn / bếp thực tế"),
            persona_tone=str(draft.get("persona_tone") or "Chân thực, giàu trải nghiệm"),
            beats=verified_beats,
            shooting_advice=shooting,
            niche_benchmark=benchmark,
            evidence_cards=evidence_cards,
            guardrail=guardrail_report,
            timings_ms=timer.finalize(),
        )
