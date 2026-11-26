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
from packages.data_contracts.multimodal import RawCommentInput, RawWhisperSegment
from packages.seeding.detector import detect_seeding_comments
from packages.seeding.evaluation import (
    build_annotation_pool,
    compute_comment_filter_sensitivity,
    evaluate_comment_indicator_metrics,
    reconstruct_observable_predictions,
    split_comments_by_video,
    validate_and_summarize_annotated_pool,
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


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"JSONL file not found: {path}")
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def run_real_pilot_eval(
    *,
    pool_jsonl: Path,
    locked_predictions_jsonl: Path,
    corpus_dir: Path,
    output: Path,
    n_boot: int = 1000,
    seed: int = 42,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Evaluate finalized M5.1 human-verified real pilot comments against locked predictions."""
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output}")

    pool_rows = _read_jsonl(pool_jsonl)
    pred_rows = _read_jsonl(locked_predictions_jsonl)
    summary = validate_and_summarize_annotated_pool(pool_rows, pred_rows)
    merged_rows: list[dict[str, Any]] = list(summary["merged_rows"])

    splits = split_comments_by_video(merged_rows, video_id_col="video_id", seed=seed)
    dev_vids = {str(r["video_id"]) for r in splits["dev"]}
    cal_vids = {str(r["video_id"]) for r in splits["calibration"]}
    test_vids = {str(r["video_id"]) for r in splits["held_out_third"]}
    if (dev_vids & cal_vids) or (dev_vids & test_vids) or (cal_vids & test_vids):
        raise ValueError("Video ID overlap detected across M5.1 splits")

    held_out_eval = evaluate_comment_indicator_metrics(
        splits["held_out_third"],
        pred_col="pred_label",
        truth_col="adjudicated_label",
        human_signoff_complete=True,
        total_annotated_pool_count=len(merged_rows),
        n_boot=n_boot,
        seed=seed,
    )
    dev_eval = evaluate_comment_indicator_metrics(
        splits["dev"],
        pred_col="pred_label",
        truth_col="adjudicated_label",
        human_signoff_complete=True,
        total_annotated_pool_count=len(merged_rows),
        n_boot=min(n_boot, 300),
        seed=seed,
    )
    cal_eval = evaluate_comment_indicator_metrics(
        splits["calibration"],
        pred_col="pred_label",
        truth_col="adjudicated_label",
        human_signoff_complete=True,
        total_annotated_pool_count=len(merged_rows),
        n_boot=min(n_boot, 300),
        seed=seed,
    )
    all_pool_eval = evaluate_comment_indicator_metrics(
        merged_rows,
        pred_col="pred_label",
        truth_col="adjudicated_label",
        human_signoff_complete=True,
        total_annotated_pool_count=len(merged_rows),
        n_boot=n_boot,
        seed=seed,
    )

    videos_pq = corpus_dir / "fact_videos.parquet"
    comments_pq = corpus_dir / "fact_comments.parquet"
    voice_pq = corpus_dir / "fact_voice_segments.parquet"
    v_df = pd.read_parquet(videos_pq) if videos_pq.is_file() else pd.DataFrame()
    c_df = pd.read_parquet(comments_pq) if comments_pq.is_file() else pd.DataFrame()
    u_df = pd.read_parquet(voice_pq) if voice_pq.is_file() else pd.DataFrame()

    if not v_df.empty:
        v_df["video_id"] = v_df["video_id"].astype(str)
    if not c_df.empty:
        c_df["video_id"] = c_df["video_id"].astype(str)
        c_df["comment_id"] = c_df["comment_id"].astype(str)
    if not u_df.empty:
        u_df["video_id"] = u_df["video_id"].astype(str)

    gold_by_key = {
        (str(r["video_id"]), str(r["comment_id"])): str(r["adjudicated_label"])
        for r in merged_rows
    }
    pool_vids = sorted({str(r["video_id"]) for r in merged_rows})

    legacy_short_dup_fp = 0
    guarded_short_dup_fp = 0
    sensitivity_per_video: list[dict[str, Any]] = []

    for vid in pool_vids:
        v_sub = v_df[v_df["video_id"] == vid] if not v_df.empty else pd.DataFrame()
        v_rec = v_sub.iloc[0].to_dict() if not v_sub.empty else {}
        caption = str(v_rec.get("caption") or v_rec.get("description") or "")
        transcript = str(v_rec.get("transcript") or v_rec.get("transcript_text") or "")

        c_sub = (
            c_df[c_df["video_id"] == vid].sort_values("comment_id")
            if not c_df.empty
            else pd.DataFrame()
        )
        raw_inputs = [
            RawCommentInput(
                comment_id=str(cr["comment_id"]),
                author_handle=str(cr.get("author_handle") or ""),
                text=str(cr.get("original_text") or cr.get("text") or ""),
                like_count=int(cr.get("like_count") or 0),
                reply_count=int(cr.get("reply_count") or 0),
            )
            for cr in c_sub.to_dict("records")
        ]
        guarded = detect_seeding_comments(vid, raw_inputs, min_duplicate_words=5)
        legacy = detect_seeding_comments(vid, raw_inputs, min_duplicate_words=1)

        for g_rec, l_rec in zip(guarded, legacy):
            gold_lbl = gold_by_key.get((vid, g_rec.comment_id))
            if gold_lbl == "no_indicator_observed":
                if l_rec.observable_label == "observable_duplicate":
                    legacy_short_dup_fp += 1
                if g_rec.observable_label == "observable_duplicate":
                    guarded_short_dup_fp += 1

        utterances: list[RawWhisperSegment] | None = None
        if not u_df.empty:
            u_sub = u_df[u_df["video_id"] == vid].sort_values("start_sec")
            if not u_sub.empty:
                utterances = [
                    RawWhisperSegment(
                        start_sec=max(0.0, float(ur.get("start_sec") or 0.0)),
                        end_sec=max(float(ur.get("start_sec") or 0.0), float(ur.get("end_sec") or 0.0)),
                        text=str(ur.get("text") or ""),
                    )
                    for ur in u_sub.to_dict("records")
                ]

        sens = compute_comment_filter_sensitivity(
            caption=caption,
            transcript=transcript,
            comments=guarded,
            utterances=utterances,
            video_id=vid,
        )
        sensitivity_per_video.append(
            {
                "video_id": vid,
                "total_comments": sens["total_comments"],
                "flagged_indicator_count": sens["flagged_indicator_count"],
                "unflagged_comment_count": sens["unflagged_comment_count"],
                "after_filter_abstained": sens["after_filter_abstained"],
                "before_filter_viewer_mean": sens["before_filter_viewer_mean"],
                "after_filter_viewer_mean": sens["after_filter_viewer_mean"],
                "mean_score_shift": sens["mean_score_shift"],
                "before_filter_supported_aspects": sens["before_filter_supported_aspects"],
                "after_filter_supported_aspects": sens["after_filter_supported_aspects"],
                "before_filter_supported_discrepancy": sens["before_filter_supported_discrepancy"],
                "after_filter_supported_discrepancy": sens["after_filter_supported_discrepancy"],
                "supported_discrepancy_shift": sens["supported_discrepancy_shift"],
            }
        )

    repo_root = Path(__file__).resolve().parents[2]
    data_hashes: dict[str, str] = {
        str(pool_jsonl): _sha256_file(pool_jsonl),
        str(locked_predictions_jsonl): _sha256_file(locked_predictions_jsonl),
    }
    for pq_path in (videos_pq, comments_pq, voice_pq):
        if pq_path.is_file():
            data_hashes[str(pq_path)] = _sha256_file(pq_path)

    report: dict[str, Any] = {
        "study_id": "m5_1_real_pilot_eval_v1",
        "fixture_type": "real_m3_3_pilot_double_annotated_pool",
        "real_pilot_comments_available": True,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
            "process_peak_rss_mib": round(float(get_peak_rss_mib()), 2),
        },
        "annotation_summary": {
            "total_pool_rows": summary["total_pool_rows"],
            "unique_video_count": summary["unique_video_count"],
            "assignment_counts": summary["assignment_counts"],
            "n_verified_label_counts": summary["n_verified_label_counts"],
            "k_verified_label_counts": summary["k_verified_label_counts"],
            "adjudicated_label_counts": summary["adjudicated_label_counts"],
            "inter_annotator_agreement": summary["agreement"],
            "disagreements": summary["disagreements"],
        },
        "split_counts": {k: len(v) for k, v in splits.items()},
        "split_video_counts": {
            "dev": len(dev_vids),
            "calibration": len(cal_vids),
            "held_out_third": len(test_vids),
            "video_overlap_count": 0,
        },
        "organic_duplicate_ablation_real_pool": {
            "legacy_min_words_1_false_positives": legacy_short_dup_fp,
            "guarded_min_words_5_false_positives": guarded_short_dup_fp,
        },
        "held_out_third_metrics": held_out_eval,
        "dev_metrics": dev_eval,
        "calibration_metrics": cal_eval,
        "all_pool_metrics": all_pool_eval,
        "real_corpus_filter_sensitivity": {
            "videos_checked": len(sensitivity_per_video),
            "videos_with_flagged_comments": sum(
                1 for s in sensitivity_per_video if int(s["flagged_indicator_count"]) > 0
            ),
            "total_flagged_comments": sum(
                int(s["flagged_indicator_count"]) for s in sensitivity_per_video
            ),
            "avg_flagged_per_video": round(
                sum(int(s["flagged_indicator_count"]) for s in sensitivity_per_video)
                / max(len(sensitivity_per_video), 1),
                4,
            ),
            "max_abs_mean_score_shift": round(
                max(
                    (
                        abs(float(s["mean_score_shift"]))
                        for s in sensitivity_per_video
                        if s["mean_score_shift"] is not None
                    ),
                    default=0.0,
                ),
                4,
            ),
            "max_abs_supported_discrepancy_shift": round(
                max(
                    (
                        abs(float(s["supported_discrepancy_shift"]))
                        for s in sensitivity_per_video
                        if s["supported_discrepancy_shift"] is not None
                    ),
                    default=0.0,
                ),
                4,
            ),
            "per_video": sensitivity_per_video,
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
            },
            "data_files_sha256": data_hashes,
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if overwrite else "x"
    with output.open(mode, encoding="utf-8") as fp:
        fp.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Run M5.1 dry-run regression, real-pilot export, or real-pilot eval.")
    parser.add_argument(
        "--mode",
        choices=("fixture_dry_run", "real_pool", "real_eval"),
        default="fixture_dry_run",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/benchmarks/m5_1_fixture_dry_run.json"),
    )
    parser.add_argument("--comments-parquet", type=Path, default=None)
    parser.add_argument(
        "--pool-jsonl",
        type=Path,
        default=Path("data/annotations/m5_1_pilot_pool.jsonl"),
    )
    parser.add_argument(
        "--locked-predictions-jsonl",
        type=Path,
        default=Path("data/annotations/m5_1_pilot_pool_locked_predictions.jsonl"),
    )
    parser.add_argument(
        "--corpus-dir",
        type=Path,
        default=Path("data/corpus/m3_3_pilot_snapshot_v2"),
    )
    parser.add_argument("--max-items", type=int, default=300)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--overwrite", action="store_true")
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

    if args.mode == "real_eval":
        eval_rep = run_real_pilot_eval(
            pool_jsonl=args.pool_jsonl,
            locked_predictions_jsonl=args.locked_predictions_jsonl,
            corpus_dir=args.corpus_dir,
            output=args.output,
            n_boot=args.n_boot,
            overwrite=args.overwrite,
        )
        hm = eval_rep["held_out_third_metrics"]
        iaa = eval_rep["annotation_summary"]["inter_annotator_agreement"]
        print(
            f"PASS: wrote {args.output} ("
            f"pool={eval_rep['annotation_summary']['total_pool_rows']}, "
            f"kappa={iaa['cohens_kappa']}, "
            f"held_out_P={hm['macro_precision']}, "
            f"held_out_R={hm['macro_recall']}, "
            f"recommended_mode={hm['recommended_mode']})"
        )
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
