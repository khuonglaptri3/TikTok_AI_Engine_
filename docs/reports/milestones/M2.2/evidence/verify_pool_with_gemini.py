#!/usr/bin/env python3
"""Bounded <= 15 RPM Gemini blinded pool auditor for M2.2 (resumable, preserves K/N human flags)."""

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
POOL_CSV = REPO_ROOT / "data/evaluation/v2_pilot/blinded_pool.csv"
CORPUS_VIDEOS = REPO_ROOT / "data/corpus/20261118_taxonomy_fix_v1/fact_videos.parquet"
CHECKPOINT_JSONL = OUT_DIR / "gemini_pool_audit_checkpoint.jsonl"
OUT_AUDIT_CSV = OUT_DIR / "nguyen_llm_pool_audit.csv"
OUT_SUMMARY_JSON = OUT_DIR / "nguyen_llm_pool_summary.json"

SYSTEM_RULES = """Bạn là bộ kiểm tra độc lập cho nhiệm vụ đánh giá liên quan tìm kiếm TikTok F&B Việt Nam (M2.2).
Với mỗi cặp (slot_id, query, filters, phenomenon) và thông tin video (city_norm, video_format, food_category, poi_name, caption, transcript), hãy chấm nhãn theo đúng thang 3 mức ("1", "0", "U"):
- "1" (Liên quan): Video thực sự nói/review/nấu/mukbang đúng món, thức uống hoặc chủ đề câu hỏi yêu cầu VÀ phù hợp với bộ lọc `filters` (nếu có `city_norm` phải khớp; nếu `video_format="Hướng dẫn nấu ăn"` phải là video hướng dẫn cách làm). Đồng nghĩa vùng miền đều tính là "1" (`tàu hũ`=`tào phớ`=`đậu hũ`; `Sài Gòn`=`Hồ Chí Minh`; `nước lèo`=`nước dùng`; `chả giò`=`nem rán`; `bánh flan`=`caramen`; `xiên bẩn`=`cá viên chiên`; `eat clean`=`healthy`). Với câu phủ định (`negation`, vd `không mắm tôm`, `không cay`, `không trà sữa`, `không hành`, `không dầu mỡ`), CHỈ gán "1" nếu có món chính và KHÔNG xoay quanh hoặc đề cao thành phần bị loại trừ.
- "0" (Không liên quan): Sai món, sai chủ đề (ví dụ clip nhạc nền không ăn uống, vlog đời sống), sai thành phố trong filter, hoặc vi phạm điều kiện phủ định (vd "siêu cay" cho câu hỏi "không cay").
- "U" (Chưa đủ bằng chứng / Không chắc): Transcript quá ngắn/mơ hồ hoặc không nhắc rõ điều kiện bắt buộc (vd đúng món nhưng không rõ có thành phần bị loại trừ hoặc đúng thành phố hay không).

Trả về JSON object đúng dạng:
{"items": [{"slot_id": "d_k01_s01", "rel": "1"|"0"|"U", "note": "<lý do tiếng Việt ngắn <120 ký tự>"}]}."""


def _load_checkpoint(path: Path) -> dict[str, dict[str, Any]]:
    done: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return done
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        rec = json.loads(line)
        if "slot_id" in rec:
            done[str(rec["slot_id"])] = rec
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


def _cohens_kappa(y1: list[str], y2: list[str], labels: tuple[str, ...] = ("1", "0", "U")) -> float:
    n = len(y1)
    if n == 0:
        return 0.0
    p_o = sum(1 for a, b in zip(y1, y2) if a == b) / n
    p_e = sum((y1.count(lbl) / n) * (y2.count(lbl) / n) for lbl in labels)
    return round((p_o - p_e) / (1.0 - p_e), 4) if (1.0 - p_e) > 1e-12 else 1.0


def main() -> None:
    parser = argparse.ArgumentParser(description="Bounded Gemini audit over M2.2 blinded_pool.csv.")
    parser.add_argument("--model", default="", help="Gemini model override (default: AppSettings.gemini_fast_model).")
    parser.add_argument("--batch-size", type=int, default=12, help="Rows per request (default: 12).")
    parser.add_argument("--max-rpm", type=int, default=14, help="Hard RPM ceiling (e.g., 5 for gemini-3.6-flash).")
    parser.add_argument("--limit", type=int, default=500, help="Max pending rows to process.")
    parser.add_argument(
        "--only-disagreements-from",
        type=Path,
        default=None,
        help="Optional prior summary JSON whose disagreement_slots should be re-audited with full transcript.",
    )
    parser.add_argument("--checkpoint", type=Path, default=CHECKPOINT_JSONL)
    parser.add_argument("--audit-csv", type=Path, default=OUT_AUDIT_CSV)
    parser.add_argument("--summary-json", type=Path, default=OUT_SUMMARY_JSON)
    parser.add_argument("--transcript-chars", type=int, default=500, help="Max transcript chars sent per row.")
    args = parser.parse_args()

    df_pool = pd.read_csv(POOL_CSV, dtype=str).fillna("")
    df_videos = pd.read_parquet(CORPUS_VIDEOS, columns=["video_id", "transcript"])
    tr_map = {str(r["video_id"]): str(r["transcript"] or "") for r in df_videos.to_dict(orient="records")}

    done_map = _load_checkpoint(args.checkpoint)
    target_df = df_pool
    prior_summary: dict[str, Any] = {}
    if args.only_disagreements_from is not None:
        prior_summary = json.loads(args.only_disagreements_from.read_text(encoding="utf-8"))
        disagree_ids = {str(x["slot_id"]) for x in prior_summary.get("disagreement_slots", [])}
        target_df = df_pool[df_pool["slot_id"].isin(disagree_ids)]

    pending = target_df[~target_df["slot_id"].isin(done_map.keys())].head(args.limit)

    settings = AppSettings.from_env()
    model_name = args.model.strip() or settings.gemini_fast_model
    effective_rpm = max(1, min(args.max_rpm, settings.rate_limit_rpm))
    min_interval_sec = 60.0 / float(effective_rpm) + 0.5

    print(
        f"M2.2 pool audit: target={len(target_df)}, checkpointed={len(done_map)}, pending={len(pending)}, "
        f"model={model_name}, cap={effective_rpm} RPM (interval={min_interval_sec:.1f}s)"
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

        with args.checkpoint.open("a", encoding="utf-8") as fp:
            for b_idx in range(total_batches):
                batch = records[b_idx * args.batch_size : (b_idx + 1) * args.batch_size]
                batch_payload = [
                    {
                        "slot_id": r["slot_id"],
                        "query": r["query_nfc"],
                        "filters": r["filters_json"],
                        "phenomenon": r["phenomenon"],
                        "city_norm": r["city_norm"],
                        "video_format": r["video_format"],
                        "food_category": r["food_category"],
                        "poi_name": r["poi_name"],
                        "caption": r["caption"][:300],
                        "transcript": (tr_map.get(r["video_id"]) or r["transcript_excerpt"])[: args.transcript_chars],
                    }
                    for r in batch
                ]

                prompt = f"{SYSTEM_RULES}\n\nBATCH DATA:\n{json.dumps(batch_payload, ensure_ascii=False)}"
                limiter.acquire("m2_2_pool_audit")
                t0 = time.perf_counter()
                try:
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=0.0,
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

                returned_by_slot = {str(it["slot_id"]): it for it in items if "slot_id" in it}
                for r in batch:
                    sid = str(r["slot_id"])
                    item = returned_by_slot.get(sid, {})
                    raw_rel = str(item.get("rel", "U")).strip().upper()
                    rel = raw_rel if raw_rel in ("1", "0", "U") else "U"
                    out_rec = {
                        "slot_id": sid,
                        "N_llm_rel": rel,
                        "N_llm_note": redact_secrets(str(item.get("note", ""))[:160]),
                        "llm_model": model_name,
                    }
                    fp.write(json.dumps(out_rec, ensure_ascii=False) + "\n")
                    done_map[sid] = out_rec
                fp.flush()
                elapsed = time.perf_counter() - t0
                print(
                    f"Batch {b_idx + 1}/{total_batches} done ({len(returned_by_slot)}/{len(batch)} items) "
                    f"in {elapsed:.2f}s"
                )
                if b_idx + 1 < total_batches:
                    wait = max(0.0, min_interval_sec - elapsed)
                    if wait > 0:
                        time.sleep(wait)

    # When re-checking only disagreements, also load already-agreed rows from prior CSV if requested.
    combined_map = dict(done_map)
    if args.only_disagreements_from is not None and OUT_AUDIT_CSV.is_file():
        prev_df = pd.read_csv(OUT_AUDIT_CSV, dtype=str).fillna("")
        for prev in prev_df.to_dict(orient="records"):
            sid = str(prev["slot_id"])
            if sid not in combined_map:
                combined_map[sid] = {
                    "slot_id": sid,
                    "N_llm_rel": prev["N_llm_rel"],
                    "N_llm_note": prev["N_llm_note"],
                    "llm_model": prev["llm_model"],
                }

    audit_rows: list[dict[str, Any]] = []
    for r in df_pool.to_dict(orient="records"):
        sid = str(r["slot_id"])
        rec = combined_map.get(sid)
        if rec is None:
            continue
        adj = str(r["adjudicated_rel"])
        llm_rel = str(rec["N_llm_rel"])
        audit_rows.append(
            {
                "slot_id": sid,
                "query_id": r["query_id"],
                "split": r["split"],
                "phenomenon": r["phenomenon"],
                "video_id": r["video_id"],
                "adjudicated_rel": adj,
                "N_llm_rel": llm_rel,
                "matches_adjudicated": llm_rel == adj,
                "N_llm_note": rec["N_llm_note"],
                "llm_model": rec["llm_model"],
            }
        )

    out_df = pd.DataFrame(audit_rows)
    out_df.to_csv(args.audit_csv, index=False)

    y_adj = out_df["adjudicated_rel"].tolist()
    y_llm = out_df["N_llm_rel"].tolist()
    agree_count = sum(1 for a, b in zip(y_adj, y_llm) if a == b)
    disagreements = out_df[~out_df["matches_adjudicated"]].to_dict(orient="records")

    summary = {
        "audit_method": f"llm_assisted_{model_name}"
        if args.only_disagreements_from is None
        else f"llm_assisted_gemini-3.1-flash-lite_plus_{model_name}_disagreement_recheck",
        "recheck_only_disagreements": args.only_disagreements_from is not None,
        "rechecked_count": len(done_map) if args.only_disagreements_from is not None else len(out_df),
        "max_rpm_limit": effective_rpm,
        "total_pool_rows": len(df_pool),
        "audited_rows": len(out_df),
        "agreement_count": agree_count,
        "raw_agreement_ratio": round(agree_count / max(len(out_df), 1), 4),
        "cohens_kappa_vs_adjudicated": _cohens_kappa(y_adj, y_llm),
        "n_llm_distribution": {str(k): int(v) for k, v in out_df["N_llm_rel"].value_counts().items()},
        "adjudicated_distribution": {str(k): int(v) for k, v in out_df["adjudicated_rel"].value_counts().items()},
        "agreement_by_split": {
            str(sp): round(float(grp["matches_adjudicated"].mean()), 4)
            for sp, grp in out_df.groupby("split")
        },
        "disagreement_count": len(disagreements),
        "disagreement_slots": [
            {
                "slot_id": d["slot_id"],
                "query_id": d["query_id"],
                "split": d["split"],
                "adjudicated_rel": d["adjudicated_rel"],
                "N_llm_rel": d["N_llm_rel"],
                "N_llm_note": d["N_llm_note"],
            }
            for d in disagreements
        ],
        "human_signoff_preserved": {"K_human_verified": False, "N_human_verified": False},
    }
    args.summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {k: v for k, v in summary.items() if k != "disagreement_slots"},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
