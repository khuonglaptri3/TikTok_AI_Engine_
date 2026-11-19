#!/usr/bin/env python3
"""Bounded <= 15 RPM Gemini claim-entailment auditor for M2.3 drafts (resumable)."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any

import pandas as pd

from packages.common.exceptions import ProviderKeyMissingError, QuotaBlockedError
from packages.common.logging import redact_secrets
from packages.common.settings import AppSettings
from packages.llm.clients.gemini import SlidingWindowRateLimiter

OUT_DIR = Path(__file__).resolve().parent
REPO_ROOT = OUT_DIR.parents[4]
AUDIT_CSV = OUT_DIR / "nguyen_15_drafts_audit.csv"
CHECKPOINT_JSONL = OUT_DIR / "llm_claim_audit_checkpoint.jsonl"
SUMMARY_JSON = OUT_DIR / "nguyen_15_llm_claim_audit.json"
CORPUS_VIDEOS = REPO_ROOT / "data/corpus/20261117_recovered_v1/fact_videos.parquet"

SYSTEM_RULES = """Bạn là trợ lý kiểm định độ bám nguồn (factual claim entailment) cho bài đánh giá M2.3 của TikTok F&B RAG.
Với mỗi bản nháp (draft_id, brief, beats_preview) và các video nguồn được trả về (source_evidence), hãy đếm cẩn thận:
1. total_factual_claims: tổng số nhận định thực tế cụ thể về món ăn, địa điểm, giá cả, thời gian, đặc điểm quán hoặc trích dẫn nội dung nguồn ("Nguồn cũ: ...") xuất hiện trong các beat. KHÔNG tính các câu định hướng quay dựng giả định tương lai như "Khi quay thực tế, mình sẽ...", "Có thể bổ sung cảnh...".
2. supported_factual_claims: số factual claims trong tổng số trên thực sự được hậu thuẫn đúng ngữ nghĩa bởi một trong các `source_evidence` tương ứng (caption, hook_text, transcript, poi_name, city_norm của video được trích dẫn).
   - Lưu ý quan trọng: nếu `Nguồn cũ: "..."` trích đúng chữ từ `transcript`/`hook_text` của video nguồn, câu trích đó được hậu thuẫn về mặt trích dẫn nguyên văn, NHƯNG nếu phần bình luận/tóm tắt xung quanh bịa thêm chi tiết không có trong nguồn (ví dụ tự gắn tên thành phố sai với nguồn, hoặc khẳng định hương vị không có trong nguồn), thì claim đó KHÔNG được hậu thuẫn.
3. citation_coverage_ok: true nếu toàn bộ các beat có thông tin thực tế / "Nguồn cũ" đều gắn ID nguồn nằm trong `cited_video_ids` hợp lệ; ngược lại false.
4. notes: ghi chú ngắn gọn tiếng Việt (< 180 ký tự) nêu rõ nếu có trích dẫn lời bài hát/nội dung lạc đề hoặc claim chưa khớp nguồn.

Trả về đúng định dạng JSON object:
{"items": [{"draft_id": "n01", "total_factual_claims": <int>, "supported_factual_claims": <int>, "citation_coverage_ok": <bool>, "notes": "..."}]}."""


def _load_checkpoint(path: Path) -> dict[str, dict[str, Any]]:
    done: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if "draft_id" in rec:
            done[str(rec["draft_id"])] = rec
    return done


def _parse_json_response(raw_text: str) -> list[dict[str, Any]]:
    clean = raw_text.strip()
    if clean.startswith("```"):
        clean = re.sub(r"^```(?:json)?\s*|\s*```$", "", clean, flags=re.DOTALL).strip()
    parsed = json.loads(clean, strict=False)
    if isinstance(parsed, dict) and isinstance(parsed.get("items"), list):
        return [x for x in parsed["items"] if isinstance(x, dict)]
    if isinstance(parsed, list):
        return [x for x in parsed if isinstance(x, dict)]
    raise ValueError("Unexpected Gemini JSON structure")


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded <= 15 RPM Gemini claim auditor for M2.3.")
    parser.add_argument("--batch-size", type=int, default=3, help="Drafts per request (default: 3 -> 5 requests).")
    parser.add_argument("--max-rpm", type=int, default=14, help="Hard RPM ceiling <= 15 (default: 14).")
    args = parser.parse_args()

    df = pd.read_csv(AUDIT_CSV, dtype=str).fillna("")
    df_videos = pd.read_parquet(
        CORPUS_VIDEOS,
        columns=["video_id", "city_norm", "poi_name", "caption", "hook_text", "transcript"],
    )
    video_map = {str(r["video_id"]): r for r in df_videos.to_dict(orient="records")}

    done_map = _load_checkpoint(CHECKPOINT_JSONL)
    pending = df[~df["draft_id"].isin(done_map.keys())]

    settings = AppSettings.from_env()
    effective_rpm = max(1, min(args.max_rpm, settings.rate_limit_rpm, 15))
    min_interval_sec = 60.0 / float(effective_rpm) + 0.3

    print(
        f"M2.3 claim audit: total={len(df)}, checkpointed={len(done_map)}, pending={len(pending)}, "
        f"model={settings.gemini_fast_model}, cap={effective_rpm} RPM"
    )

    if len(pending) > 0:
        api_key = settings.gemini_api_key.strip()
        if not api_key:
            raise ProviderKeyMissingError("GEMINI_API_KEY is missing in .env")

        from google import genai
        from google.genai import types

        limiter = SlidingWindowRateLimiter(max_rpm=effective_rpm, redis_url=None)
        client = genai.Client(api_key=api_key)
        records = pending.to_dict(orient="records")
        total_batches = (len(records) + args.batch_size - 1) // args.batch_size

        with CHECKPOINT_JSONL.open("a", encoding="utf-8") as fp:
            for b_idx in range(total_batches):
                batch = records[b_idx * args.batch_size : (b_idx + 1) * args.batch_size]
                batch_payload: list[dict[str, Any]] = []
                for row in batch:
                    ev_ids = [v for v in str(row["evidence_ids"]).split("|") if v]
                    ev_list = []
                    for vid in ev_ids:
                        src = video_map.get(vid, {})
                        ev_list.append(
                            {
                                "video_id": vid,
                                "city_norm": "" if pd.isna(src.get("city_norm")) else str(src.get("city_norm") or ""),
                                "poi_name": "" if pd.isna(src.get("poi_name")) else str(src.get("poi_name") or ""),
                                "caption": str(src.get("caption") or "")[:300],
                                "hook_text": str(src.get("hook_text") or "")[:220],
                                "transcript": str(src.get("transcript") or "")[:700],
                            }
                        )
                    batch_payload.append(
                        {
                            "draft_id": row["draft_id"],
                            "brief": row["brief"],
                            "cited_video_ids": row["cited_video_ids"],
                            "beats_preview": row["beats_preview"],
                            "source_evidence": ev_list,
                        }
                    )

                prompt = f"{SYSTEM_RULES}\n\nBATCH DATA:\n{json.dumps(batch_payload, ensure_ascii=False)}"
                limiter.acquire("m2_3_claim_audit")
                t0 = time.perf_counter()
                try:
                    resp = client.models.generate_content(
                        model=settings.gemini_fast_model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.1,
                            response_mime_type="application/json",
                        ),
                    )
                    items = _parse_json_response(resp.text or "{}")
                except QuotaBlockedError:
                    raise
                except Exception as exc:
                    safe_msg = redact_secrets(str(exc))
                    if "429" in safe_msg or "RESOURCE_EXHAUSTED" in safe_msg or "quota" in safe_msg.lower():
                        raise QuotaBlockedError(f"Gemini quota hit at batch {b_idx + 1}: {safe_msg[:200]}") from exc
                    raise RuntimeError(f"Batch {b_idx + 1} failed: {safe_msg[:240]}") from exc

                returned_by_id = {str(it["draft_id"]): it for it in items if "draft_id" in it}
                for row in batch:
                    did = str(row["draft_id"])
                    item = returned_by_id.get(did, {})
                    total_c = max(0, int(item.get("total_factual_claims", 0)))
                    sup_c = max(0, min(total_c, int(item.get("supported_factual_claims", 0))))
                    out_rec = {
                        "draft_id": did,
                        "total_factual_claims": total_c,
                        "supported_factual_claims": sup_c,
                        "citation_coverage_ok": bool(item.get("citation_coverage_ok", False)),
                        "notes": redact_secrets(str(item.get("notes", ""))[:200]),
                        "llm_model": settings.gemini_fast_model,
                    }
                    fp.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
                    done_map[did] = out_rec
                fp.flush()
                elapsed = time.perf_counter() - t0
                print(
                    f"Batch {b_idx + 1}/{total_batches} done ({len(returned_by_id)}/{len(batch)} drafts) "
                    f"in {elapsed:.2f}s"
                )
                if b_idx + 1 < total_batches:
                    wait = max(0.0, min_interval_sec - elapsed)
                    if wait > 0:
                        time.sleep(wait)

    df["N_total_factual_claims"] = df["draft_id"].map(
        lambda did: done_map.get(did, {}).get("total_factual_claims", "")
    )
    df["N_supported_factual_claims"] = df["draft_id"].map(
        lambda did: done_map.get(did, {}).get("supported_factual_claims", "")
    )
    df["N_citation_coverage_ok"] = df["draft_id"].map(
        lambda did: done_map.get(did, {}).get("citation_coverage_ok", "")
    )
    df["K_notes"] = df["draft_id"].map(
        lambda did: f"[LLM {settings.gemini_fast_model}] {done_map.get(did, {}).get('notes', '')}".strip()
        if did in done_map
        else ""
    )
    df.to_csv(AUDIT_CSV, index=False)

    total_claims = sum(int(done_map[d]["total_factual_claims"]) for d in df["draft_id"] if d in done_map)
    sup_claims = sum(int(done_map[d]["supported_factual_claims"]) for d in df["draft_id"] if d in done_map)
    cov_ok_count = sum(1 for d in df["draft_id"] if d in done_map and bool(done_map[d]["citation_coverage_ok"]))

    summary = {
        "audit_method": f"llm_assisted_{settings.gemini_fast_model}",
        "max_rpm_limit": effective_rpm,
        "drafts_audited": len(done_map),
        "total_factual_claims": total_claims,
        "supported_factual_claims": sup_claims,
        "supported_claims_ratio": round(sup_claims / max(total_claims, 1), 4),
        "citation_coverage_ok_count": cov_ok_count,
        "human_claim_audit_completed": False,
        "k_15_queries_completed": False,
        "per_draft": [done_map[d] for d in df["draft_id"] if d in done_map],
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k != "per_draft"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
