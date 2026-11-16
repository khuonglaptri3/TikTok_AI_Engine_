from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import pandas as pd

from packages.common.settings import get_settings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Optional resumable Gemini Free-Tier batch enricher for unspecified price/occasion rows."
    )
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/20261116_v1"))
    parser.add_argument("--checkpoint", type=Path, default=Path("artifacts/enrichment/checkpoint.jsonl"))
    parser.add_argument("--limit", type=int, default=20, help="Max videos to enrich in this bounded Free-Tier run.")
    parser.add_argument("--dry-run", action="store_true", help="Inspect candidate rows without calling Gemini API.")
    args = parser.parse_args()

    settings = get_settings()
    fact_path = args.corpus / "fact_videos.parquet"
    if not fact_path.is_file():
        raise SystemExit(f"Corpus not found at {fact_path}. Run pipelines.build_gold_corpus first.")

    df = pd.read_parquet(
        fact_path,
        columns=["video_id", "has_transcript", "price_tier", "video_format", "caption", "transcript"],
    )
    candidates = df[(df["has_transcript"]) & (df["price_tier"] == "unspecified")].head(args.limit)

    done_ids: set[str] = set()
    if args.checkpoint.is_file():
        for line in args.checkpoint.read_text(encoding="utf-8").splitlines():
            if line.strip():
                done_ids.add(json.loads(line)["video_id"])

    todo = [r for r in candidates.to_dict(orient="records") if r["video_id"] not in done_ids]
    if args.dry_run or not settings.gemini_api_key:
        mode = "dry_run" if args.dry_run else "skipped_no_gemini_key"
        print(json.dumps({"status": mode, "candidates_found": len(todo), "limit": args.limit}, indent=2))
        return

    from google import genai

    client = genai.Client(api_key=settings.gemini_api_key)
    args.checkpoint.parent.mkdir(parents=True, exist_ok=True)
    min_interval = 60.0 / max(settings.rate_limit_rpm, 1)

    enriched = 0
    with args.checkpoint.open("a", encoding="utf-8") as fp:
        for row in todo:
            prompt = (
                "Phân loại ngữ cảnh video ẩm thực TikTok sau thành JSON gồm price_tier "
                "(budget_lt50k|mid_50_150k|casual_150_500k|premium_gt500k|home_cooking|unspecified) "
                "và audience_persona (sinh_vien|dan_van_phong|gia_dinh|cap_doi|chung).\n"
                f"Caption: {row['caption']}\nTranscript: {str(row['transcript'])[:600]}"
            )
            resp = client.models.generate_content(
                model=settings.gemini_fast_model,
                contents=prompt,
                config={"response_mime_type": "application/json"},
            )
            payload = {"video_id": row["video_id"], "raw": resp.text or "{}"}
            fp.write(json.dumps(payload, ensure_ascii=False) + "\n")
            fp.flush()
            enriched += 1
            time.sleep(min_interval)

    print(json.dumps({"status": "completed", "enriched": enriched, "checkpoint": str(args.checkpoint)}, indent=2))


if __name__ == "__main__":
    main()
