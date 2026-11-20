"""LLM-assisted blinded draft annotation for the M4.2 100-item historical audit workbook."""
from __future__ import annotations

import argparse
import hashlib
import json
import time
import unicodedata
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from packages.absa.disclosure import FORBIDDEN_DISCLOSURE_HASHTAGS
from packages.absa.disclosure_eval import strip_forbidden_inline_hashtags
from packages.common.exceptions import QuotaBlockedError
from packages.common.settings import AppSettings
from packages.llm.clients.gemini import BoundedGeminiClient, SlidingWindowRateLimiter

VALID_LLM_WORDING_LABELS: frozenset[str] = frozenset(
    {
        "explicit_promo_cta",
        "brand_or_venue_focus_no_cta",
        "organic_or_general_review",
        "unclear_or_noisy_text",
    }
)


class StructuredJsonClient(Protocol):
    def generate_structured_json(self, prompt: str, turn_calls_used: int = 0) -> dict[str, Any]:
        ...


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_blinded_disclosure_prompt(batch: list[dict[str, Any]]) -> str:
    """Build a flag-blinded prompt so the LLM inspects only observable Vietnamese wording."""
    payload_items: list[dict[str, Any]] = []
    for row in batch:
        clean_tags = [
            unicodedata.normalize("NFC", str(t))
            for t in (row.get("hashtags") or [])
            if unicodedata.normalize("NFC", str(t)).strip().lstrip("#").lower()
            not in FORBIDDEN_DISCLOSURE_HASHTAGS
        ]
        scrubbed_caption = strip_forbidden_inline_hashtags(str(row.get("caption") or ""))[:400]
        full_or_excerpt = str(row.get("transcript_full") or row.get("transcript_excerpt") or "")
        scrubbed_transcript = strip_forbidden_inline_hashtags(full_or_excerpt)[:3500]
        payload_items.append(
            {
                "item_id": str(row["item_id"]),
                "food_category": str(row.get("food_category") or ""),
                "has_transcript": bool(row.get("has_transcript", False)),
                "caption": scrubbed_caption,
                "transcript_excerpt": scrubbed_transcript,
                "hashtags": clean_tags[:12],
            }
        )

    instructions = (
        "You are auditing Vietnamese F&B TikTok video texts for M4.2 (observable promotional wording audit).\n"
        "IMPORTANT SCOPE RULES:\n"
        "1. Judge ONLY observable text wording (caption, transcript_excerpt, non-flag hashtags). Platform ad flags are blinded.\n"
        "2. NEVER speculate about hidden or undisclosed sponsorship intent.\n"
        "3. Assign each item exactly one `llm_observed_wording_label` from:\n"
        "   - \"explicit_promo_cta\": explicit discount/voucher, menu/branch opening promo, booking CTA, or cart/product buy link CTA (e.g., giỏ hàng, góc trái, combo, giảm giá, voucher, khai trương, đặt hàng).\n"
        "   - \"brand_or_venue_focus_no_cta\": focuses heavily on naming/praising one specific venue or product brand without explicit price/cart CTA or voucher wording.\n"
        "   - \"organic_or_general_review\": casual review, recipe, mukbang, or general eating vlog with no obvious commercial pitch CTA.\n"
        "   - \"unclear_or_noisy_text\": ASR captured background song lyrics, too short/missing transcript, or ambiguous context.\n"
        "4. Return STRICT JSON object {\"items\": [...]} matching every input `item_id` with keys:\n"
        "   - \"item_id\": string\n"
        "   - \"llm_observed_wording_label\": one of the 4 allowed labels above\n"
        "   - \"llm_observed_promo_phrases\": array of exact short Vietnamese phrases copied from text (or [])\n"
        "   - \"llm_domain_or_asr_error_note\": concise Vietnamese note explaining observed wording, domain cues, or ASR errors\n"
        "   - \"llm_commercial_cue_evident\": boolean\n\n"
        f"ITEMS:\n{json.dumps(payload_items, ensure_ascii=False)}"
    )
    return instructions


def annotate_batch_with_client(
    batch: list[dict[str, Any]],
    *,
    client: StructuredJsonClient,
    model_name: str,
) -> list[dict[str, Any]]:
    """Annotate one blinded batch while preserving human_verified=False placeholders."""
    prompt = build_blinded_disclosure_prompt(batch)
    parsed = client.generate_structured_json(prompt, turn_calls_used=0)
    raw_items = parsed.get("items")
    if not isinstance(raw_items, list):
        raise ValueError("LLM output missing 'items' list")

    by_id: dict[str, dict[str, Any]] = {}
    for entry in raw_items:
        if isinstance(entry, dict) and "item_id" in entry:
            by_id[str(entry["item_id"])] = entry

    expected_ids = [str(r["item_id"]) for r in batch]
    missing = [iid for iid in expected_ids if iid not in by_id]
    if missing:
        raise ValueError(f"LLM output missing expected item_ids: {missing}")

    annotated: list[dict[str, Any]] = []
    for row in batch:
        iid = str(row["item_id"])
        pred = by_id[iid]
        label = str(pred.get("llm_observed_wording_label") or "")
        if label not in VALID_LLM_WORDING_LABELS:
            raise ValueError(f"Invalid llm_observed_wording_label for {iid}: {label!r}")
        phrases_raw = pred.get("llm_observed_promo_phrases") or []
        phrases = [str(p).strip() for p in phrases_raw if str(p).strip()]
        note = str(pred.get("llm_domain_or_asr_error_note") or "").strip()
        cue_evident = bool(pred.get("llm_commercial_cue_evident", False))

        updated = dict(row)
        updated.update(
            {
                "llm_observed_wording_label": label,
                "llm_observed_promo_phrases": phrases,
                "llm_domain_or_asr_error_note": note,
                "llm_commercial_cue_evident": cue_evident,
                "llm_model": model_name,
                "llm_blinded_to_platform_flag": True,
                "N_human_verified": False,
                "K_human_verified": False,
            }
        )
        annotated.append(updated)
    return annotated


def summarize_llm_draft_audit(
    rows: list[dict[str, Any]], *, model_name: str, draft_path: Path
) -> dict[str, Any]:
    """Cross-tabulate blinded LLM wording labels vs observed platform flags and lexicon triggers."""
    crosstab: dict[str, dict[str, int]] = {}
    lex_agreement = {"both_positive": 0, "llm_only": 0, "lex_only": 0, "both_negative": 0}
    label_counts: dict[str, int] = {}

    for r in rows:
        flag_status = str(r["observed_flag_status"])
        llm_lbl = str(r["llm_observed_wording_label"])
        label_counts[llm_lbl] = label_counts.get(llm_lbl, 0) + 1
        bucket = crosstab.setdefault(flag_status, {})
        bucket[llm_lbl] = bucket.get(llm_lbl, 0) + 1

        llm_pos = bool(r.get("llm_commercial_cue_evident", False))
        lex_pos = float(r.get("auto_lexical_promo_score") or 0.0) > 0.0
        if llm_pos and lex_pos:
            lex_agreement["both_positive"] += 1
        elif llm_pos and not lex_pos:
            lex_agreement["llm_only"] += 1
        elif not llm_pos and lex_pos:
            lex_agreement["lex_only"] += 1
        else:
            lex_agreement["both_negative"] += 1

    return {
        "audit_id": "m4_2_llm_draft_audit_v1",
        "audited_at": datetime.now(UTC).isoformat(),
        "label_source": "llm_assisted_blinded_draft_pending_human_N_K_signoff",
        "human_signoff_complete": False,
        "model": model_name,
        "draft_jsonl_path": str(draft_path),
        "draft_jsonl_sha256": _sha256_file(draft_path),
        "total_items": len(rows),
        "llm_wording_label_counts": dict(sorted(label_counts.items())),
        "crosstab_observed_flag_vs_llm_wording": {
            k: dict(sorted(v.items())) for k, v in sorted(crosstab.items())
        },
        "commercial_cue_agreement_vs_regex_lexicon": lex_agreement,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run blinded Gemini Free-Tier draft annotation on M4.2 100-item review sheet."
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("data/evaluation/m4_2_disclosure/review_sample_100.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/evaluation/m4_2_disclosure/review_sample_100_llm_draft.jsonl"),
    )
    parser.add_argument(
        "--summary-output",
        type=Path,
        default=Path("docs/reports/milestones/M4.2/evidence/m4_2_llm_audit_summary.json"),
    )
    parser.add_argument("--batch-size", type=int, default=10)
    parser.add_argument("--max-rpm", type=int, default=12)
    parser.add_argument("--min-interval-sec", type=float, default=5.0)
    args = parser.parse_args()

    rows = [
        json.loads(line)
        for line in args.input.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    existing_by_id: dict[str, dict[str, Any]] = {}
    if args.output.exists():
        for line in args.output.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rec = json.loads(line)
                existing_by_id[str(rec["item_id"])] = rec

    settings = AppSettings.from_env().model_copy(
        update={"llm_deadline_seconds": 60.0, "rate_limit_rpm": args.max_rpm}
    )
    client = BoundedGeminiClient(
        settings=settings,
        rate_limiter=SlidingWindowRateLimiter(max_rpm=args.max_rpm, redis_url=None),
    )

    pending = [r for r in rows if str(r["item_id"]) not in existing_by_id]
    print(f"Loaded {len(rows)} items ({len(existing_by_id)} cached, {len(pending)} pending) using {settings.gemini_fast_model}")

    for start in range(0, len(pending), args.batch_size):
        batch = pending[start : start + args.batch_size]
        attempt = 0
        while True:
            attempt += 1
            try:
                annotated = annotate_batch_with_client(
                    batch, client=client, model_name=settings.gemini_fast_model
                )
                break
            except QuotaBlockedError as exc:
                if attempt >= 3:
                    raise
                print(f"Rate/quota pause on batch {start}: {exc}; sleeping 20s...")
                time.sleep(20.0)

        for rec in annotated:
            existing_by_id[str(rec["item_id"])] = rec

        # Flush incrementally in canonical item order so interrupted runs keep all completed batches
        ordered = [existing_by_id[str(r["item_id"])] for r in rows if str(r["item_id"]) in existing_by_id]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in ordered) + "\n",
            encoding="utf-8",
        )
        print(f"Annotated {len(ordered)}/{len(rows)} items")
        if start + args.batch_size < len(pending):
            time.sleep(args.min_interval_sec)

    final_rows = [existing_by_id[str(r["item_id"])] for r in rows]
    summary = summarize_llm_draft_audit(
        final_rows, model_name=settings.gemini_fast_model, draft_path=args.output
    )
    args.summary_output.parent.mkdir(parents=True, exist_ok=True)
    args.summary_output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"PASS: wrote {args.output} and {args.summary_output}")


if __name__ == "__main__":
    main()
