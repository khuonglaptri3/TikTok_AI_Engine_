#!/usr/bin/env python3
"""Automated Gemini Free-Tier (<= 15 RPM) labeler for M1.1 N_* audit columns (resumable)."""

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
AUDIT_CSV = OUT_DIR / "audit_sample_120.csv"
CHECKPOINT_JSONL = OUT_DIR / "llm_prelabels_checkpoint.jsonl"

SYSTEM_RULES = """Bạn là trợ lý audit dữ liệu TikTok F&B Việt Nam cho nhiệm vụ M1.1.
Với mỗi video trong batch, hãy đánh giá nhãn máy hiện có dựa CHỈ trên thông tin cung cấp (caption, poi_name, poi_address, poi_city, transcript_excerpt) theo quy tắc:
- city_correct: "1" nếu city_norm khớp bằng chứng (hoặc city_norm rỗng khi không nêu thành phố/quận nào); "0" nếu city_norm sai (ví dụ nhầm tên món thành thành phố) HOẶC có nêu thành phố/quận VN rõ ràng trong poi_name/poi_address/caption mà bị bỏ sót (rỗng); "U" nếu không đủ thông tin.
- city_expected: tên thành phố chuẩn tiếng Việt viết thường nếu city_correct=="0" (ví dụ "hồ chí minh", "hà nội", "đà nẵng", "huế"), hoặc "" nếu đúng/không rõ.
- format_correct: "1" / "0" / "U" cho video_format (Review quán ăn, Review món ăn, Review sản phẩm ăn uống, Hướng dẫn nấu ăn, Mukbang).
- category_correct: "1" / "0" / "U" cho food_category (nếu món rõ ràng bị rơi vào "Ẩm thực Tổng hợp" hoặc sai nhóm -> "0").
- dishes_false_positive: "1" nếu cột dishes có món gán sai/nhầm chuỗi con (ví dụ "ốc" do chữ "Trung Quốc"/"tốc độ", hoặc món không có trong text); "0" nếu không có lỗi; "U" nếu không chắc.
- price_correct: "1" / "0" / "U" cho price_tier (lưu ý "unspecified" là đúng nếu text không nói giá).
- occasion_correct: "1" / "0" / "U" cho occasions (lưu ý: nếu text không nói dịp ăn mà máy gán "an_vat_xe_chieu" -> "0").
- anatomy_usable: "NA" nếu has_transcript==False; ngược lại "1" nếu hook_text & cta_text dùng được, "0" nếu bị rác/cắt hỏng.
- notes: ghi chú ngắn gọn tiếng Việt (< 120 ký tự) giải thích lỗi nếu có.

Trả về JSON object có đúng dạng: {"items": [{"sample_no": <int>, "city_correct": "...", "city_expected": "...", "format_correct": "...", "category_correct": "...", "dishes_false_positive": "...", "price_correct": "...", "occasion_correct": "...", "anatomy_usable": "...", "notes": "..."}]}."""


def _load_checkpoint(path: Path) -> dict[int, dict[str, Any]]:
    done: dict[int, dict[str, Any]] = {}
    if not path.is_file():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if "sample_no" in rec:
            done[int(rec["sample_no"])] = rec
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
    parser = argparse.ArgumentParser(description="Bounded <=15 RPM Gemini labeler writing N_* into audit_sample_120.csv.")
    parser.add_argument("--batch-size", type=int, default=10, help="Records per request (default: 10 -> 12 requests).")
    parser.add_argument("--max-rpm", type=int, default=15, help="Hard RPM cap (default: 15).")
    parser.add_argument("--limit", type=int, default=120, help="Max total rows to process.")
    args = parser.parse_args()

    df = pd.read_csv(AUDIT_CSV, dtype=str).fillna("")
    df["sample_no_int"] = df["sample_no"].astype(int)
    done_map = _load_checkpoint(CHECKPOINT_JSONL)

    pending = df[~df["sample_no_int"].isin(done_map.keys())].head(args.limit)
    settings = AppSettings.from_env()
    effective_rpm = max(1, min(args.max_rpm, settings.rate_limit_rpm, 15))
    min_interval_sec = 60.0 / float(effective_rpm) + 0.3

    print(f"Loaded {len(df)} rows; already checkpointed={len(done_map)}; pending={len(pending)}; model={settings.gemini_fast_model}; cap={effective_rpm} RPM")

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
                batch_payload = [
                    {
                        "sample_no": int(r["sample_no_int"]),
                        "has_transcript": r["has_transcript"] == "True",
                        "poi_name": r["poi_name"],
                        "poi_address": r["poi_address"],
                        "poi_city": r["poi_city"],
                        "caption": r["caption"][:300],
                        "transcript_excerpt": r["transcript_excerpt"][:350],
                        "machine_labels": {
                            "city_norm": r["city_norm"],
                            "district_norm": r["district_norm"],
                            "location_source": r["location_source"],
                            "video_format": r["video_format"],
                            "food_category": r["food_category"],
                            "dishes": r["dishes"],
                            "price_tier": r["price_tier"],
                            "occasions": r["occasions"],
                            "hook_text": r["hook_text"][:160],
                            "cta_text": r["cta_text"][:160],
                        },
                    }
                    for r in batch
                ]

                prompt = f"{SYSTEM_RULES}\n\nBATCH DATA:\n{json.dumps(batch_payload, ensure_ascii=False)}"
                limiter.acquire("m1_1_prelabel")
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

                returned_by_no = {int(it["sample_no"]): it for it in items if "sample_no" in it}
                for r in batch:
                    s_no = int(r["sample_no_int"])
                    item = returned_by_no.get(s_no, {})
                    out_rec = {
                        "sample_no": s_no,
                        "video_id": r["video_id"],
                        "LLM_city_correct": str(item.get("city_correct", "U")),
                        "LLM_city_expected": str(item.get("city_expected", "")),
                        "LLM_format_correct": str(item.get("format_correct", "U")),
                        "LLM_category_correct": str(item.get("category_correct", "U")),
                        "LLM_dishes_false_positive": str(item.get("dishes_false_positive", "U")),
                        "LLM_price_correct": str(item.get("price_correct", "U")),
                        "LLM_occasion_correct": str(item.get("occasion_correct", "U")),
                        "LLM_anatomy_usable": str(item.get("anatomy_usable", "NA" if r["has_transcript"] != "True" else "U")),
                        "LLM_notes": redact_secrets(str(item.get("notes", ""))[:160]),
                        "LLM_model": settings.gemini_fast_model,
                    }
                    fp.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
                    done_map[s_no] = out_rec
                fp.flush()
                elapsed = time.perf_counter() - t0
                print(f"Batch {b_idx + 1}/{total_batches} done ({len(returned_by_no)}/{len(batch)} items) in {elapsed:.2f}s")
                if b_idx + 1 < total_batches:
                    wait = max(0.0, min_interval_sec - elapsed)
                    if wait > 0:
                        time.sleep(wait)

    col_mapping = {
        "N_city_correct": "LLM_city_correct",
        "N_city_expected": "LLM_city_expected",
        "N_format_correct": "LLM_format_correct",
        "N_category_correct": "LLM_category_correct",
        "N_dishes_false_positive": "LLM_dishes_false_positive",
        "N_price_correct": "LLM_price_correct",
        "N_occasion_correct": "LLM_occasion_correct",
        "N_anatomy_usable": "LLM_anatomy_usable",
        "N_notes": "LLM_notes",
    }
    for n_col, src_col in col_mapping.items():
        df[n_col] = df["sample_no_int"].map(lambda s, c=src_col: done_map.get(int(s), {}).get(c, ""))

    out_df = df.drop(columns=["sample_no_int"])
    out_df.to_csv(AUDIT_CSV, index=False)

    stats = {
        n_col: {str(k): int(v) for k, v in out_df[n_col].value_counts().items()}
        for n_col in (
            "N_city_correct",
            "N_format_correct",
            "N_category_correct",
            "N_dishes_false_positive",
            "N_price_correct",
            "N_occasion_correct",
            "N_anatomy_usable",
        )
    }
    print("UPDATED audit_sample_120.csv N_* SUMMARY:", json.dumps(stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
