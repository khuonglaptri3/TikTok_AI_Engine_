"""Run M5.2 4-aspect ABSA dry-run validation or blinded real-pilot annotation pool export."""
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

from packages.absa.evaluation import (
    build_m5_2_annotation_pool,
    evaluate_m5_2_aspect_sentiment,
    predict_unit_aspects,
    split_units_by_video,
    validate_and_summarize_m5_2_pool,
)
from packages.absa.spans import TextUnitInput
from packages.common.resources import get_peak_rss_mib
from packages.data_contracts.multimodal import (
    AspectSpanEvidence,
    RawCommentInput,
    RawWhisperSegment,
    TextUnitSourceKind,
)
from packages.seeding.detector import detect_seeding_comments
from packages.seeding.evaluation import compute_comment_filter_sensitivity


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _authored_m5_2_fixture_units() -> list[dict[str, Any]]:
    """Explicitly synthetic 12-video / 72-unit F&B regression fixture (NOT real pilot data)."""
    archetypes: list[list[tuple[str, TextUnitSourceKind, str, str, dict[str, str]]]] = [
        # Archetype 0: Pho hype vs viewer critique + M5.1 multi-word duplicate-spam pair
        [
            (
                "utt_0",
                "creator_utterance",
                "koc_pho",
                "Nước dùng quán phở lâu đời đậm đà ngon xuất sắc, nhân viên phục vụ nhiệt tình lắm",
                {
                    "taste": "positive",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "positive",
                },
            ),
            (
                "cmt_0",
                "viewer_comment",
                "diner_a1",
                "Nước dùng hơi mặn nhưng giá 45k bình thường",
                {
                    "taste": "negative",
                    "price": "neutral",
                    "hygiene": "absent_unknown",
                    "service": "absent_unknown",
                },
            ),
            (
                "cmt_1",
                "viewer_comment",
                "diner_a2",
                "Thịt bò không ngon, phục vụ quá chậm luôn",
                {
                    "taste": "negative",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "negative",
                },
            ),
            (
                "cmt_2",
                "viewer_comment",
                "diner_a3",
                "Nước lèo nhạt nhẽo, bàn ghế hơi bẩn",
                {
                    "taste": "negative",
                    "price": "absent_unknown",
                    "hygiene": "negative",
                    "service": "absent_unknown",
                },
            ),
            (
                "cmt_3",
                "viewer_comment",
                "seed_a1",
                "Nước dùng ở quán này đậm đà ngon xuất sắc luôn mọi người",
                {
                    "taste": "positive",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "absent_unknown",
                },
            ),
            (
                "cmt_4",
                "viewer_comment",
                "seed_a2",
                "Nước dùng ở quán này đậm đà ngon xuất sắc luôn mọi người nha",
                {
                    "taste": "positive",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "absent_unknown",
                },
            ),
        ],
        # Archetype 1: Bun cha hygiene/price focus + false-positive traps ("check in 100k views", "quán lâu đời", "ăn sạch", "giá đỗ")
        [
            (
                "utt_0",
                "creator_utterance",
                "koc_buncha",
                "Quán ăn sạch sẽ thoáng mát, mức giá hạt dẻ chỉ 35k một phần",
                {
                    "taste": "absent_unknown",
                    "price": "positive",
                    "hygiene": "positive",
                    "service": "absent_unknown",
                },
            ),
            (
                "cmt_0",
                "viewer_comment",
                "diner_b1",
                "Đỉnh của chóp luôn, hôm qua mới check in 100k views ở quán lâu đời này",
                {
                    "taste": "absent_unknown",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "absent_unknown",
                },
            ),
            (
                "cmt_1",
                "viewer_comment",
                "diner_b2",
                "Giá 35k không quá đắt nhưng bàn ghế dơ quá",
                {
                    "taste": "absent_unknown",
                    "price": "neutral",
                    "hygiene": "negative",
                    "service": "absent_unknown",
                },
            ),
            (
                "cmt_2",
                "viewer_comment",
                "diner_b3",
                "Không gian quán bẩn, sàn nhà nhớp nháp mà giá hơi đắt",
                {
                    "taste": "absent_unknown",
                    "price": "negative",
                    "hygiene": "negative",
                    "service": "absent_unknown",
                },
            ),
            (
                "cmt_3",
                "viewer_comment",
                "diner_b4",
                "Chỗ ngồi chật và vệ sinh chưa sạch, giá như vậy là bình thường",
                {
                    "taste": "absent_unknown",
                    "price": "neutral",
                    "hygiene": "negative",
                    "service": "absent_unknown",
                },
            ),
            (
                "cmt_4",
                "viewer_comment",
                "diner_b5",
                "Đói quá nên ăn sạch cả tô, cho thêm dĩa giá đỗ nhé",
                {
                    "taste": "absent_unknown",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "absent_unknown",
                },
            ),
        ],
        # Archetype 2: Com tam service/taste mix + negated neutral acceptability + unstripped whitespace idiom
        [
            (
                "utt_0",
                "creator_utterance",
                "koc_comtam",
                "Sườn nướng mềm thơm đậm vị, nhân viên phục vụ nhanh nhẹn dễ thương",
                {
                    "taste": "positive",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "positive",
                },
            ),
            (
                "cmt_0",
                "viewer_comment",
                "diner_c1",
                "  Sườn nướng thơm ngon, không gian sạch sẽ thoáng mát  ",
                {
                    "taste": "positive",
                    "price": "absent_unknown",
                    "hygiene": "positive",
                    "service": "absent_unknown",
                },
            ),
            (
                "cmt_1",
                "viewer_comment",
                "diner_c2",
                "Phục vụ cũng không tệ, giá 50k ổn áp hợp lý",
                {
                    "taste": "absent_unknown",
                    "price": "positive",
                    "hygiene": "absent_unknown",
                    "service": "neutral",
                },
            ),
            (
                "cmt_2",
                "viewer_comment",
                "diner_c3",
                "Thái độ nhân viên không chấp nhận được, lên món lâu lắm",
                {
                    "taste": "absent_unknown",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "negative",
                },
            ),
            (
                "cmt_3",
                "viewer_comment",
                "diner_c4",
                "Nhân viên phục vụ cọc cằn nhưng cơm tấm vị vẫn ngon",
                {
                    "taste": "positive",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "negative",
                },
            ),
            (
                "cmt_4",
                "viewer_comment",
                "diner_c5",
                "Ngồi từ trưa tới chiều mới thấy mặt nhân viên mang đĩa ra",
                {
                    "taste": "absent_unknown",
                    "price": "absent_unknown",
                    "hygiene": "absent_unknown",
                    "service": "negative",
                },
            ),
        ],
    ]

    rows: list[dict[str, Any]] = []
    for v_idx in range(12):
        vid = f"fixture_m5_2_vid_{v_idx:02d}"
        template = archetypes[v_idx % 3]
        for suffix, skind, handle, text, gold_aspects in template:
            sep = "utt" if skind == "creator_utterance" else "cmt"
            uid = f"{vid}::{sep}::{suffix}"
            rows.append(
                {
                    "video_id": vid,
                    "unit_id": uid,
                    "raw_local_id": suffix,
                    "author_handle": f"{handle}_{v_idx:02d}",
                    "source_kind": skind,
                    "text": text,
                    "adjudicated_aspects": dict(gold_aspects),
                }
            )
    return rows


def run_fixture_dry_run(*, output: Path) -> dict[str, Any]:
    """Validate M5.2 video-disjoint splitter, span auditor, F1/CI evaluator, and sensitivity grid on synthetic fixtures."""
    if output.exists():
        raise FileExistsError(f"Output already exists: {output}")

    raw_rows = _authored_m5_2_fixture_units()
    evaluated_rows: list[dict[str, Any]] = []
    spans_by_uid: dict[str, list[AspectSpanEvidence]] = {}
    units_by_id: dict[str, str] = {}

    for row in raw_rows:
        uid = str(row["unit_id"])
        skind: TextUnitSourceKind = row["source_kind"]
        txt = str(row["text"])
        pred_aspects, pred_spans = predict_unit_aspects(
            TextUnitInput(unit_id=uid, source_kind=skind, text=txt)
        )
        units_by_id[uid] = txt
        spans_by_uid[uid] = pred_spans
        evaluated_rows.append(
            {
                **row,
                "pred_aspects": pred_aspects,
            }
        )

    splits = split_units_by_video(evaluated_rows, video_id_col="video_id", dev_ratio=0.5, seed=42)
    dev_uids = {str(r["unit_id"]) for r in splits["dev"]}
    held_uids = {str(r["unit_id"]) for r in splits["held_out"]}

    dev_spans = [sp for uid in sorted(dev_uids) for sp in spans_by_uid[uid]]
    held_spans = [sp for uid in sorted(held_uids) for sp in spans_by_uid[uid]]
    all_spans = [sp for uid in sorted(spans_by_uid) for sp in spans_by_uid[uid]]

    total_videos = len({str(r["video_id"]) for r in evaluated_rows})
    dev_metrics = evaluate_m5_2_aspect_sentiment(
        splits["dev"],
        spans=dev_spans,
        units_by_id={uid: units_by_id[uid] for uid in dev_uids},
        is_real_pilot_data=False,
        human_signoff_complete=False,
        total_annotated_units=len(evaluated_rows),
        total_unique_videos=total_videos,
        n_boot=300,
        seed=42,
    )
    held_out_metrics = evaluate_m5_2_aspect_sentiment(
        splits["held_out"],
        spans=held_spans,
        units_by_id={uid: units_by_id[uid] for uid in held_uids},
        is_real_pilot_data=False,
        human_signoff_complete=False,
        total_annotated_units=len(evaluated_rows),
        total_unique_videos=total_videos,
        n_boot=300,
        seed=42,
    )
    all_fixture_metrics = evaluate_m5_2_aspect_sentiment(
        evaluated_rows,
        spans=all_spans,
        units_by_id=units_by_id,
        is_real_pilot_data=False,
        human_signoff_complete=False,
        total_annotated_units=len(evaluated_rows),
        total_unique_videos=total_videos,
        n_boot=300,
        seed=42,
    )

    # Video-level M5.1 filter sensitivity + 3x3 (polarity_tau, min_viewer_comments) grid summary
    rows_by_video: dict[str, list[dict[str, Any]]] = {}
    for row in evaluated_rows:
        rows_by_video.setdefault(str(row["video_id"]), []).append(row)

    sensitivity_runs: list[dict[str, Any]] = []
    for vid, v_rows in sorted(rows_by_video.items()):
        utt_rows = [r for r in v_rows if r["source_kind"] == "creator_utterance"]
        cmt_rows = [r for r in v_rows if r["source_kind"] == "viewer_comment"]
        utterances = [
            RawWhisperSegment(
                start_sec=float(idx * 3.0),
                end_sec=float((idx + 1) * 3.0),
                text=str(u["text"]),
            )
            for idx, u in enumerate(utt_rows)
        ]
        transcript = " ".join(str(u["text"]).strip() for u in utt_rows)
        raw_cmts = [
            RawCommentInput(
                comment_id=str(c["unit_id"]),
                author_handle=str(c["author_handle"]),
                text=str(c["text"]),
            )
            for c in cmt_rows
        ]
        seeded_cmts = detect_seeding_comments(vid, raw_cmts, min_duplicate_words=5)
        sens = compute_comment_filter_sensitivity(
            video_id=vid,
            caption="",
            transcript=transcript,
            comments=seeded_cmts,
            utterances=utterances,
        )
        sensitivity_runs.append({"video_id": vid, **sens})

    grid_summary: list[dict[str, Any]] = []
    for tau in (0.05, 0.15, 0.25):
        for min_c in (1, 3, 5):
            matching_cells = [
                cell
                for run in sensitivity_runs
                for cell in run["threshold_sensitivity"]
                if cell["polarity_tau"] == tau and cell["min_viewer_comments"] == min_c
            ]
            non_null_discs = [
                float(c["supported_sentiment_discrepancy"])
                for c in matching_cells
                if c["supported_sentiment_discrepancy"] is not None
            ]
            grid_summary.append(
                {
                    "polarity_tau": tau,
                    "min_viewer_comments": min_c,
                    "videos_with_supported_overlap": len(non_null_discs),
                    "mean_supported_aspect_count": round(
                        sum(int(c["supported_aspect_count"]) for c in matching_cells)
                        / max(len(matching_cells), 1),
                        4,
                    ),
                    "mean_supported_sentiment_discrepancy": (
                        round(sum(non_null_discs) / len(non_null_discs), 4)
                        if non_null_discs
                        else None
                    ),
                }
            )

    disc_shifts = [
        abs(float(r["supported_discrepancy_shift"]))
        for r in sensitivity_runs
        if r["supported_discrepancy_shift"] is not None
    ]

    repo_root = Path(__file__).resolve().parents[2]
    report: dict[str, Any] = {
        "study_id": "m5_2_fixture_dry_run_v1",
        "fixture_type": "authored_edge_regression_fixture_NOT_real_pilot",
        "real_pilot_data_available": False,
        "evaluated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
            "process_peak_rss_mib": round(float(get_peak_rss_mib()), 2),
        },
        "split_counts": {
            "dev_units": len(splits["dev"]),
            "held_out_units": len(splits["held_out"]),
            "total_units": len(evaluated_rows),
            "total_videos": total_videos,
        },
        "dev_metrics": dev_metrics,
        "held_out_metrics": held_out_metrics,
        "all_fixture_metrics": all_fixture_metrics,
        "before_after_filter_summary": {
            "videos_checked": len(sensitivity_runs),
            "videos_with_flagged_seeding": sum(
                1 for r in sensitivity_runs if int(r["flagged_indicator_count"]) > 0
            ),
            "total_flagged_comments": sum(
                int(r["flagged_indicator_count"]) for r in sensitivity_runs
            ),
            "before_supported_overlap_videos": sum(
                1 for r in sensitivity_runs if r["before_filter_supported_discrepancy"] is not None
            ),
            "after_supported_overlap_videos": sum(
                1 for r in sensitivity_runs if r["after_filter_supported_discrepancy"] is not None
            ),
            "max_abs_supported_discrepancy_shift": (
                round(max(disc_shifts), 4) if disc_shifts else 0.0
            ),
        },
        "threshold_sensitivity_summary": grid_summary,
        "provenance": {
            "code_files_sha256": {
                fname: _sha256_file(repo_root / fname)
                for fname in (
                    "packages/data_contracts/multimodal.py",
                    "packages/absa/spans.py",
                    "packages/absa/analyzer.py",
                    "packages/absa/evaluation.py",
                    "packages/seeding/evaluation.py",
                    "apps/api/app/routers/trust.py",
                    "apps/demo/presentation.py",
                    "pipelines/audit_m5_2_absa/run_baseline_checks.py",
                )
            }
        },
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as fp:
        fp.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    return report


def run_real_pool_export(
    *,
    corpus_dir: Path,
    output_pool: Path,
    output_locked_predictions: Path | None = None,
    max_units: int = 180,
    double_overlap: int = 50,
    seed: int = 42,
    require_comments: bool = True,
) -> list[dict[str, Any]]:
    """Export blinded 120-200 real pilot units + separate locked predictions JSONL from a Gold snapshot."""
    pred_path = (
        output_locked_predictions
        if output_locked_predictions is not None
        else output_pool.with_name(f"{output_pool.stem}_locked_predictions.jsonl")
    )
    if output_pool.exists():
        raise FileExistsError(f"Output pool already exists: {output_pool}")
    if pred_path.exists():
        raise FileExistsError(f"Locked predictions file already exists: {pred_path}")

    videos_pq = corpus_dir / "fact_videos.parquet"
    if not videos_pq.is_file():
        raise FileNotFoundError(f"Missing required fact_videos.parquet in {corpus_dir}")
    voice_pq = corpus_dir / "fact_voice_segments.parquet"
    comments_pq = corpus_dir / "fact_comments.parquet"

    videos_df = pd.read_parquet(videos_pq)
    voice_df = pd.read_parquet(voice_pq) if voice_pq.is_file() else None
    comments_df = pd.read_parquet(comments_pq) if comments_pq.is_file() else None
    if require_comments and (comments_df is None or comments_df.empty):
        raise ValueError(
            "fact_comments.parquet must contain non-empty viewer comments for official M5.2 real_pool export"
        )

    pool = build_m5_2_annotation_pool(
        videos_df,
        voice_df,
        comments_df,
        max_units=max_units,
        double_overlap=double_overlap,
        seed=seed,
        include_predictions=False,
    )

    locked_preds: list[dict[str, Any]] = []
    for row in pool:
        uid = str(row["unit_id"])
        skind: TextUnitSourceKind = row["source_kind"]
        txt = str(row["text"])
        pred_aspects, pred_spans = predict_unit_aspects(
            TextUnitInput(unit_id=uid, source_kind=skind, text=txt)
        )
        locked_preds.append(
            {
                "item_id": row["item_id"],
                "unit_id": uid,
                "video_id": row["video_id"],
                "source_kind": skind,
                "pred_aspects": pred_aspects,
                "pred_spans": [sp.model_dump() for sp in pred_spans],
            }
        )

    output_pool.parent.mkdir(parents=True, exist_ok=True)
    pred_path.parent.mkdir(parents=True, exist_ok=True)
    with output_pool.open("x", encoding="utf-8") as fp_pool:
        for row in pool:
            fp_pool.write(json.dumps(row, ensure_ascii=False) + "\n")
    with pred_path.open("x", encoding="utf-8") as fp_pred:
        for row in locked_preds:
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
    use_current_engine: bool = False,
    n_boot: int = 500,
    seed: int = 42,
    overwrite: bool = False,
) -> dict[str, Any]:
    """Evaluate finalized M5.2 human-verified 120-200 real pilot units against locked/current ABSA engine."""
    if output.exists() and not overwrite:
        raise FileExistsError(f"Output already exists: {output}")

    pool_rows = _read_jsonl(pool_jsonl)
    pred_rows = _read_jsonl(locked_predictions_jsonl)
    summary = validate_and_summarize_m5_2_pool(pool_rows, pred_rows)

    merged_rows: list[dict[str, Any]] = list(summary["merged_rows"])
    units_by_id: dict[str, str] = dict(summary["units_by_id"])
    locked_spans_by_uid: dict[str, list[dict[str, Any]]] = dict(summary["locked_spans_by_uid"])

    # Also compute current live engine predictions to track any dev-only lexical refinement transparently
    current_rows: list[dict[str, Any]] = []
    current_spans_by_uid: dict[str, list[dict[str, Any]]] = {}
    for r in merged_rows:
        uid = str(r["unit_id"])
        skind: TextUnitSourceKind = r["source_kind"]
        txt = str(r["text"])
        c_map, c_spans = predict_unit_aspects(
            TextUnitInput(unit_id=uid, source_kind=skind, text=txt)
        )
        current_spans_by_uid[uid] = [sp.model_dump() for sp in c_spans]
        current_rows.append(
            {
                **r,
                "pred_aspects": c_map if use_current_engine else r["pred_aspects"],
                "locked_pred_aspects": r["pred_aspects"],
                "current_pred_aspects": c_map,
            }
        )

    active_spans_by_uid = current_spans_by_uid if use_current_engine else locked_spans_by_uid

    splits = split_units_by_video(current_rows, video_id_col="video_id", dev_ratio=0.5, seed=seed)
    dev_vids = {str(r["video_id"]) for r in splits["dev"]}
    held_vids = {str(r["video_id"]) for r in splits["held_out"]}
    if dev_vids & held_vids:
        raise ValueError("Video ID overlap detected across M5.2 dev and held_out splits")

    dev_uids = {str(r["unit_id"]) for r in splits["dev"]}
    held_uids = {str(r["unit_id"]) for r in splits["held_out"]}
    total_videos = int(summary["unique_video_count"])

    dev_metrics = evaluate_m5_2_aspect_sentiment(
        splits["dev"],
        spans=[sp for uid in sorted(dev_uids) for sp in active_spans_by_uid[uid]],
        units_by_id={uid: units_by_id[uid] for uid in dev_uids},
        is_real_pilot_data=True,
        human_signoff_complete=True,
        total_annotated_units=len(current_rows),
        total_unique_videos=total_videos,
        n_boot=n_boot,
        seed=seed,
    )
    held_out_metrics = evaluate_m5_2_aspect_sentiment(
        splits["held_out"],
        spans=[sp for uid in sorted(held_uids) for sp in active_spans_by_uid[uid]],
        units_by_id={uid: units_by_id[uid] for uid in held_uids},
        is_real_pilot_data=True,
        human_signoff_complete=True,
        total_annotated_units=len(current_rows),
        total_unique_videos=total_videos,
        n_boot=n_boot,
        seed=seed,
    )
    all_pool_metrics = evaluate_m5_2_aspect_sentiment(
        current_rows,
        spans=[sp for uid in sorted(active_spans_by_uid) for sp in active_spans_by_uid[uid]],
        units_by_id=units_by_id,
        is_real_pilot_data=True,
        human_signoff_complete=True,
        total_annotated_units=len(current_rows),
        total_unique_videos=total_videos,
        n_boot=n_boot,
        seed=seed,
    )

    locked_held_out_metrics = (
        held_out_metrics
        if not use_current_engine
        else evaluate_m5_2_aspect_sentiment(
            splits["held_out"],
            spans=[sp for uid in sorted(held_uids) for sp in locked_spans_by_uid[uid]],
            units_by_id={uid: units_by_id[uid] for uid in held_uids},
            pred_col="locked_pred_aspects",
            is_real_pilot_data=True,
            human_signoff_complete=True,
            total_annotated_units=len(current_rows),
            total_unique_videos=total_videos,
            n_boot=n_boot,
            seed=seed,
        )
    )

    videos_pq = corpus_dir / "fact_videos.parquet"
    voice_pq = corpus_dir / "fact_voice_segments.parquet"
    comments_pq = corpus_dir / "fact_comments.parquet"
    v_df = pd.read_parquet(videos_pq) if videos_pq.is_file() else pd.DataFrame()
    u_df = pd.read_parquet(voice_pq) if voice_pq.is_file() else pd.DataFrame()
    c_df = pd.read_parquet(comments_pq) if comments_pq.is_file() else pd.DataFrame()

    if not v_df.empty:
        v_df["video_id"] = v_df["video_id"].astype(str)
    if not u_df.empty:
        u_df["video_id"] = u_df["video_id"].astype(str)
    if not c_df.empty:
        c_df["video_id"] = c_df["video_id"].astype(str)
        c_df["comment_id"] = c_df["comment_id"].astype(str)

    pool_vids = sorted({str(r["video_id"]) for r in current_rows})
    sensitivity_runs: list[dict[str, Any]] = []
    for vid in pool_vids:
        v_sub = v_df[v_df["video_id"] == vid] if not v_df.empty else pd.DataFrame()
        v_rec = v_sub.iloc[0].to_dict() if not v_sub.empty else {}
        caption = str(v_rec.get("caption") or v_rec.get("description") or "")
        transcript = str(v_rec.get("transcript") or v_rec.get("transcript_text") or "")

        utterances: list[RawWhisperSegment] | None = None
        if not u_df.empty:
            u_sub = u_df[u_df["video_id"] == vid].sort_values("start_sec")
            if not u_sub.empty:
                utterances = [
                    RawWhisperSegment(
                        start_sec=max(0.0, float(ur.get("start_sec") or 0.0)),
                        end_sec=max(
                            float(ur.get("start_sec") or 0.0), float(ur.get("end_sec") or 0.0)
                        ),
                        text=str(ur.get("text") or ""),
                    )
                    for ur in u_sub.to_dict("records")
                ]
                if not transcript.strip():
                    transcript = " ".join(u.text.strip() for u in utterances if u.text.strip())

        c_sub = (
            c_df[c_df["video_id"] == vid].sort_values("comment_id")
            if not c_df.empty
            else pd.DataFrame()
        )
        raw_cmts = [
            RawCommentInput(
                comment_id=str(cr["comment_id"]),
                author_handle=str(cr.get("author_handle") or ""),
                text=str(cr.get("original_text") or cr.get("text") or ""),
                like_count=int(cr.get("like_count") or 0),
                reply_count=int(cr.get("reply_count") or 0),
            )
            for cr in c_sub.to_dict("records")
        ]
        seeded_cmts = detect_seeding_comments(vid, raw_cmts, min_duplicate_words=5)
        sens = compute_comment_filter_sensitivity(
            video_id=vid,
            caption=caption,
            transcript=transcript,
            comments=seeded_cmts,
            utterances=utterances,
        )
        sensitivity_runs.append({"video_id": vid, **sens})

    grid_summary: list[dict[str, Any]] = []
    for tau in (0.05, 0.15, 0.25):
        for min_c in (1, 3, 5):
            matching_cells = [
                cell
                for run in sensitivity_runs
                for cell in run["threshold_sensitivity"]
                if cell["polarity_tau"] == tau and cell["min_viewer_comments"] == min_c
            ]
            non_null_discs = [
                float(c["supported_sentiment_discrepancy"])
                for c in matching_cells
                if c["supported_sentiment_discrepancy"] is not None
            ]
            grid_summary.append(
                {
                    "polarity_tau": tau,
                    "min_viewer_comments": min_c,
                    "videos_with_supported_overlap": len(non_null_discs),
                    "mean_supported_aspect_count": round(
                        sum(int(c["supported_aspect_count"]) for c in matching_cells)
                        / max(len(matching_cells), 1),
                        4,
                    ),
                    "mean_supported_sentiment_discrepancy": (
                        round(sum(non_null_discs) / len(non_null_discs), 4)
                        if non_null_discs
                        else None
                    ),
                }
            )

    disc_shifts = [
        abs(float(r["supported_discrepancy_shift"]))
        for r in sensitivity_runs
        if r["supported_discrepancy_shift"] is not None
    ]

    repo_root = Path(__file__).resolve().parents[2]
    data_hashes: dict[str, str] = {
        str(pool_jsonl): _sha256_file(pool_jsonl),
        str(locked_predictions_jsonl): _sha256_file(locked_predictions_jsonl),
    }
    for pq_path in (videos_pq, voice_pq, comments_pq):
        if pq_path.is_file():
            data_hashes[str(pq_path)] = _sha256_file(pq_path)

    report: dict[str, Any] = {
        "study_id": "m5_2_real_pilot_eval_v1",
        "fixture_type": "real_m3_3_pilot_double_annotated_multimodal_pool",
        "real_pilot_data_available": True,
        "prediction_source": "current_dev_refined_engine" if use_current_engine else "locked_pre_annotation_predictions",
        "evaluated_at": datetime.now(UTC).isoformat(),
        "environment": {
            "platform": platform.platform(),
            "python": sys.version,
            "cpu_count": os.cpu_count(),
            "process_peak_rss_mib": round(float(get_peak_rss_mib()), 2),
        },
        "annotation_summary": {
            "total_units": summary["total_units"],
            "unique_video_count": summary["unique_video_count"],
            "assignment_counts": summary["assignment_counts"],
            "gold_span_audit": summary["gold_span_audit"],
            "inter_annotator_agreement": summary["agreement"],
            "disagreements": summary["disagreements"],
        },
        "split_counts": {
            "dev_units": len(splits["dev"]),
            "held_out_units": len(splits["held_out"]),
            "dev_videos": len(dev_vids),
            "held_out_videos": len(held_vids),
            "total_units": len(current_rows),
            "total_videos": total_videos,
            "video_overlap_count": 0,
        },
        "dev_metrics": dev_metrics,
        "held_out_metrics": held_out_metrics,
        "locked_held_out_metrics": locked_held_out_metrics,
        "all_pool_metrics": all_pool_metrics,
        "before_after_filter_summary": {
            "videos_checked": len(sensitivity_runs),
            "videos_with_flagged_seeding": sum(
                1 for r in sensitivity_runs if int(r["flagged_indicator_count"]) > 0
            ),
            "total_flagged_comments": sum(
                int(r["flagged_indicator_count"]) for r in sensitivity_runs
            ),
            "before_supported_overlap_videos": sum(
                1 for r in sensitivity_runs if r["before_filter_supported_discrepancy"] is not None
            ),
            "after_supported_overlap_videos": sum(
                1 for r in sensitivity_runs if r["after_filter_supported_discrepancy"] is not None
            ),
            "max_abs_supported_discrepancy_shift": (
                round(max(disc_shifts), 4) if disc_shifts else 0.0
            ),
        },
        "threshold_sensitivity_summary": grid_summary,
        "provenance": {
            "code_files_sha256": {
                fname: _sha256_file(repo_root / fname)
                for fname in (
                    "packages/data_contracts/multimodal.py",
                    "packages/absa/spans.py",
                    "packages/absa/analyzer.py",
                    "packages/absa/evaluation.py",
                    "packages/seeding/evaluation.py",
                    "apps/api/app/routers/trust.py",
                    "apps/demo/presentation.py",
                    "pipelines/audit_m5_2_absa/run_baseline_checks.py",
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
    parser = argparse.ArgumentParser(
        description="Run M5.2 4-aspect ABSA fixture dry-run, real-pool export, or real-pilot eval."
    )
    parser.add_argument(
        "--mode",
        choices=("fixture_dry_run", "real_pool", "real_eval"),
        default="fixture_dry_run",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("artifacts/benchmarks/m5_2_fixture_dry_run_v1.json"),
    )
    parser.add_argument("--corpus-dir", type=Path, default=None)
    parser.add_argument("--output-pool", type=Path, default=None)
    parser.add_argument("--output-locked-predictions", type=Path, default=None)
    parser.add_argument(
        "--pool-jsonl",
        type=Path,
        default=Path("data/annotations/m5_2_pilot_pool.jsonl"),
    )
    parser.add_argument(
        "--locked-predictions-jsonl",
        type=Path,
        default=Path("data/annotations/m5_2_pilot_locked_predictions.jsonl"),
    )
    parser.add_argument("--use-current-engine", action="store_true")
    parser.add_argument("--max-units", type=int, default=180)
    parser.add_argument("--double-overlap", type=int, default=50)
    parser.add_argument("--n-boot", type=int, default=500)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.mode == "real_pool":
        if args.corpus_dir is None or not args.corpus_dir.is_dir():
            raise FileNotFoundError("--corpus-dir must point to an existing Gold snapshot directory")
        out_pool = args.output_pool if args.output_pool is not None else args.output
        pool = run_real_pool_export(
            corpus_dir=args.corpus_dir,
            output_pool=out_pool,
            output_locked_predictions=args.output_locked_predictions,
            max_units=args.max_units,
            double_overlap=args.double_overlap,
            seed=args.seed,
        )
        print(f"PASS: exported {len(pool)} blinded M5.2 pilot units to {out_pool}")
        return

    if args.mode == "real_eval":
        c_dir = (
            args.corpus_dir
            if args.corpus_dir is not None
            else Path("data/corpus/m3_3_pilot_snapshot_v2")
        )
        eval_rep = run_real_pilot_eval(
            pool_jsonl=args.pool_jsonl,
            locked_predictions_jsonl=args.locked_predictions_jsonl,
            corpus_dir=c_dir,
            output=args.output,
            use_current_engine=args.use_current_engine,
            n_boot=args.n_boot,
            seed=args.seed,
            overwrite=args.overwrite,
        )
        held = eval_rep["held_out_metrics"]
        iaa = eval_rep["annotation_summary"]["inter_annotator_agreement"]
        print(
            f"PASS: wrote {args.output} ("
            f"units={eval_rep['annotation_summary']['total_units']}, "
            f"kappa_4state={iaa['cohens_kappa_4state']}, "
            f"held_out_aspect_f1={held['aspect_detection_macro_f1']}, "
            f"held_out_sentiment_f1={held['observed_sentiment_macro_f1']}, "
            f"span_validity={held['span_audit']['validity_rate']}, "
            f"pilot_gate_eligible={held['m5_2_pilot_gate_eligible']})"
        )
        return

    report = run_fixture_dry_run(output=args.output)
    held = report["held_out_metrics"]
    print(
        f"PASS: wrote {args.output} ("
        f"held_out_aspect_f1={held['aspect_detection_macro_f1']}, "
        f"held_out_sentiment_f1={held['observed_sentiment_macro_f1']}, "
        f"span_validity={held['span_audit']['validity_rate']}, "
        f"pilot_gate_eligible={held['m5_2_pilot_gate_eligible']})"
    )


if __name__ == "__main__":
    main()
