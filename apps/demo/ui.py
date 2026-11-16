from __future__ import annotations

import json
from typing import Any

import gradio as gr
import httpx
from fastapi import FastAPI

from apps.demo.presentation import (
    format_benchmark_markdown,
    format_evidence_cards_markdown,
    format_script_markdown,
    format_timings_markdown,
)
from packages.taxonomy import FOOD_CATEGORIES, OCCASION_LABELS, PRICE_TIERS, VIDEO_FORMATS


def _clean_choice(val: str | None) -> str | None:
    if not val or val == "(Tự động / Tất cả)":
        return None
    return val.strip()


def build_gradio_blocks(api_app: FastAPI) -> gr.Blocks:
    """Build thin 3-tab Gradio workspace calling FastAPI routes over in-process ASGI transport."""

    async def _post_api(path: str, payload: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        transport = httpx.ASGITransport(app=api_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://inprocess") as client:
            resp = await client.post(path, json=payload, timeout=45.0)
            return resp.status_code, resp.json()

    async def _get_api(path: str) -> tuple[int, dict[str, Any]]:
        transport = httpx.ASGITransport(app=api_app)
        async with httpx.AsyncClient(transport=transport, base_url="http://inprocess") as client:
            resp = await client.get(path, timeout=15.0)
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
        filters = {
            k: v
            for k, v in {
                "video_format": _clean_choice(video_format),
                "food_category": _clean_choice(food_category),
                "price_tier": _clean_choice(price_tier),
                "occasion": _clean_choice(occasion),
                "city_norm": city_norm.strip().lower() if city_norm and city_norm.strip() else None,
            }.items()
            if v is not None
        }
        payload = {
            "brief": brief,
            "generation_mode": generation_mode,
            "target_duration_sec": int(target_dur),
            "top_k_evidence": int(top_k),
            "filters": filters,
        }
        status, data = await _post_api("/api/v1/script/generate", payload)
        if status != 200:
            err = f"### ⚠️ Lỗi (`{data.get('code', status)}`)\n{data.get('message', json.dumps(data, ensure_ascii=False))}"
            return err, "", "", ""

        script_md = format_script_markdown(data)
        bench_md = format_benchmark_markdown(data.get("niche_benchmark") or {})
        ev_md = format_evidence_cards_markdown(
            data.get("evidence_cards") or [],
            mode="hybrid_rrf",
            total_cands=len(data.get("evidence_cards") or []),
        )
        timings_md = format_timings_markdown(data.get("timings_ms") or {})
        return script_md, bench_md, ev_md, timings_md

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
        filters = {
            k: v
            for k, v in {
                "video_format": _clean_choice(video_format),
                "food_category": _clean_choice(food_category),
                "price_tier": _clean_choice(price_tier),
                "city_norm": city_norm.strip().lower() if city_norm and city_norm.strip() else None,
            }.items()
            if v is not None
        }
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
        bench_md = format_benchmark_markdown(b_data) if b_status == 200 else str(b_data)
        if r_status != 200:
            err = f"### ⚠️ Lỗi truy xuất (`{r_data.get('code', r_status)}`)\n{r_data.get('message', '')}"
            return bench_md, err, ""
        ev_md = format_evidence_cards_markdown(
            r_data.get("items") or [],
            mode=str(r_data.get("mode", mode)),
            total_cands=int(r_data.get("total_candidates", 0)),
        )
        t_md = format_timings_markdown(r_data.get("timings_ms") or {})
        return bench_md, ev_md, t_md

    async def handle_refresh_status() -> tuple[dict[str, Any], dict[str, Any]]:
        _, ready_data = await _get_api("/health/ready")
        _, eval_data = await _get_api("/api/v1/evaluation/summary")
        return ready_data, eval_data

    all_opt = "(Tự động / Tất cả)"

    with gr.Blocks(title="ViralFoodRAG — Evidence-Based TikTok Intelligence") as demo:
        gr.Markdown(
            "# 🍜 ViralFoodRAG — Evidence-Based TikTok Content Intelligence & Script Engine\n"
            "Hệ thống phân tích chuẩn thực nghiệm ngách (**70,996 video • 264 creators • 23,448 GPS POIs • 21,748 transcripts**) "
            "và sinh kịch bản dựa trên bằng chứng video thành công thực tế."
        )

        with gr.Tabs():
            with gr.Tab("1. Evidence-Grounded Script Studio"):
                with gr.Row():
                    with gr.Column(scale=2):
                        brief_in = gr.Textbox(
                            label="Đề bài sáng tạo video (Brief)",
                            lines=3,
                            value="Review quán ốc sinh viên bình dân khoảng 35k ăn đêm ở Quận 4 Sài Gòn, nhấn mạnh nước chấm sả tắc",
                        )
                        with gr.Row():
                            gen_mode_in = gr.Radio(
                                choices=["offline_grounded", "gemini_free"],
                                value="offline_grounded",
                                label="Chế độ tổng hợp (offline_grounded = $0 không cần API key; gemini_free = dùng GEMINI_API_KEY)",
                            )
                            dur_in = gr.Slider(20, 120, value=45, step=5, label="Thời lượng mục tiêu (giây)")
                            topk_in = gr.Slider(3, 8, value=5, step=1, label="Số video bằng chứng (Top-K)")
                    with gr.Column(scale=1):
                        fmt_in = gr.Dropdown([all_opt, *VIDEO_FORMATS], value=all_opt, label="Định dạng video")
                        cat_in = gr.Dropdown([all_opt, *FOOD_CATEGORIES], value=all_opt, label="Nhóm ẩm thực")
                        price_in = gr.Dropdown([all_opt, *PRICE_TIERS], value=all_opt, label="Phân khúc giá")
                        occ_in = gr.Dropdown([all_opt, *OCCASION_LABELS], value=all_opt, label="Hoàn cảnh / Dịp ăn")
                        city_in = gr.Textbox(label="Tỉnh / Thành phố (tuỳ chọn, vd: hồ chí minh, hà nội, đà lạt)", value="")

                gen_btn = gr.Button("🚀 Truy Xuất Bằng Chứng & Sinh Kịch Bản Chuẩn Ngách", variant="primary")
                timings_out = gr.Markdown()
                bench_out = gr.Markdown()
                script_out = gr.Markdown()
                evidence_out = gr.Markdown()

                gen_btn.click(
                    fn=handle_generate_script,
                    inputs=[brief_in, gen_mode_in, dur_in, topk_in, fmt_in, cat_in, price_in, occ_in, city_in],
                    outputs=[script_out, bench_out, evidence_out, timings_out],
                )

            with gr.Tab("2. Hybrid Evidence Explorer & Micro-Benchmarks"):
                with gr.Row():
                    q_in = gr.Textbox(
                        label="Từ khoá / Ngữ cảnh tìm kiếm lời thoại & caption",
                        value="công thức làm gà rang bơ tỏi đơn giản tại nhà",
                        scale=3,
                    )
                    mode_in = gr.Dropdown(["bm25", "hybrid_rrf", "dense"], value="bm25", label="Chế độ truy xuất", scale=1)
                    rerank_in = gr.Checkbox(value=True, label="Bật Reranker")
                    k_in = gr.Slider(3, 15, value=5, step=1, label="Top-K")
                with gr.Row():
                    e_fmt = gr.Dropdown([all_opt, *VIDEO_FORMATS], value=all_opt, label="Định dạng")
                    e_cat = gr.Dropdown([all_opt, *FOOD_CATEGORIES], value=all_opt, label="Nhóm món")
                    e_price = gr.Dropdown([all_opt, *PRICE_TIERS], value=all_opt, label="Mức giá")
                    e_city = gr.Textbox(label="Thành phố chuẩn hoá", value="")

                search_btn = gr.Button("🔍 Phân Tích Ngách & Truy Xuất Video Viral", variant="primary")
                e_timings = gr.Markdown()
                e_bench = gr.Markdown()
                e_cards = gr.Markdown()

                search_btn.click(
                    fn=handle_explore_evidence,
                    inputs=[q_in, mode_in, k_in, rerank_in, e_fmt, e_cat, e_price, e_city],
                    outputs=[e_bench, e_cards, e_timings],
                )

            with gr.Tab("3. Readiness & Retrieval Benchmark"):
                refresh_btn = gr.Button("🔄 Kiểm Tra Trạng Thái Hệ Thống & Báo Cáo Đánh Giá")
                with gr.Row():
                    ready_json = gr.JSON(label="/health/ready")
                    eval_json = gr.JSON(label="/api/v1/evaluation/summary (Frozen Retrieval Benchmark)")
                refresh_btn.click(fn=handle_refresh_status, inputs=[], outputs=[ready_json, eval_json])

    blocks_out: gr.Blocks = demo
    return blocks_out
