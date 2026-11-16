from __future__ import annotations

from typing import Any

from packages.analytics import NicheAnalyticsEngine
from packages.common.logging import StageTimer
from packages.data_contracts.analytics import NicheBenchmarkSummary
from packages.data_contracts.query import NicheQueryFilter, RetrievalRequest, ScriptGenerationRequest
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

        id0 = c0.citation.video_id if c0 else ""
        id1 = c1.citation.video_id if c1 else id0
        id2 = c2.citation.video_id if c2 else id0

        ref_hook_0 = c0.hook_text[:110] if (c0 and c0.hook_text) else f"Khám phá {dish_focus} đáng thử tại {city_focus}"
        hook_options = [
            f"Một tọa độ {dish_focus} tại {city_focus} đang được dân sành ăn truyền tai nhau — thực tế có xứng đáng với mức giá?",
            f"Cầm ngân sách hợp lý đi thử {dish_focus} theo gợi ý thực tế: phần ăn đầy đặn và hương vị ra sao?",
            f"Lấy cảm hứng mở đầu trực diện như @{c0.citation.author_handle if c0 else 'creator'}: '{ref_hook_0}'",
        ]

        # Calibrate word count per beat to match target_duration_sec * median_wps
        wps = max(2.4, min(benchmark.median_word_per_second, 4.2))
        target_words = max(55, int(round(target_duration_sec * wps)))

        beat1_text = (
            f"Hôm nay mình ghé trải nghiệm {dish_focus} tại {city_focus} theo đúng đề bài '{brief[:90]}'. "
            f"Ngay từ cái nhìn đầu tiên, phần nguyên liệu được chuẩn bị rất tươi và lên màu bắt mắt."
        )
        ev_detail_1 = (
            c0.body_beats[0]
            if (c0 and c0.body_beats)
            else "Phần nước dùng và gia vị được cân chỉnh vừa vặn, giữ được độ tươi tự nhiên của nguyên liệu."
        )
        beat2_text = (
            f"Điểm đáng chú ý đầu tiên nằm ở khâu chế biến và bày trí: {ev_detail_1} "
            f"Khi quay cận cảnh lúc món vừa dọn ra còn nóng hổi, mùi thơm dậy lên rất rõ ràng."
        )
        ev_detail_2 = (
            c1.body_beats[0]
            if (c1 and c1.body_beats)
            else "Kết cấu món ăn có sự tương phản rõ giữa độ giòn bên ngoài và vị đậm đà bên trong."
        )
        beat3_text = (
            f"Thử trực tiếp từng thành phần để kiểm chứng chất lượng: {ev_detail_2} "
            f"Xét về khẩu phần và trải nghiệm thực tế trong phân khúc {effective_filters.price_tier or 'phổ thông'}, mức giá này hoàn toàn hợp lý."
        )
        beat4_text = (
            f"Tổng kết lại, đây là lựa chọn {dish_focus} rất đáng lưu vào danh sách khi bạn cần một bữa ăn chất lượng tại {city_focus}. "
            f"Bạn đã từng thử kiểu chế biến này chưa, bình luận địa chỉ quen thuộc của bạn bên dưới nhé!"
        )

        # Pad middle beat slightly if target_duration_sec > 55s so pacing matches target duration
        current_words = sum(len(t.split()) for t in (beat1_text, beat2_text, beat3_text, beat4_text))
        if target_words - current_words >= 25 and c2 and c2.transcript_excerpt:
            beat3_text += (
                " Ngoài ra bạn nên đi vào khung giờ sớm một chút để món lên nhanh, giữ trọn độ nóng giòn "
                "và dễ chọn được góc ngồi thoáng đãng khi đi cùng bạn bè."
            )

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
            "hook_options": hook_options,
            "caption_draft": f"Trải nghiệm thực tế {dish_focus} tại {city_focus} — chi tiết hương vị và mức giá cho mọi người tham khảo!",
            "recommended_hashtags": hashtags,
            "setting": setting,
            "persona_tone": "Chân thực, trực diện vào chất lượng món & giá cả, miêu tả vị giác cụ thể",
            "beats": [
                {
                    "section_title": "1. Hook mở đầu (0-5s giữ chân)",
                    "visual_angle": cam_angles[0],
                    "dialogue": beat1_text,
                    "cited_video_ids": [v for v in [id0] if v],
                },
                {
                    "section_title": "2. Bối cảnh & Cận cảnh chế biến",
                    "visual_angle": cam_angles[1],
                    "dialogue": beat2_text,
                    "cited_video_ids": [v for v in [id0, id1] if v][:2],
                },
                {
                    "section_title": "3. Trải nghiệm hương vị & Giá trị thực",
                    "visual_angle": cam_angles[2],
                    "dialogue": beat3_text,
                    "cited_video_ids": [v for v in [id1, id2] if v][:2],
                },
                {
                    "section_title": "4. Tổng kết & Kêu gọi tương tác (CTA)",
                    "visual_angle": "Góc cận biểu cảm gật đầu xác nhận kèm text tóm tắt điểm cộng trên màn hình",
                    "dialogue": beat4_text,
                    "cited_video_ids": [v for v in [id2] if v],
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
                    f"Thời lượng tối ưu của ngách nằm trong khoảng {benchmark.duration_q25_sec:.0f}s - {benchmark.duration_q75_sec:.0f}s (trung vị {benchmark.duration_median_sec:.0f}s)",
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
                draft = self.gemini.generate_structured_json(prompt)
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
