from __future__ import annotations

import asyncio

import httpx

from apps.api.app.main import create_app
from packages.common.settings import AppSettings


def test_api_endpoints_and_gradio_demo_mount_end_to_end() -> None:
    # Force empty GEMINI_API_KEY in test settings so tests are 100% deterministic & zero-network
    settings = AppSettings.from_env().model_copy(update={"gemini_api_key": ""})
    app = create_app(settings=settings, mount_demo=True)

    async def _run_checks() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            # 1. Health & readiness
            r_live = await client.get("/health/live")
            assert r_live.status_code == 200
            assert "X-Request-ID" in r_live.headers

            r_ready = await client.get("/health/ready")
            assert r_ready.status_code == 200
            ready_body = r_ready.json()
            assert ready_body["status"] == "ready"
            assert ready_body["total_videos"] == 70996
            assert ready_body["indexed_bm25_videos"] == 21748

            # 2. Demo modules & frozen evaluation report
            r_mod = await client.get("/api/v1/demo/modules")
            assert r_mod.status_code == 200
            assert len(r_mod.json()["taxonomy"]["video_formats"]) == 5

            r_eval = await client.get("/api/v1/evaluation/summary")
            assert r_eval.status_code == 200
            assert r_eval.json()["benchmark_id"] == "retrieval_v2"

            # 3. Niche micro-benchmark
            r_bench = await client.post(
                "/api/v1/analytics/niche-benchmark",
                json={"video_format": "Review quán ăn", "city_norm": "hồ chí minh"},
            )
            assert r_bench.status_code == 200
            assert r_bench.json()["matched_videos"] > 500

            # 4. Hybrid evidence search
            r_search = await client.post(
                "/api/v1/retrieval/search",
                json={
                    "query": "bánh mì thịt nướng Sài Gòn",
                    "mode": "hybrid_rrf",
                    "top_k": 4,
                    "rerank": True,
                },
            )
            assert r_search.status_code == 200
            s_data = r_search.json()
            assert len(s_data["items"]) == 4

            # 5. Grounded script generation (offline_grounded = $0, zero external API key needed)
            r_script = await client.post(
                "/api/v1/script/generate",
                json={
                    "brief": "Review quán ốc sinh viên bình dân 35k ăn đêm ở Quận 4 Sài Gòn",
                    "target_duration_sec": 45,
                    "top_k_evidence": 4,
                    "generation_mode": "offline_grounded",
                },
            )
            assert r_script.status_code == 200
            sc_data = r_script.json()
            assert len(sc_data["beats"]) == 4
            assert sc_data["guardrail"]["passed"] is True
            assert len(sc_data["evidence_cards"]) == 4

            # 6. Fail-closed PROVIDER_KEY_MISSING when gemini_free requested without key
            r_nokey = await client.post(
                "/api/v1/script/generate",
                json={
                    "brief": "Review phở bò chuẩn vị Hà Nội buổi sáng",
                    "generation_mode": "gemini_free",
                },
            )
            assert r_nokey.status_code == 503
            assert r_nokey.json()["code"] == "PROVIDER_KEY_MISSING"

            # 7. Out-of-domain 422 rejection
            r_ood = await client.post(
                "/api/v1/script/generate",
                json={
                    "brief": "Phân tích biểu đồ nến đầu tư chứng khoán và tiền ảo bitcoin",
                    "generation_mode": "offline_grounded",
                },
            )
            assert r_ood.status_code == 422
            assert r_ood.json()["code"] == "UNSUPPORTED_DOMAIN"

            # 8. Mounted Gradio UI at /demo/
            r_demo = await client.get("/demo/", follow_redirects=True)
            assert r_demo.status_code == 200
            assert "gradio" in r_demo.text.lower()

    asyncio.run(_run_checks())
