from __future__ import annotations

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

        city_auto, _, region_auto, _ = resolve_location(
            poi_city=None,
            poi_address=brief,
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
        if not dishes and c0 and c0.dishes:
            dishes = c0.dishes[:2]
        dish_focus = ", ".join(dishes[:2]) if dishes else (effective_filters.food_category or "món ăn đặc trưng")
        city_focus = (effective_filters.city_norm or (c0.city_norm if c0 else None) or "địa phương").title()
        fmt = effective_filters.video_format or "Review quán ăn"

        ref_hook_0 = c0.hook_text[:110] if (c0 and c0.hook_text) else f"Tìm hiểu {dish_focus} tại {city_focus}"
        hook_options = [
            f"Nếu quay về {dish_focus} tại {city_focus}, bạn muốn kiểm tra hương vị hay mức giá trước?",
            f"Cùng lên ý tưởng tìm hiểu {dish_focus}: cần ghi lại điều gì để người xem tự đánh giá?",
            (f"Mở đầu tham khảo từ kho @{c0.citation.author_handle}: '{ref_hook_0}'"
             if c0 and c0.hook_text.strip() else f"Gợi ý mở đầu sáng tạo: '{ref_hook_0}'"),
        ]

        # Whitespace-token pacing is an estimate, not measured acoustic alignment.
        wps = max(2.0, min(benchmark.median_word_per_second, 5.0))
        target_words = max(55, int(round(target_duration_sec * wps)))

        beat1_text = (
            f"Hôm nay mình lên ý tưởng tìm hiểu {dish_focus} tại {city_focus}. "
            "Khi quay thực tế, mình sẽ ghi lại món ăn và bảng giá trước khi đưa ra nhận xét. "
            "Bạn muốn biết điều gì về món này?"
        )
        beat2_text = (
            "Đây là thông tin trong nguồn cũ, cần kiểm tra lại khi đến quay. "
            "Mình sẽ ghi hình phần chế biến nếu được phép và mô tả đúng những gì quan sát được."
        )
        beat3_text = (
            "Khi thử món, mình sẽ tách nhận xét về hương vị, khẩu phần và mức giá đang niêm yết. "
            "Những nhận định này cần trải nghiệm thực tế trước khi đưa vào bản quay cuối."
        )
        beat4_text = (
            f"Sau khi quay và kiểm tra thông tin, mình sẽ tổng kết điểm phù hợp của {dish_focus} với nhu cầu người xem. "
            "Phần kết sẽ nêu rõ thời điểm trải nghiệm và điều còn chưa xác minh. "
            "Bạn muốn mình tìm hiểu thêm chi tiết nào?"
        )

        # Pad middle beat slightly if target_duration_sec > 55s so pacing matches target duration
        current_words = sum(len(t.split()) for t in (beat1_text, beat2_text, beat3_text, beat4_text))
        if target_words - current_words >= 25 and c2 and c2.transcript_excerpt:
            beat3_text += (
                " Có thể bổ sung cảnh bảng giá, khẩu phần và phần trả lời của người bán nếu được đồng ý. "
                "Mình sẽ ghi rõ thông tin nào được quan sát và thông tin nào chỉ lấy từ nguồn tham khảo."
            )

        # Keep short requests within their spoken-word budget. Longer drafts may
        # deliberately fail the timing check instead of padding with invented facts.
        dialogue_texts = [beat1_text, beat2_text, beat3_text, beat4_text]
        budgets = [max(1, target_words // 4)] * 3
        budgets.append(max(1, target_words - sum(budgets)))
        citation_ids: list[list[str]] = []
        for idx, (card, budget) in enumerate(zip([c0, c0, c1, c2], budgets)):
            if not card:
                candidates: list[str] = []
            elif idx == 0:
                candidates = [card.hook_text, *card.body_beats, card.transcript_excerpt, card.cta_text]
            elif idx == 1:
                candidates = [*card.body_beats, card.transcript_excerpt, card.hook_text, card.cta_text]
            elif idx == 2:
                candidates = [*card.body_beats[1:], *card.body_beats[:1], card.transcript_excerpt, card.hook_text, card.cta_text]
            else:
                candidates = [card.cta_text, *card.body_beats, card.transcript_excerpt, card.hook_text]
            excerpt = next((text for text in candidates if text.strip()), "")
            # Attribute only content actually incorporated in this beat. Bound
            # the excerpt before shortening so its attribution cannot be cut off.
            excerpt = " ".join(excerpt.split()[:min(12, max(1, budget - 4))])
            if card and excerpt:
                dialogue_texts[idx] = f'Nguồn cũ: "{excerpt}" ' + dialogue_texts[idx]
                citation_ids.append([card.citation.video_id])
            else:
                citation_ids.append([])
        if sum(len(text.split()) for text in dialogue_texts) > target_words:
            dialogue_texts = [" ".join(text.split()[:budget]) for text, budget in zip(dialogue_texts, budgets)]
        beat1_text, beat2_text, beat3_text, beat4_text = dialogue_texts

        if fmt == "Hướng dẫn nấu ăn":
            setting = "Gian bếp gia đình gọn gàng, ánh sáng chếch 45 độ chiếu rõ thớt sơ chế và chảo nấu."
            cam_angles = [
                "Góc top-down 90 độ trên bàn sơ chế nguyên liệu trong 4 giây mở đầu",
                "Góc cận 45 độ bắt trọn khoảnh khắc áp chảo / nước sốt sôi sệt lại",
                "Cận cảnh gắp thành phẩm ra đĩa trắng ăn kèm cơm nóng ở cuối video",
            ]
        else:
            setting = f"Không gian trải nghiệm thực tế tại {city_focus}, ưu tiên bàn gần nguồn sáng tự nhiên."
            cam_angles = [
                "3 giây đầu: cận cảnh 45 độ món chính vừa bốc khói đặt xuống bàn trước khi quay mặt người",
                "Góc POV gắp/cắt đôi món ăn để lộ nhân hoặc kết cấu bên trong và chấm ngập nước sốt",
                "Cảnh trung (medium shot) toàn bàn ăn kèm bảng giá hoặc không gian quán làm bằng chứng thực tế",
            ]

        hashtags = benchmark.top_hashtags[:6] or ["ancungtiktok", "reviewanngon", "foodtiktok"]
        return {
            "draft_status": "creative_draft",
            "grounding_verified": False,
            "hook_options": hook_options,
            "caption_draft": f"Bản nháp về {dish_focus} tại {city_focus}, lấy ý tưởng từ nguồn tham khảo lịch sử; cần kiểm chứng trước khi quay.",
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
            ret_resp = self.retrieval.search(
                RetrievalRequest(
                    query=request.brief,
                    mode="hybrid_rrf",
                    top_k=request.top_k_evidence,
                    rerank=True,
                    filters=effective_filters,
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
