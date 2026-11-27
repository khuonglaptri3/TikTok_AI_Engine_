"""Import a Kaggle-trained PhoBERT_NER_T4-ABSA bundle (.zip or directory) and run local M5.2 evaluation."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from packages.absa.evaluation import split_units_by_video
from packages.absa.neural_absa import (
    DEFAULT_BASE_MODEL_ID,
    DEFAULT_FINETUNED_DIR,
    LoadedPhoBertAbsaModel,
    get_phobert_absa_model,
)
from packages.absa.spans import extract_unit_aspect_spans
from pipelines.train_absa_phobert.train import _evaluate_split_with_extractor, _load_jsonl

REPO_ROOT = Path(__file__).resolve().parents[2]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def import_and_evaluate_kaggle_bundle(
    source_path: Path,
    *,
    target_model_dir: Path = DEFAULT_FINETUNED_DIR,
    output_eval_path: Path = REPO_ROOT / "artifacts/benchmarks/m5_2_phobert_absa_eval_v1.json",
) -> dict[str, Any]:
    if not source_path.exists():
        raise FileNotFoundError(f"Kaggle bundle not found: {source_path}")

    target_model_dir.mkdir(parents=True, exist_ok=True)
    kaggle_metrics: dict[str, Any] = {}

    if source_path.is_file() and source_path.suffix.lower() == ".zip":
        with zipfile.ZipFile(source_path, "r") as zf:
            for member in zf.infolist():
                if member.is_dir():
                    continue
                fname = Path(member.filename).name
                if fname == "training_metrics_kaggle.json":
                    kaggle_metrics = json.loads(zf.read(member).decode("utf-8"))
                elif fname in {
                    "model.safetensors",
                    "absa_model_meta.json",
                    "config.json",
                    "tokenizer.json",
                    "tokenizer_config.json",
                    "special_tokens_map.json",
                    "vocab.txt",
                }:
                    (target_model_dir / fname).write_bytes(zf.read(member))
    elif source_path.is_dir():
        cand_dirs = [source_path, source_path / "phobert-ner-t4-absa-v1"]
        for cdir in cand_dirs:
            if (cdir / "model.safetensors").is_file():
                for fpath in cdir.iterdir():
                    if fpath.is_file() and fpath.resolve() != (target_model_dir / fpath.name).resolve():
                        shutil.copy2(fpath, target_model_dir / fpath.name)
                break
        km_path = source_path / "training_metrics_kaggle.json"
        if km_path.is_file():
            kaggle_metrics = json.loads(km_path.read_text(encoding="utf-8"))
    else:
        raise ValueError(f"Expected .zip archive or directory, got {source_path}")

    get_phobert_absa_model.cache_clear()
    reloaded = LoadedPhoBertAbsaModel.from_dir(target_model_dir)
    meta = json.loads((target_model_dir / "absa_model_meta.json").read_text(encoding="utf-8"))

    train_jsonl_path = REPO_ROOT / "data/annotations/absa_train_video_disjoint_v1.jsonl"
    pool_jsonl_path = REPO_ROOT / "data/annotations/m5_2_pilot_pool.jsonl"
    disjoint_train_rows = _load_jsonl(train_jsonl_path)
    pool_rows = _load_jsonl(pool_jsonl_path)
    splits = split_units_by_video(pool_rows, seed=42)
    dev_rows = splits["dev"]
    held_out_rows = splits["held_out"]

    train_vids = {str(r["video_id"]) for r in disjoint_train_rows}
    dev_vids = {str(r["video_id"]) for r in dev_rows}
    held_vids = {str(r["video_id"]) for r in held_out_rows}

    total_units = len(pool_rows)
    total_vids = len({str(r["video_id"]) for r in pool_rows})

    dev_pure = _evaluate_split_with_extractor(
        dev_rows,
        lambda u: reloaded.extract_unit_spans(u, hybrid_lexicon=False),
        total_units=total_units,
        total_videos=total_vids,
        n_boot=200,
    )
    held_pure = _evaluate_split_with_extractor(
        held_out_rows,
        lambda u: reloaded.extract_unit_spans(u, hybrid_lexicon=False),
        total_units=total_units,
        total_videos=total_vids,
        n_boot=300,
    )
    dev_hybrid = _evaluate_split_with_extractor(
        dev_rows,
        lambda u: reloaded.extract_unit_spans(u, hybrid_lexicon=True),
        total_units=total_units,
        total_videos=total_vids,
        n_boot=200,
    )
    held_hybrid = _evaluate_split_with_extractor(
        held_out_rows,
        lambda u: reloaded.extract_unit_spans(u, hybrid_lexicon=True),
        total_units=total_units,
        total_videos=total_vids,
        n_boot=300,
    )
    held_lexicon = _evaluate_split_with_extractor(
        held_out_rows,
        lambda u: extract_unit_aspect_spans(u, polarity_tau=0.15),
        total_units=total_units,
        total_videos=total_vids,
        n_boot=300,
    )

    receipt: dict[str, Any] = {
        "study_id": "m5_2_phobert_ner_t4_absa_finetune_v1",
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "base_model_id": str(meta.get("base_model_id") or DEFAULT_BASE_MODEL_ID),
        "architecture": meta.get("architecture", "PhoBertNerT4MultiTaskABSA"),
        "anti_leakage": {
            "train_disjoint_videos": len(train_vids),
            "train_disjoint_comments": len(disjoint_train_rows),
            "dev_videos": len(dev_vids),
            "held_out_test_videos": len(held_vids),
            "held_out_test_units": len(held_out_rows),
            "train_vs_held_out_video_overlap": len(train_vids & held_vids),
            "dev_vs_held_out_video_overlap": len(dev_vids & held_vids),
        },
        "kaggle_training_provenance": kaggle_metrics or meta,
        "models": {
            "phobert_ner_t4_finetuned": {
                "description": "Pure neural fine-tuned ThuyNT03/PhoBERT_NER_T4-ABSA multi-task checkpoint",
                "dev_metrics": {
                    "aspect_detection_macro_f1": dev_pure["aspect_detection_macro_f1"],
                    "observed_sentiment_macro_f1": dev_pure["observed_sentiment_macro_f1"],
                    "span_validity_rate": dev_pure["span_validity_rate"],
                },
                "held_out_metrics": {
                    "aspect_detection_macro_f1": held_pure["aspect_detection_macro_f1"],
                    "observed_sentiment_macro_f1": held_pure["observed_sentiment_macro_f1"],
                    "span_validity_rate": held_pure["span_validity_rate"],
                    "m5_2_pilot_gate_eligible": held_pure["m5_2_pilot_gate_eligible"],
                    "per_aspect_detection": held_pure["per_aspect_detection"],
                    "aspect_detection_macro_f1_ci95": held_pure["aspect_detection_macro_f1_ci95"],
                    "observed_sentiment_macro_f1_ci95": held_pure["observed_sentiment_macro_f1_ci95"],
                },
            },
            "phobert_hybrid": {
                "description": "Fine-tuned ThuyNT03/PhoBERT_NER_T4-ABSA neural classifier + Vietnamese F&B NFC span calibration",
                "dev_metrics": {
                    "aspect_detection_macro_f1": dev_hybrid["aspect_detection_macro_f1"],
                    "observed_sentiment_macro_f1": dev_hybrid["observed_sentiment_macro_f1"],
                    "span_validity_rate": dev_hybrid["span_validity_rate"],
                },
                "held_out_metrics": {
                    "aspect_detection_macro_f1": held_hybrid["aspect_detection_macro_f1"],
                    "observed_sentiment_macro_f1": held_hybrid["observed_sentiment_macro_f1"],
                    "span_validity_rate": held_hybrid["span_validity_rate"],
                    "m5_2_pilot_gate_eligible": held_hybrid["m5_2_pilot_gate_eligible"],
                    "per_aspect_detection": held_hybrid["per_aspect_detection"],
                    "aspect_detection_macro_f1_ci95": held_hybrid["aspect_detection_macro_f1_ci95"],
                    "observed_sentiment_macro_f1_ci95": held_hybrid["observed_sentiment_macro_f1_ci95"],
                },
            },
            "lexicon_v1": {
                "description": "Context-aware Vietnamese F&B linguistic rule/lexicon baseline",
                "held_out_metrics": {
                    "aspect_detection_macro_f1": held_lexicon["aspect_detection_macro_f1"],
                    "observed_sentiment_macro_f1": held_lexicon["observed_sentiment_macro_f1"],
                    "span_validity_rate": held_lexicon["span_validity_rate"],
                    "m5_2_pilot_gate_eligible": held_lexicon["m5_2_pilot_gate_eligible"],
                },
            },
        },
        "provenance": {
            "model_safetensors_sha256": _sha256_file(target_model_dir / "model.safetensors"),
            "train_jsonl_sha256": _sha256_file(train_jsonl_path),
            "m5_2_pilot_pool_sha256": _sha256_file(pool_jsonl_path),
        },
    }
    output_eval_path.parent.mkdir(parents=True, exist_ok=True)
    output_eval_path.write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"Imported Kaggle checkpoint into {target_model_dir}\n"
        f"  phobert_ner_t4_finetuned held_out: aspect_F1={held_pure['aspect_detection_macro_f1']}, "
        f"sent_F1={held_pure['observed_sentiment_macro_f1']}, span_valid={held_pure['span_validity_rate']}\n"
        f"  phobert_hybrid held_out: aspect_F1={held_hybrid['aspect_detection_macro_f1']}, "
        f"sent_F1={held_hybrid['observed_sentiment_macro_f1']}, span_valid={held_hybrid['span_validity_rate']}"
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Import Kaggle-trained PhoBERT ABSA bundle")
    parser.add_argument("source", type=Path, help="Path to phobert_ner_t4_absa_finetuned_bundle.zip or extracted folder")
    args = parser.parse_args()
    import_and_evaluate_kaggle_bundle(args.source)


if __name__ == "__main__":
    main()
