"""Run M4.2 corpus audit, 100-item review sampling, and leakage-free grouped classifier."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from packages.absa.disclosure import (
    analyze_disclosure_and_promo,
    classify_observed_disclosure_flags,
)
from packages.absa.disclosure_eval import (
    compute_pu_observable_summary,
    evaluate_observed_ad_vs_ec_classifier,
)
from packages.analytics import load_verified_corpus
from packages.common.resources import get_peak_rss_mib


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sample_historical_review_100(df: pd.DataFrame, *, seed: int = 42) -> list[dict[str, Any]]:
    """Sample 100 stratified historical texts with deterministic 30 double-review overlap."""
    rng = np.random.default_rng(seed)
    work = df.copy()
    work["observed_flag_status"] = [
        classify_observed_disclosure_flags(bool(a), bool(e))
        for a, e in zip(
            work["is_ad"].fillna(False).tolist(),
            work["is_ec_video"].fillna(False).tolist(),
        )
    ]

    # Allocation sums to 100 unique historical texts across all 4 observable flag strata.
    targets: tuple[tuple[str, int, int], ...] = (
        ("observed_ad", 15, 10),
        ("observed_ecommerce", 15, 10),
        ("observed_ad_and_ecommerce", 10, 5),
        ("unlabeled_unknown", 20, 15),
    )

    chosen_frames: list[pd.DataFrame] = []
    for status, n_trans, n_cap in targets:
        sub = work[work["observed_flag_status"] == status].sort_values("video_id").reset_index(drop=True)
        tr_pool = sub[sub["has_transcript"].fillna(False)]
        cap_pool = sub[~sub["has_transcript"].fillna(False)]

        if len(tr_pool) >= n_trans and len(cap_pool) >= n_cap:
            tr_idx = rng.choice(len(tr_pool), size=n_trans, replace=False)
            cap_idx = rng.choice(len(cap_pool), size=n_cap, replace=False)
            chosen_frames.append(tr_pool.iloc[tr_idx])
            chosen_frames.append(cap_pool.iloc[cap_idx])
        else:
            total_needed = min(n_trans + n_cap, len(sub))
            any_idx = rng.choice(len(sub), size=total_needed, replace=False)
            chosen_frames.append(sub.iloc[any_idx])

    sampled_df = pd.concat(chosen_frames, ignore_index=True)
    perm = rng.permutation(len(sampled_df))
    sampled_df = sampled_df.iloc[perm].reset_index(drop=True)

    # First 30 shuffled items go to both N and K; remaining 70 split 35/35 between N and K.
    records: list[dict[str, Any]] = []
    for i, row in enumerate(sampled_df.to_dict("records")):
        if i < 30:
            assignment = "double_review_N_K"
        elif i < 65:
            assignment = "N_only"
        else:
            assignment = "K_only"

        caption = str(row.get("caption") or "")
        transcript = str(row.get("transcript") or "")
        raw_tags = row.get("hashtags")
        tags = (
            [str(t) for t in raw_tags.tolist()]
            if hasattr(raw_tags, "tolist")
            else list(raw_tags or [])
        )
        analysis = analyze_disclosure_and_promo(
            caption=caption,
            transcript=transcript,
            is_ad=bool(row.get("is_ad", False)),
            is_ec_video=bool(row.get("is_ec_video", False)),
            hashtags=tags,
        )
        records.append(
            {
                "item_id": f"m4_2_{i + 1:03d}",
                "video_id": str(row["video_id"]),
                "author_handle": str(row["author_handle"]),
                "food_category": str(row.get("food_category") or ""),
                "has_transcript": bool(row.get("has_transcript", False)),
                "caption": caption,
                "transcript_excerpt": transcript[:600],
                "transcript_full": transcript,
                "hashtags": tags,
                "observed_flag_status": analysis.disclosure_flag_status,
                "auto_lexical_promo_indicators": analysis.matched_indicators,
                "auto_lexical_promo_score": analysis.lexical_promo_score,
                "review_assignment": assignment,
                "N_observed_wording_label": None,
                "N_error_or_domain_note": "",
                "N_human_verified": False,
                "K_observed_wording_label": None,
                "K_error_or_domain_note": "",
                "K_human_verified": False,
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run M4.2 observed disclosure/commerce study and generate 100-item review workbook."
    )
    parser.add_argument("--corpus", type=Path, default=Path("data/corpus/20261118_taxonomy_fix_v1"))
    parser.add_argument(
        "--review-output",
        type=Path,
        default=Path("data/evaluation/m4_2_disclosure/review_sample_100.jsonl"),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/benchmarks/m4_2_observed_disclosure_study.json"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.review_output.exists():
        raise FileExistsError(f"Review workbook already exists: {args.review_output}")
    if args.output.exists():
        raise FileExistsError(f"Study receipt already exists: {args.output}")

    manifest, _, df_videos = load_verified_corpus(args.corpus)

    pu_summary = compute_pu_observable_summary(df_videos)
    review_items = sample_historical_review_100(df_videos, seed=args.seed)

    clf_all = evaluate_observed_ad_vs_ec_classifier(
        df_videos,
        test_fraction=0.30,
        seed=args.seed,
        n_boot=500,
        min_df=3,
    )
    df_transcribed = df_videos[df_videos["has_transcript"].fillna(False)].copy()
    clf_transcribed = evaluate_observed_ad_vs_ec_classifier(
        df_transcribed,
        test_fraction=0.30,
        seed=args.seed,
        n_boot=500,
        min_df=2,
    )

    args.review_output.parent.mkdir(parents=True, exist_ok=True)
    with args.review_output.open("x", encoding="utf-8") as fp:
        for rec in review_items:
            fp.write(json.dumps(rec, ensure_ascii=False) + "\n")

    repo_root = Path(__file__).resolve().parents[2]
    report = {
        "study_id": "m4_2_observed_disclosure_study_v1",
        "corpus_snapshot_id": manifest.snapshot_id,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
            "process_peak_rss_mib": round(float(get_peak_rss_mib()), 2),
        },
        "target_policy": {
            "undisclosed_sponsorship_status": "DEFERRED",
            "unlabeled_items_treated_as_verified_negative": False,
            "flag_feature_leakage_excluded": True,
            "historical_audio_prosody_joined": False,
        },
        "review_workbook": {
            "path": str(args.review_output),
            "sha256": _sha256_file(args.review_output),
            "total_items": len(review_items),
            "double_review_overlap_count": sum(
                1 for r in review_items if r["review_assignment"] == "double_review_N_K"
            ),
            "N_assigned_count": sum(
                1
                for r in review_items
                if r["review_assignment"] in {"double_review_N_K", "N_only"}
            ),
            "K_assigned_count": sum(
                1
                for r in review_items
                if r["review_assignment"] in {"double_review_N_K", "K_only"}
            ),
            "human_review_completed": False,
        },
        "corpus_pu_observable_summary": pu_summary,
        "grouped_genuine_target_classifiers": {
            "all_observed_ad_only_vs_ec_only": clf_all,
            "transcribed_observed_ad_only_vs_ec_only": clf_transcribed,
        },
        "provenance": {
            "corpus_manifest_sha256": _sha256_file(args.corpus / "manifest.json"),
            "code_files_sha256": {
                fname: _sha256_file(repo_root / fname)
                for fname in (
                    "packages/absa/disclosure.py",
                    "packages/absa/disclosure_eval.py",
                    "packages/absa/analyzer.py",
                    "packages/data_contracts/multimodal.py",
                    "apps/demo/presentation.py",
                    "pipelines/audit_m4_2_disclosure/run_study.py",
                )
            },
        },
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as fp:
        fp.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(
        f"PASS: wrote {args.output} and {args.review_output} "
        f"(all PR-AUC={clf_all['metrics']['pr_auc']}, Brier={clf_all['metrics']['brier_score']}; "
        f"transcribed PR-AUC={clf_transcribed['metrics']['pr_auc']}, Brier={clf_transcribed['metrics']['brier_score']})"
    )


if __name__ == "__main__":
    main()
