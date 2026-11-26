from __future__ import annotations

import json
from typing import Any

import gradio as gr
import httpx
from fastapi import FastAPI

from apps.demo.presentation import parse_demo_comment_lines
from apps.demo.visuals import (
    render_benchmark_html,
    render_corpus_video_header_html,
    render_disclosure_promo_html,
    render_error_alert_html,
    render_evidence_cards_html,
    render_hero_banner_html,
    render_milestone_evaluations_html,
    render_placeholder_html,
    render_prosody_segments_html,
    render_script_html,
    render_system_status_html,
    render_timings_html,
    render_trust_audit_html,
)
from packages.taxonomy import FOOD_CATEGORIES, OCCASION_LABELS, PRICE_TIERS, VIDEO_FORMATS


def _clean_choice(val: str | None) -> str | None:
    if not val or val == "(Tự động / Tất cả)":
        return None
    return val.strip()


def _build_filters(
    video_format: str | None,
    food_category: str | None,
    price_tier: str | None,
    occasion: str | None,
    city_norm: str | None,
) -> dict[str, str]:
    raw = {
        "video_format": _clean_choice(video_format),
        "food_category": _clean_choice(food_category),
        "price_tier": _clean_choice(price_tier),
        "occasion": _clean_choice(occasion),
        "city_norm": city_norm.strip().lower() if city_norm and city_norm.strip() else None,
    }
    return {k: v for k, v in raw.items() if v is not None}


def _format_video_choice(item: dict[str, Any]) -> tuple[str, str]:
    vid = str(item.get("video_id") or "")
    handle = str(item.get("author_handle") or "creator")
    cmts = int(item.get("comment_count") or 0)
    segs = int(item.get("voice_segment_count") or 0)
    prov = "🎙️ audio" if segs > 0 or item.get("has_prosody_audio") else "💬 text"
    prev = " ".join(str(item.get("caption_preview") or "").split())[:58]
    label = f"{prov} | @{handle} ({cmts} cmts, {segs} utts) — {prev} [{vid}]"
    return (label, vid)


def build_gradio_blocks(api_app: FastAPI) -> gr.Blocks:
    """Build thin 4-tab Gradio workspace calling FastAPI routes over in-process ASGI transport."""

    async def _post_api(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        transport = httpx.ASGITransport(app=api_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://inprocess") as client:
            resp = await client.post(path, json=payload, timeout=45.0)
            return resp.status_code, resp.json()

    async def _get_api(
        path: str,
        params: dict[str, Any] | None = None,
    ) -> tuple[int, dict[str, Any]]:
        transport = httpx.ASGITransport(app=api_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://inprocess") as client:
            resp = await client.get(path, params=params, timeout=15.0)
            return resp.status_code, resp.json()

    async def handle_generate_script(
        brief: str,
        generation_mode: str,
        target_dur: int,
        top_k: int,
        video_format: str,
        food_category: str,
        price_tier: str,
        occasion: str,
        city_norm: str,
    ) -> tuple[str, str, str, str]:
        filters = _build_filters(video_format, food_category, price_tier, occasion, city_norm)
        payload = {
            "brief": brief,
            "generation_mode": generation_mode,
            "target_duration_sec": int(target_dur),
            "top_k_evidence": int(top_k),
            "filters": filters,
        }
        status, data = await _post_api("/api/v1/script/generate", payload)
        if status != 200:
            err_html = render_error_alert_html(
                data.get("code", f"HTTP {status}"),
                data.get("message", json.dumps(data, ensure_ascii=False)),
            )
            return "", err_html, "", ""

        timings_html = render_timings_html(data.get("timings_ms") or {}, label="Script Pipeline")
        script_html = render_script_html(data)
        bench_html = render_benchmark_html(data.get("niche_benchmark") or {})
        cards = data.get("evidence_cards") or []
        ev_html = render_evidence_cards_html(cards, mode="hybrid_rrf", total_cands=len(cards))
        return timings_html, script_html, bench_html, ev_html

    async def handle_explore_evidence(
        query: str,
        mode: str,
        top_k: int,
        rerank: bool,
        video_format: str,
        food_category: str,
        price_tier: str,
        city_norm: str,
    ) -> tuple[str, str, str]:
        filters = _build_filters(video_format, food_category, price_tier, None, city_norm)
        b_status, b_data = await _post_api("/api/v1/analytics/niche-benchmark", filters)
        r_status, r_data = await _post_api(
            "/api/v1/retrieval/search",
            {
                "query": query,
                "mode": mode,
                "top_k": int(top_k),
                "rerank": bool(rerank),
                "filters": filters,
            },
        )
        bench_html = (
            render_benchmark_html(b_data)
            if b_status == 200
            else render_error_alert_html(b_data.get("code", b_status), b_data.get("message", ""))
        )
        if r_status != 200:
            err_html = render_error_alert_html(
                r_data.get("code", f"HTTP {r_status}"),
                r_data.get("message", json.dumps(r_data, ensure_ascii=False)),
            )
            return "", bench_html, err_html

        timings_html = render_timings_html(r_data.get("timings_ms") or {}, label="Retrieval")
        ev_html = render_evidence_cards_html(
            r_data.get("items") or [],
            mode=str(r_data.get("mode", mode)),
            total_cands=int(r_data.get("total_candidates", 0)),
            insufficient_evidence=bool(r_data.get("insufficient_evidence", False)),
            abstain_reason=r_data.get("abstain_reason"),
        )
        return timings_html, bench_html, ev_html

    async def handle_filter_corpus_videos(
        require_voice: bool,
        min_comments: int,
    ) -> dict[str, Any]:
        status, data = await _get_api(
            "/api/v1/trust/corpus-videos",
            params={
                "require_voice": "true" if require_voice else "false",
                "min_comments": int(min_comments),
                "limit": 150,
            },
        )
        if status != 200:
            return gr.update(choices=[], value=None)
        choices = [_format_video_choice(it) for it in (data.get("items") or [])]
        default_val = choices[0][1] if choices else None
        return gr.update(choices=choices, value=default_val)

    async def handle_audit_corpus_video(
        video_id: str | None,
        hide_seeding: bool,
    ) -> tuple[str, str, str, str, str]:
        if not video_id or not str(video_id).strip():
            msg = render_error_alert_html(
                "NO_VIDEO_SELECTED",
                "Vui lòng chọn một video thực tế từ danh sách kho Gold.",
                amber=True,
            )
            return "", msg, "", "", ""
        status, data = await _get_api(f"/api/v1/trust/corpus-video/{str(video_id).strip()}")
        if status != 200:
            err = render_error_alert_html(
                data.get("code", f"HTTP {status}"),
                data.get("message", json.dumps(data, ensure_ascii=False)),
            )
            return "", err, "", "", ""
        timings_html = render_timings_html(data.get("timings_ms") or {}, label="Corpus Multimodal Audit")
        header_html = render_corpus_video_header_html(data.get("video") or {})
        disc_html = render_disclosure_promo_html(data.get("disclosure_and_promo") or {})
        prosody_html = render_prosody_segments_html(data.get("prosody_and_timing") or {})
        trust_html = render_trust_audit_html(data.get("trust_audit") or {}, hide_seeding=hide_seeding)
        return timings_html, header_html, disc_html, prosody_html, trust_html

    async def handle_trust_audit_manual(
        caption: str,
        transcript: str,
        raw_comments_lines: str,
        hide_seeding: bool,
        is_ad: bool = False,
        is_ec_video: bool = False,
        epistemic_question: str = "",
    ) -> tuple[str, str, str]:
        q_clean = (epistemic_question or "").strip()
        d_status, d_data = await _post_api(
            "/api/v1/trust/disclosure-check",
            {
                "caption": caption,
                "transcript": transcript,
                "is_ad": bool(is_ad),
                "is_ec_video": bool(is_ec_video),
                "question": q_clean or None,
            },
        )
        if d_status != 200:
            err = render_error_alert_html(
                d_data.get("code", f"HTTP {d_status}"),
                d_data.get("message", json.dumps(d_data, ensure_ascii=False)),
            )
            return "", err, ""

        comments_payload = parse_demo_comment_lines(raw_comments_lines)
        status, data = await _post_api(
            "/api/v1/trust/audit-video",
            {
                "caption": caption,
                "transcript": transcript,
                "is_ad": bool(is_ad),
                "is_ec_video": bool(is_ec_video),
                "comments": comments_payload,
            },
        )
        if status != 200:
            return (
                "",
                render_disclosure_promo_html(d_data),
                render_error_alert_html(status, json.dumps(data, ensure_ascii=False)),
            )
        merged_timings = dict(d_data.get("timings_ms") or {})
        merged_timings.update(data.get("timings_ms") or {})
        return (
            render_timings_html(merged_timings, label="Manual Audit"),
            render_disclosure_promo_html(d_data),
            render_trust_audit_html(data, hide_seeding=hide_seeding),
        )

    async def handle_refresh_status() -> tuple[str, str, dict[str, Any], dict[str, Any]]:
        _, ready_data = await _get_api("/health/ready")
        _, eval_data = await _get_api("/api/v1/evaluation/summary")
        _, ms_data = await _get_api("/api/v1/evaluation/milestones")
        summary_html = render_system_status_html(ready_data, eval_data)
        ms_html = render_milestone_evaluations_html(ms_data)
        return summary_html, ms_html, ready_data, ms_data

    container = getattr(api_app.state, "container", None)
    manifest = getattr(getattr(container, "analytics", None), "manifest", None)
    mm_store = getattr(container, "multimodal", None)
    gemini_ok = bool(getattr(getattr(container, "gemini", None), "is_configured", False))

    initial_mm_items = (
        mm_store.list_videos(require_voice=False, min_comments=1, limit=150)
        if mm_store is not None and getattr(mm_store, "available", False)
        else []
    )
    initial_choices = [_format_video_choice(it) for it in initial_mm_items]
    initial_vid = initial_choices[0][1] if initial_choices else None

    hero_html = render_hero_banner_html(
        snapshot_id=str(getattr(manifest, "snapshot_id", "local_verified_corpus")),
        total_videos=int(getattr(manifest, "total_videos", 0)),
        total_creators=int(getattr(manifest, "total_creators", 0)),
        poi_tagged_videos=int(getattr(manifest, "poi_tagged_videos", 0)),
        transcribed_videos=int(getattr(manifest, "transcribed_videos", 0)),
        gemini_configured=gemini_ok,
        multimodal_snapshot_id=getattr(mm_store, "snapshot_id", None),
        multimodal_comments=int(getattr(mm_store, "total_comments", 0)),
        multimodal_voice_segments=int(getattr(mm_store, "total_voice_segments", 0)),
    )

    all_opt = "(Tự động / Tất cả)"

    with gr.Blocks(title="ViralFoodRAG — Evidence-Based TikTok Intelligence") as demo:
        gr.HTML(hero_html)

        with gr.Tabs():
            # TAB 1: Script Studio
            with gr.Tab("1. Studio Kịch Bản (Script Studio)"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=5):
                        brief_in = gr.Textbox(
                            label="Đề bài video (Brief)",
                            lines=3,
                            value="Review quán ốc sinh viên bình dân khoảng 35k ăn đêm ở Quận 4 Sài Gòn, nhấn mạnh nước chấm sả tắc",
                        )
                        with gr.Row():
                            p_s1 = gr.Button("Mẫu 1: Ốc sinh viên Q4", size="sm")
                            p_s2 = gr.Button("Mẫu 2: Đậu hũ thúi Q1 (M3.3)", size="sm")
                            p_s3 = gr.Button("Mẫu 3: Test chặn ngoài F&B", size="sm")
                        gen_mode_in = gr.Radio(
                            choices=["offline_grounded", "gemini_free"],
                            value="offline_grounded",
                            label="Chế độ tổng hợp (offline_grounded = $0 không cần key)",
                        )
                        with gr.Row():
                            dur_in = gr.Slider(20, 120, value=45, step=5, label="Thời lượng mục tiêu (giây)")
                            topk_in = gr.Slider(3, 8, value=5, step=1, label="Số video bằng chứng")
                        with gr.Accordion("Bộ lọc ngách nâng cao (tùy chọn)", open=False):
                            fmt_in = gr.Dropdown([all_opt, *VIDEO_FORMATS], value=all_opt, label="Định dạng video")
                            cat_in = gr.Dropdown([all_opt, *FOOD_CATEGORIES], value=all_opt, label="Nhóm ẩm thực")
                            price_in = gr.Dropdown([all_opt, *PRICE_TIERS], value=all_opt, label="Phân khúc giá")
                            occ_in = gr.Dropdown([all_opt, *OCCASION_LABELS], value=all_opt, label="Hoàn cảnh / Dịp ăn")
                            city_in = gr.Textbox(label="Tỉnh / Thành phố (vd: hồ chí minh, hà nội, đà lạt)", value="")
                        gen_btn = gr.Button("🚀 Truy Xuất & Sinh Kịch Bản Chuẩn Ngách", variant="primary")

                    with gr.Column(scale=7):
                        timings_out = gr.HTML(render_timings_html({}))
                        with gr.Tabs():
                            with gr.Tab("📜 Kịch Bản & Guardrail"):
                                script_out = gr.HTML(render_placeholder_html("Chọn mẫu hoặc nhập đề bài rồi nhấn 'Truy Xuất & Sinh Kịch Bản'."))
                            with gr.Tab("📊 Niche Micro-Benchmark"):
                                bench_out = gr.HTML(render_placeholder_html("Thống kê ngách lịch sử sẽ hiển thị tại đây."))
                            with gr.Tab("🎬 Bằng Chứng Trích Dẫn"):
                                evidence_out = gr.HTML(render_placeholder_html("Các video bằng chứng nguồn sẽ hiển thị tại đây."))

                p_s1.click(lambda: ("Review quán ốc sinh viên bình dân khoảng 35k ăn đêm ở Quận 4 Sài Gòn, nhấn mạnh nước chấm sả tắc", ""), outputs=[brief_in, city_in])
                p_s2.click(lambda: ("Đậu hũ thúi hong thúi quán đông khách Quận 1", ""), outputs=[brief_in, city_in])
                p_s3.click(lambda: ("Phân tích thị trường chứng khoán và tiền ảo bitcoin tháng này", ""), outputs=[brief_in, city_in])

                gen_btn.click(
                    fn=handle_generate_script,
                    inputs=[brief_in, gen_mode_in, dur_in, topk_in, fmt_in, cat_in, price_in, occ_in, city_in],
                    outputs=[timings_out, script_out, bench_out, evidence_out],
                )

            # TAB 2: Hybrid Evidence Explorer
            with gr.Tab("2. Khám Phá Bằng Chứng & Ngách"):
                with gr.Row(equal_height=False):
                    with gr.Column(scale=4):
                        q_in = gr.Textbox(
                            label="Từ khóa / Ngữ cảnh tìm kiếm",
                            lines=2,
                            value="công thức làm gà rang bơ tỏi đơn giản tại nhà",
                        )
                        with gr.Row():
                            p_e1 = gr.Button("Mẫu 1: Gà rang bơ tỏi", size="sm")
                            p_e2 = gr.Button("Mẫu 2: Không có nguồn (Lai Châu)", size="sm")
                        with gr.Row():
                            mode_in = gr.Dropdown(["bm25", "hybrid_rrf", "dense"], value="bm25", label="Chế độ truy xuất")
                            k_in = gr.Slider(3, 15, value=5, step=1, label="Top-K")
                        rerank_in = gr.Checkbox(value=True, label="Bật Reranker theo ngữ cảnh")
                        with gr.Accordion("Bộ lọc ngách (tùy chọn)", open=False):
                            e_fmt = gr.Dropdown([all_opt, *VIDEO_FORMATS], value=all_opt, label="Định dạng")
                            e_cat = gr.Dropdown([all_opt, *FOOD_CATEGORIES], value=all_opt, label="Nhóm món")
                            e_price = gr.Dropdown([all_opt, *PRICE_TIERS], value=all_opt, label="Mức giá")
                            e_city = gr.Textbox(label="Thành phố chuẩn hóa", value="")
                        search_btn = gr.Button("🔍 Phân Tích Ngách & Truy Xuất", variant="primary")

                    with gr.Column(scale=8):
                        e_timings = gr.HTML(render_timings_html({}))
                        e_bench = gr.HTML(render_placeholder_html("Thống kê ngách của lát cắt lọc sẽ hiển thị tại đây."))
                        e_cards = gr.HTML(render_placeholder_html("Danh sách video bằng chứng sẽ hiển thị tại đây."))

                p_e1.click(lambda: ("công thức làm gà rang bơ tỏi đơn giản tại nhà", ""), outputs=[q_in, e_city])
                p_e2.click(lambda: ("quán cơm tấm sườn bì chả ở Lai Châu", "lai châu"), outputs=[q_in, e_city])
                search_btn.click(
                    fn=handle_explore_evidence,
                    inputs=[q_in, mode_in, k_in, rerank_in, e_fmt, e_cat, e_price, e_city],
                    outputs=[e_timings, e_bench, e_cards],
                )

            # TAB 3: Multimodal Corpus & Trust Diagnostics (M3.3 + M4.1 + M4.2 + M5.1 + M5.2)
            with gr.Tab("3. Kiểm Toán Đa Phương Thức (M3–M5)"):
                with gr.Tabs():
                    with gr.Tab("🎬 Kho Video Thực Tế (2,823 Bình Luận & 29 Audio M4.1)"):
                        with gr.Row(equal_height=False):
                            with gr.Column(scale=4):
                                gr.Markdown(
                                    "Chọn trực tiếp video thực tế từ kho Gold `m3_3_playwright_comments_20261125_v5` "
                                    "để chạy trọn bộ **M4.1 (Prosody & Timestamp)**, **M4.2 (Disclosure & Promo)**, "
                                    "**M5.1 (Seeding)** và **M5.2 (4-Aspect ABSA + NFC Spans)**."
                                )
                                mm_voice_only = gr.Checkbox(
                                    value=False,
                                    label="Chỉ hiện video có âm thanh Prosody & câu thoại ASR (M4.1)",
                                )
                                mm_min_cmts = gr.Slider(
                                    1,
                                    25,
                                    value=3,
                                    step=1,
                                    label="Số bình luận thực tế tối thiểu",
                                )
                                mm_filter_btn = gr.Button("🔄 Lọc Danh Sách Video Thực Tế", size="sm")
                                mm_dropdown = gr.Dropdown(
                                    choices=initial_choices,
                                    value=initial_vid,
                                    label="Video thực tế trong kho Gold",
                                )
                                mm_hide_seed = gr.Checkbox(
                                    value=False,
                                    label="Tạm ẩn bình luận có chỉ dấu trên giao diện (mặc định tắt — M5.1)",
                                )
                                mm_audit_btn = gr.Button(
                                    "🔎 Kiểm Toán Toàn Diện Video Thực Tế (M4 + M5)",
                                    variant="primary",
                                )

                            with gr.Column(scale=8):
                                mm_timings = gr.HTML(render_timings_html({}))
                                mm_header = gr.HTML(
                                    render_placeholder_html(
                                        "Chọn một video bên trái rồi nhấn 'Kiểm Toán Toàn Diện Video Thực Tế'."
                                    )
                                )
                                mm_disc = gr.HTML("")
                                mm_prosody = gr.HTML("")
                                mm_trust = gr.HTML("")

                        mm_filter_btn.click(
                            fn=handle_filter_corpus_videos,
                            inputs=[mm_voice_only, mm_min_cmts],
                            outputs=[mm_dropdown],
                        )
                        mm_audit_btn.click(
                            fn=handle_audit_corpus_video,
                            inputs=[mm_dropdown, mm_hide_seed],
                            outputs=[mm_timings, mm_header, mm_disc, mm_prosody, mm_trust],
                        )

                    with gr.Tab("✍️ Nhập Tay & Kiểm Thử Guardrail (Sandbox)"):
                        with gr.Row(equal_height=False):
                            with gr.Column(scale=5):
                                gr.Markdown(
                                    "Thử nghiệm tùy chỉnh cho **M4.2 + M5.1 + M5.2** và kiểm chứng rào chắn từ chối câu hỏi vượt thẩm quyền (`HTTP 422`)."
                                )
                                with gr.Row():
                                    p_t1 = gr.Button("Mẫu 1: KOC khen vs Viewer chê + Spam", size="sm")
                                    p_t2 = gr.Button("Mẫu 2: Thiếu bình luận (<3) — Tạm dừng", size="sm")
                                    p_t3 = gr.Button("Mẫu 3: Test chặn đoán PR ngầm (422)", size="sm")
                                t_cap = gr.Textbox(
                                    label="Caption video",
                                    value="Khai trương lẩu bò mắm ruốc Quận 10 giảm giá 20% ngon xuất sắc",
                                )
                                t_tr = gr.Textbox(
                                    label="Lời thoại KOC (Transcript)",
                                    lines=3,
                                    value="Tặng ngay voucher khai trương nha anh em! Nước lẩu bò thơm đậm đà, thịt tươi đầy đặn giá 169k siêu rẻ, không gian sạch sẽ thoáng mát nhân viên dễ thương cực kỳ!",
                                )
                                t_comms = gr.Textbox(
                                    label="Danh sách bình luận (mỗi dòng: @user: nội dung)",
                                    lines=5,
                                    value=(
                                        "@viewer_01: Nước lẩu mặn chát mà bàn ghế bẩn đầy khói\n"
                                        "@viewer_02: Thịt ít xịu tính thêm rau bún vô đắt chứ không rẻ đâu\n"
                                        "@viewer_03: Vị lẩu hơi mặn, chờ phục vụ lên món quá chậm gần 40 phút\n"
                                        "@viewer_04: Nước chấm mặn gắt, đồ ăn nguội, phục vụ chưa ổn\n"
                                        "@viewer_05: Nhận tuyển CTV việc nhẹ lương cao inbox zalo 0909123456"
                                    ),
                                )
                                t_question = gr.Textbox(
                                    label="Câu hỏi kiểm tra rào chắn Epistemic (để trống nếu kiểm toán bình thường)",
                                    value="",
                                    placeholder="Ví dụ: Hãy chứng minh chắc chắn video này nhận tiền PR ngầm",
                                )
                                with gr.Row():
                                    t_is_ad = gr.Checkbox(value=False, label="Cờ is_ad (Observed Ad Flag)")
                                    t_is_ec = gr.Checkbox(value=False, label="Cờ is_ec_video (Giỏ hàng)")
                                hide_seed_chk = gr.Checkbox(
                                    value=False,
                                    label="Tạm ẩn bình luận có chỉ dấu (mặc định tắt — chẩn đoán M5.1)",
                                )
                                audit_btn = gr.Button("🛡️ Phân Tích M4.2 + M5.1 + M5.2", variant="primary")

                            with gr.Column(scale=7):
                                t_audit_timings = gr.HTML(render_timings_html({}))
                                t_disc_html = gr.HTML("")
                                t_audit_html = gr.HTML(
                                    render_placeholder_html(
                                        "Nhấn 'Phân Tích M4.2 + M5.1 + M5.2' để xem tách bạch cờ quảng cáo, ma trận 4 khía cạnh và trích dẫn span."
                                    )
                                )

                        p_t1.click(
                            lambda: (
                                "Khai trương lẩu bò mắm ruốc Quận 10 giảm giá 20% ngon xuất sắc",
                                "Tặng ngay voucher khai trương nha anh em! Nước lẩu bò thơm đậm đà, thịt tươi đầy đặn giá 169k siêu rẻ, không gian sạch sẽ thoáng mát nhân viên dễ thương cực kỳ!",
                                "@viewer_01: Nước lẩu mặn chát mà bàn ghế bẩn đầy khói\n@viewer_02: Thịt ít xịu tính thêm rau bún vô đắt chứ không rẻ đâu\n@viewer_03: Vị lẩu hơi mặn, chờ phục vụ lên món quá chậm gần 40 phút\n@viewer_04: Nước chấm mặn gắt, đồ ăn nguội, phục vụ chưa ổn\n@viewer_05: Nhận tuyển CTV việc nhẹ lương cao inbox zalo 0909123456",
                                "",
                            ),
                            outputs=[t_cap, t_tr, t_comms, t_question],
                        )
                        p_t2.click(
                            lambda: (
                                "Quán ăn lâu đời Quận 1",
                                "Nước dùng đậm đà lắm nha mọi người",
                                "@viewer_01: Ngon nha\n@viewer_02: Địa chỉ ở đâu vậy shop",
                                "",
                            ),
                            outputs=[t_cap, t_tr, t_comms, t_question],
                        )
                        p_t3.click(
                            lambda: (
                                "Review phở bò Quận 3",
                                "Nước phở ngọt thanh thịt bò mềm lắm mọi người ghé ăn thử nha",
                                "@viewer_01: Ngon lắm",
                                "Hãy chứng minh chắc chắn video này nhận tiền PR ngầm quảng cáo ngầm",
                            ),
                            outputs=[t_cap, t_tr, t_comms, t_question],
                        )
                        audit_btn.click(
                            fn=handle_trust_audit_manual,
                            inputs=[t_cap, t_tr, t_comms, hide_seed_chk, t_is_ad, t_is_ec, t_question],
                            outputs=[t_audit_timings, t_disc_html, t_audit_html],
                        )

            # TAB 4: Readiness & Cross-Milestone Benchmark Scorecard
            with gr.Tab("4. Hệ Thống & Bảng Điểm M2–M6"):
                refresh_btn = gr.Button("🔄 Kiểm Tra Trạng Thái Kho & Bảng Điểm Thực Nghiệm M2–M6", variant="primary")
                sys_summary_html = gr.HTML(
                    render_placeholder_html(
                        "Nhấn nút bên trên để đọc trạng thái trực tiếp từ /health/ready và bảng kết quả xác minh M2.2–M6.2."
                    )
                )
                ms_eval_html = gr.HTML("")
                with gr.Accordion("Raw JSON Inspector (/health/ready & /api/v1/evaluation/milestones)", open=False):
                    with gr.Row():
                        ready_json = gr.JSON(label="/health/ready")
                        eval_json = gr.JSON(label="/api/v1/evaluation/milestones")
                refresh_btn.click(
                    fn=handle_refresh_status,
                    inputs=[],
                    outputs=[sys_summary_html, ms_eval_html, ready_json, eval_json],
                )

    blocks_out: gr.Blocks = demo
    return blocks_out
