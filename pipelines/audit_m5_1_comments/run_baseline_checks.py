"""Run M5.1 observable comment indicator dry-run validation or real-pilot pool sampling."""
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

import pandas as pd

from packages.common.resources import get_peak_rss_mib
from packages.data_contracts.multimodal import RawCommentInput
from packages.seeding.detector import detect_seeding_comments
from packages.seeding.evaluation import (
    build_annotation_pool,
    compute_comment_filter_sensitivity,
    evaluate_comment_indicator_metrics,
    reconstruct_observable_predictions,
    split_comments_by_video,
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _authored_edge_fixture_threads() -> list[dict[str, Any]]:
    """Explicitly synthetic 12-video / 48-comment regression fixture (NOT real pilot data)."""
    specs: list[tuple[str, str, str, str]] = [
        # Organic short duplicate traps (4 distinct viewers across multiple videos)
        ("org_1", "u1", "Ngon quá", "no_indicator_observed"),
        ("org_2", "u2", "Ngon quá", "no_indicator_observed"),
        ("org_3", "u3", "Xin địa chỉ", "no_indicator_observed"),
        ("org_4", "u4", "Xin địa chỉ", "no_indicator_observed"),
        # Genuine contact / link indicators
        ("lnk_1", "s1", "Inbox em nhận voucher 50k zalo 0912345678", "contact_or_link"),
        ("lnk_2", "s2", "Xem menu full tại https://example.com/quan-an", "contact_or_link"),
        # Genuine noise / emoji spam
        ("nse_1", "e1", "😋🔥❤️", "noise_or_empty"),
        ("nse_2", "e2", "   !!! ...  ", "noise_or_empty"),
        # Multi-word near-duplicate templates
        ("dup_1", "d1", "Nước dùng ở quán này đậm đà ngon xuất sắc luôn mọi người", "observable_duplicate"),
        ("dup_2", "d2", "Nước dùng ở quán này đậm đà ngon xuất sắc luôn mọi người nha", "observable_duplicate"),
        # Clean nuanced critiques / ambiguous unknown
        ("cln_1", "r1", "Thịt bò hơi dai và mặn chát, bàn ghế bẩn phục vụ quá chậm", "no_indicator_observed"),
        ("tpl_1", "t1", "Quán ruột của mình mỗi tuần đều ghé ăn ngon xuất sắc", "template_phrase_match"),
        ("unk_1", "x1", "Chị chủ dễ tính ghê á hihi", "unknown_ambiguous"),
    ]
    rows: list[dict[str, Any]] = []
    # Replicate across 12 distinct video threads (4 per 3-way split, 48 items total; < 150 cap)
    for v_idx in range(12):
        vid = f"fixture_vid_{v_idx:02d}"
        # Keep paired duplicates inside the same thread so duplicate clusters trigger within thread
        if v_idx % 3 == 0:
            subset = specs[:6] + [specs[10]]
        elif v_idx % 3 == 1:
            subset = specs[6:13]
        else:
            subset = [specs[0], specs[1], specs[4], specs[6], specs[8], specs[9], specs[10], specs[11], specs[12]]
        for cid_suffix, handle, text, gold in subset:
            rows.append(
                {
                    "video_id": vid,
                    "comment_id": f"{vid}_{cid_suffix}",
                    "author_handle": f"{handle}_{v_idx}",
                    "text": text,
                    "adjudicated_label": gold,
                }
            )
    return rows


def run_fixture_dry_run(*, output: Path) -> dict[str, Any]:
    """Validate M5.1 splitter, organic-duplicate fix, metrics, and diagnostic gate on synthetic fixtures."""
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")

    raw_rows = _authored_edge_fixture_threads()
    by_video: dict[str, list[dict[str, Any]]] = {}
    for row in raw_rows:
        by_video.setdefault(str(row["video_id"]), []).append(row)

    evaluated_rows: list[dict[str, Any]] = []
    legacy_short_dup_fp = 0
    guarded_short_dup_fp = 0
    sensitivity_samples: list[dict[str, Any]] = []

    for vid, v_rows in sorted(by_video.items()):
        inputs = [
            RawCommentInput(
                comment_id=str(r["comment_id"]),
                author_handle=str(r["author_handle"]),
                text=str(r["text"]),
            )
            for r in v_rows
        ]
        guarded = detect_seeding_comments(vid, inputs, min_duplicate_words=5)
        legacy = detect_seeding_comments(vid, inputs, min_duplicate_words=1)

        for r, g_rec, l_rec in zip(v_rows, guarded, legacy):
            if r["adjudicated_label"] == "no_indicator_observed":
                if l_rec.observable_label == "observable_duplicate":
                    legacy_short_dup_fp += 1
                if g_rec.observable_label == "observable_duplicate":
                    guarded_short_dup_fp += 1
            evaluated_rows.append(
                {
                    **r,
                    "pred_label": g_rec.observable_label,
                    "legacy_pred_label": l_rec.observable_label,
                }
            )

        sensitivity_samples.append(
            compute_comment_filter_sensitivity(
                caption="Bún bò đậm đà ngon xuất sắc",
                transcript="Nước lèo thơm ngon không gian sạch sẽ",
                comments=guarded,
            )
        )

    splits = split_comments_by_video(evaluated_rows, video_id_col="video_id", seed=42)
    held_out_eval = evaluate_comment_indicator_metrics(
        splits["held_out_third"],
        pred_col="pred_label",
        truth_col="adjudicated_label",
        human_signoff_complete=False,
        total_annotated_pool_count=len(evaluated_rows),
        n_boot=200,
        seed=42,
    )
    full_fixture_eval = evaluate_comment_indicator_metrics(
        evaluated_rows,
        pred_col="pred_label",
        truth_col="adjudicated_label",
        human_signoff_complete=False,
        n_boot=200,
        seed=42,
    )

    repo_root = Path(__file__).resolve().parents[2]
    report = {
        "study_id": "m5_1_fixture_dry_run_v1",
        "fixture_type": "authored_edge_regression_fixture_NOT_real_pilot",
        "real_pilot_comments_available": False,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
            "process_peak_rss_mib": round(float(get_peak_rss_mib()), 2),
        },
        "organic_duplicate_ablation": {
            "legacy_min_words_1_false_positives": legacy_short_dup_fp,
            "guarded_min_words_5_false_positives": guarded_short_dup_fp,
        },
        "split_counts": {k: len(v) for k, v in splits.items()},
        "held_out_third_metrics": held_out_eval,
        "all_fixture_metrics": full_fixture_eval,
        "mean_filter_sensitivity": {
            "videos_checked": len(sensitivity_samples),
            "avg_flagged_per_video": round(
                sum(s["flagged_indicator_count"] for s in sensitivity_samples)
                / max(len(sensitivity_samples), 1),
                4,
            ),
            "max_abs_mean_score_shift": round(
                max(
                    (
                        abs(float(s["mean_score_shift"]))
                        for s in sensitivity_samples
                        if s["mean_score_shift"] is not None
                    ),
                    default=0.0,
                ),
                4,
            ),
        },
        "provenance": {
            "code_files_sha256": {
                fname: _sha256_file(repo_root / fname)
                for fname in (
                    "packages/seeding/detector.py",
                    "packages/seeding/evaluation.py",
                    "packages/data_contracts/multimodal.py",
                    "apps/api/app/routers/trust.py",
                    "apps/demo/presentation.py",
                    "pipelines/audit_m5_1_comments/run_baseline_checks.py",
                )
            }
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as fp:
        fp.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def run_real_pool_export(
    *, comments_parquet: Path, output_jsonl: Path, max_items: int = 300, seed: int = 42
) -> list[dict[str, Any]]:
    """Export <= 300 real pilot comments from M3.3 fact_comments.parquet for human K/N annotation."""
    if output_jsonl.exists():
        raise FileExistsError(f"Output pool already exists: {output_jsonl}")
    df = pd.read_parquet(comments_parquet)
    pool = build_annotation_pool(
        df,
        max_items=max_items,
        double_overlap=min(60, len(df)),
        seed=seed,
        include_predictions=False,
    )
    preds = reconstruct_observable_predictions(df, pool)
    pred_key_path = output_jsonl.with_name(f"{output_jsonl.stem}_locked_predictions.jsonl")
    if pred_key_path.exists():
        raise FileExistsError(f"Locked prediction file already exists: {pred_key_path}")
    output_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with output_jsonl.open("x", encoding="utf-8") as fp:
        for row in pool:
            fp.write(json.dumps(row, ensure_ascii=False) + "\n")
    with pred_key_path.open("x", encoding="utf-8") as fp_pred:
        for row in preds:
            fp_pred.write(json.dumps(row, ensure_ascii=False) + "\n")
    return pool


def main() -> None:
    parser = argparse.ArgumentParser(description="Run M5.1 dry-run regression or real-pilot export.")
    parser.add_argument(
        "--mode",
        choices=("fixture_dry_run", "real_pool"),
        default="fixture_dry_run",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/benchmarks/m5_1_fixture_dry_run.json"),
    )
    parser.add_argument("--comments-parquet", type=Path, default=None)
    parser.add_argument("--max-items", type=int, default=300)
    args = parser.parse_args()

    if args.mode == "real_pool":
        if args.comments_parquet is None or not args.comments_parquet.is_file():
            raise FileNotFoundError("--comments-parquet must point to an existing fact_comments.parquet")
        pool = run_real_pool_export(
            comments_parquet=args.comments_parquet,
            output_jsonl=args.output,
            max_items=args.max_items,
        )
        print(f"PASS: exported {len(pool)} pilot comments to {args.output}")
        return

    report = run_fixture_dry_run(output=args.output)
    print(
        f"PASS: wrote {args.output} ("
        f"legacy_org_dup_fp={report['organic_duplicate_ablation']['legacy_min_words_1_false_positives']} -> "
        f"guarded={report['organic_duplicate_ablation']['guarded_min_words_5_false_positives']}, "
        f"recommended_mode={report['held_out_third_metrics']['recommended_mode']})"
    )


if __name__ == "__main__":
    main()
