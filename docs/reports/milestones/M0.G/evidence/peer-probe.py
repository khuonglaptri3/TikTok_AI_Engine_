"""Assert the independent G0 runtime checks; retain failures for owner review."""
from __future__ import annotations

import hashlib
import io
import json
import logging
import math
import os
import subprocess
import sys
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[5]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
os.environ["GRADIO_ANALYTICS_ENABLED"] = "False"
os.environ["GEMINI_API_KEY"] = ""
os.environ["GOOGLE_API_KEY"] = ""

from fastapi.testclient import TestClient
from pydantic import ValidationError

from apps.api.app.main import create_app
from packages.analytics import load_verified_corpus
from packages.common.exceptions import QuotaBlockedError
from packages.common.logging import SecretRedactingFilter, redact_secrets
from packages.common.settings import AppSettings
from packages.llm.clients.gemini import BoundedGeminiClient, SlidingWindowRateLimiter


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def main() -> int:
    results: list[dict] = []
    receipt: dict = {"started_at": datetime.now(UTC).isoformat(), "checks": results,
                     "head": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
                     "live_provider_calls": 0, "fake_provider_calls": 0,
                     "provider_spend_usd": 0, "scope": "Independent local CPU/offline G0 review"}

    def check(name: str, ok: bool, detail: object = None, *, blocking: bool = True) -> None:
        results.append({"name": name, "passed": bool(ok), "blocking": blocking, "detail": detail})

    def timings(name: str, body: dict) -> None:
        values = body.get("timings_ms", {})
        check(name + "_finite_ms", bool(values) and all(isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 for v in values.values()), values)

    try:
        paths = sorted((ROOT / "data/corpus/20261117_recovered_v1").iterdir())
        paths += sorted((ROOT / "data/corpus/20261118_taxonomy_fix_v1").iterdir())
        paths += sorted((ROOT / "artifacts/indexes/bm25-v2").iterdir())
        paths = [p for p in paths if p.is_file()]
        before = {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}
        receipt["runtime_sha256_before"] = before
        for path in paths:
            rel = path.relative_to(ROOT).as_posix()
            blob = subprocess.check_output(["git", "rev-parse", f"HEAD:{rel}"], cwd=ROOT, text=True).strip()
            actual = subprocess.check_output(["git", "hash-object", "--", rel], cwd=ROOT, text=True).strip()
            check("git_blob_identity:" + rel, blob == actual)
        datasets = {}
        for name in ("20261117_recovered_v1", "20261118_taxonomy_fix_v1"):
            manifest, creators, videos = load_verified_corpus(ROOT / "data/corpus" / name)
            check("snapshot:" + name, len(videos) == 70996 and len(creators) == 264 and videos.shape[1] == 49 and videos["video_id"].is_unique,
                  {"videos": len(videos), "creators": len(creators), "columns": videos.shape[1], "snapshot_id": manifest.snapshot_id})
            datasets[name] = videos

        settings = AppSettings(gemini_api_key="", corpus_dir=ROOT / "data/corpus/20261117_recovered_v1", bm25_index_dir=ROOT / "artifacts/indexes/bm25-v2")
        with patch.object(BoundedGeminiClient, "_call_gemini_sdk", side_effect=AssertionError("Unexpected live provider call")) as sdk:
            app = create_app(settings=settings, mount_demo=True)
            with TestClient(app) as client:
                live = client.get("/health/live")
                ready = client.get("/health/ready")
                demo = client.get("/demo/")
                check("live", live.status_code == 200)
                ready_data = ready.json()
                check("readiness", ready.status_code == 200 and ready_data.get("status") == "ready" and ready_data.get("total_videos") == 70996 and ready_data.get("indexed_bm25_videos") == 21748 and ready_data.get("gemini_key_configured") is False, ready_data)
                check("demo", demo.status_code == 200 and "gradio" in demo.text.lower(), {"status": demo.status_code, "html_bytes": len(demo.content)})
                valid_ids = set(datasets["20261117_recovered_v1"]["video_id"].astype(str))
                index_ids = app.state.container.retrieval.bm25.video_ids
                check("index_membership", len(index_ids) == 21748 and len(set(index_ids)) == 21748 and set(index_ids) <= valid_ids)
                requests = [
                    ("benchmark", "/api/v1/analytics/niche-benchmark", {"video_format": "Review quán ăn", "city_norm": "hồ chí minh"}, 200, None),
                    ("search", "/api/v1/retrieval/search", {"query": "bánh mì thịt nướng Sài Gòn", "mode": "bm25", "top_k": 5}, 200, None),
                    ("draft", "/api/v1/script/generate", {"brief": "Review quán ốc sinh viên bình dân 35k ăn đêm ở Quận 4 Sài Gòn", "target_duration_sec": 45, "generation_mode": "offline_grounded"}, 200, None),
                    ("missing_key", "/api/v1/script/generate", {"brief": "Review phở bò chuẩn vị Hà Nội buổi sáng", "generation_mode": "gemini_free"}, 503, "PROVIDER_KEY_MISSING"),
                    ("out_of_domain", "/api/v1/script/generate", {"brief": "Phân tích biểu đồ nến đầu tư chứng khoán và tiền ảo bitcoin", "generation_mode": "offline_grounded"}, 422, "UNSUPPORTED_DOMAIN"),
                    ("blank_query", "/api/v1/retrieval/search", {"query": "  ", "mode": "bm25"}, 422, None),
                    ("short_duration", "/api/v1/script/generate", {"brief": "Review phở bò Hà Nội", "target_duration_sec": 5, "generation_mode": "offline_grounded"}, 422, None),
                    ("dense_unavailable", "/api/v1/retrieval/search", {"query": "bánh mì Sài Gòn", "mode": "dense"}, 503, "INDEX_NOT_READY"),
                ]
                responses = {}
                for name, route, payload, expected, code in requests:
                    start = time.perf_counter()
                    response = client.post(route, json=payload)
                    body = response.json()
                    responses[name] = body
                    check("http:" + name, response.status_code == expected and (code is None or body.get("code") == code), {"status": response.status_code, "expected_status": expected, "code": body.get("code"), "wall_ms": round((time.perf_counter() - start) * 1000, 3)})
                    if expected == 200:
                        timings(name, body)
                    if name == "search":
                        ids = [v["citation"]["video_id"] for v in body.get("items", [])]
                        check("search_source_membership", len(ids) == 5 and set(ids) <= valid_ids, ids)
                    if name == "draft":
                        cards = {card["citation"]["video_id"] for card in body.get("evidence_cards", [])}
                        cited = [v for beat in body.get("beats", []) for v in beat["cited_video_ids"]]
                        check("draft_source_membership", bool(cited) and set(cited) <= cards <= valid_ids)
                        check("draft_qualification", body.get("draft_status") == "creative_draft" and body.get("grounding_verified") is False)
                        check("draft_guardrail", body.get("guardrail", {}).get("passed") is True, body.get("guardrail"))
                receipt["endpoint_responses"] = responses
            check("zero_provider_calls", sdk.call_count == 0, sdk.call_count)

        marker = "G0_SYNTHETIC_MARKER"
        examples = [f'{{"password": "{marker}"}}', f"{{'api_key': '{marker}'}}", f"api_key={marker}"]
        check("quoted_secret_redaction", all(marker not in redact_secrets(v) for v in examples))
        stream = io.StringIO()
        logger = logging.Logger("g0-independent-redaction")
        logger.addFilter(SecretRedactingFilter())
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)
        try:
            raise RuntimeError(f'{{"password": "{marker}"}}')
        except RuntimeError:
            logger.exception("Synthetic exception")
        record = logging.LogRecord(logger.name, logging.ERROR, __file__, 1, "Synthetic stack", (), None)
        record.stack_info = f"api_key={marker}"
        logger.handle(record)
        check("traceback_stack_redaction", marker not in stream.getvalue() and "[REDACTED]" in stream.getvalue())

        # Demonstrate whether the project-wide <=2 rule is a hard bound, without network.
        default_client = BoundedGeminiClient(
            AppSettings(gemini_api_key="synthetic-offline-key"),
            rate_limiter=SlidingWindowRateLimiter(max_rpm=15),
        )
        with patch.object(default_client, "_call_gemini_sdk", return_value='{"ok": true}') as default_fake:
            try:
                default_client.generate_structured_json("synthetic budget control", turn_calls_used=2)
                default_blocked = False
            except QuotaBlockedError:
                default_blocked = True
            check("default_two_call_budget_control", default_blocked and default_fake.call_count == 0,
                  {"configured_budget": 2, "turn_calls_used": 2, "mock_sdk_calls": default_fake.call_count})
        try:
            policy_settings = AppSettings(gemini_api_key="synthetic-offline-key", max_llm_calls_per_turn=3)
            config_rejected = False
        except ValidationError:
            config_rejected = True
        check("policy_configuration_rejects_above_two", config_rejected,
              "AppSettings(max_llm_calls_per_turn=3) must be rejected under the project-wide <=2 rule.")
        if not config_rejected:
            fake_client = BoundedGeminiClient(policy_settings, rate_limiter=SlidingWindowRateLimiter(max_rpm=15))
            with patch.object(fake_client, "_call_gemini_sdk", return_value='{"ok": true}') as fake:
                try:
                    fake_client.generate_structured_json("synthetic budget probe", turn_calls_used=2)
                    blocked = False
                except QuotaBlockedError:
                    blocked = True
                receipt["fake_provider_calls"] = fake.call_count
                check("policy_third_call_blocked", blocked and fake.call_count == 0,
                      {"configured_budget": 3, "turn_calls_used": 2, "mock_sdk_calls": fake.call_count, "actual_network_calls": 0})
        after = {p.relative_to(ROOT).as_posix(): digest(p) for p in paths}
        check("runtime_bytes_preserved", before == after)
        receipt["runtime_sha256_after"] = after
    except Exception:
        receipt["unexpected_error"] = traceback.format_exc()
        check("probe_completed", False, "See unexpected_error in receipt.")
    receipt["completed_at"] = datetime.now(UTC).isoformat()
    receipt["failed_checks"] = [v["name"] for v in results if not v["passed"]]
    (OUT / "peer-runtime-receipt.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"checks": len(results), "failed": receipt["failed_checks"], "unexpected_error": receipt.get("unexpected_error")}, ensure_ascii=False))
    return int(any(not v["passed"] and v["blocking"] for v in results))


if __name__ == "__main__":
    raise SystemExit(main())
