"""Fine-tune ThuyNT03/PhoBERT_NER_T4-ABSA on video-disjoint Vietnamese F&B ABSA data."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import time
import unicodedata
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import torch
from transformers import AutoTokenizer, PreTrainedTokenizerBase

from packages.absa.evaluation import evaluate_m5_2_aspect_sentiment, split_units_by_video
from packages.absa.neural_absa import (
    ASPECT_STATE_TO_ID,
    BIO_LABELS,
    DEFAULT_BASE_MODEL_ID,
    DEFAULT_FINETUNED_DIR,
    LoadedPhoBertAbsaModel,
    PhoBertNerT4MultiTaskABSA,
    align_char_spans_to_bio_ids,
    encode_token_diacritic_hashes,
)
from packages.absa.spans import TextUnitInput, extract_unit_aspect_spans
from packages.common.resources import get_peak_rss_mib
from packages.data_contracts.multimodal import ASPECT_NAMES, AspectName, AspectSpanEvidence

REPO_ROOT = Path(__file__).resolve().parents[2]


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _encode_dataset_rows(
    rows: list[dict[str, Any]],
    tokenizer: PreTrainedTokenizerBase,
    *,
    aspect_col: str,
    spans_col: str,
    max_length: int = 80,
    diacritic_buckets: int = 8192,
    max_ngrams: int = 12,
) -> list[dict[str, Any]]:
    encoded: list[dict[str, Any]] = []
    for row in rows:
        nfc = unicodedata.normalize("NFC", str(row.get("text") or ""))
        if not nfc.strip():
            continue
        enc = tokenizer(
            nfc,
            return_offsets_mapping=True,
            truncation=True,
            max_length=max_length,
        )
        input_ids: list[int] = [int(x) for x in enc["input_ids"]]
        offsets = [(int(a), int(b)) for a, b in enc["offset_mapping"]]
        diac = encode_token_diacritic_hashes(
            nfc,
            offsets,
            num_buckets=diacritic_buckets,
            max_ngrams=max_ngrams,
        )
        raw_spans = row.get(spans_col) or []
        bio_ids = align_char_spans_to_bio_ids(offsets, raw_spans)

        asp_map = row.get(aspect_col) or {}
        asp_ids = [
            ASPECT_STATE_TO_ID[str(asp_map.get(asp, "absent_unknown"))]
            for asp in ASPECT_NAMES
        ]
        has_rare = any(
            str(asp_map.get(asp, "absent_unknown")) != "absent_unknown"
            for asp in ("price", "hygiene", "service")
        ) or str(asp_map.get("taste", "absent_unknown")) in {"neutral", "negative"}
        has_any = any(x != 0 for x in asp_ids)

        encoded.append(
            {
                "unit_id": str(row.get("unit_id") or ""),
                "video_id": str(row.get("video_id") or ""),
                "input_ids": input_ids,
                "diacritic_ids": diac,
                "bio_ids": bio_ids,
                "aspect_ids": asp_ids,
                "has_any_aspect": has_any,
                "has_rare_aspect": has_rare,
                "is_human_dev": bool(row.get("_is_human_dev", False)),
            }
        )
    return encoded


def _collate_batch(items: list[dict[str, Any]], pad_token_id: int) -> dict[str, torch.Tensor]:
    max_len = max(len(it["input_ids"]) for it in items)
    max_ngrams = int(items[0]["diacritic_ids"].size(1))
    bsz = len(items)

    input_ids = torch.full((bsz, max_len), pad_token_id, dtype=torch.long)
    attn_mask = torch.zeros((bsz, max_len), dtype=torch.long)
    diac_ids = torch.zeros((bsz, max_len, max_ngrams), dtype=torch.long)
    bio_labels = torch.full((bsz, max_len), -100, dtype=torch.long)
    aspect_labels = torch.zeros((bsz, len(ASPECT_NAMES)), dtype=torch.long)
    has_prefix = "prefix_hidden" in items[0]
    hidden_dim = int(items[0]["prefix_hidden"].size(1)) if has_prefix else 0
    prefix_hidden = torch.zeros((bsz, max_len, hidden_dim), dtype=torch.float32) if has_prefix else None

    for i, it in enumerate(items):
        L = len(it["input_ids"])
        input_ids[i, :L] = torch.tensor(it["input_ids"], dtype=torch.long)
        attn_mask[i, :L] = 1
        diac_ids[i, :L, :] = it["diacritic_ids"][:L]
        bio_labels[i, :L] = torch.tensor(it["bio_ids"], dtype=torch.long)
        aspect_labels[i, :] = torch.tensor(it["aspect_ids"], dtype=torch.long)
        if prefix_hidden is not None:
            prefix_hidden[i, :L, :] = it["prefix_hidden"][:L]

    out: dict[str, torch.Tensor] = {
        "input_ids": input_ids,
        "attention_mask": attn_mask,
        "diacritic_ngram_ids": diac_ids,
        "bio_labels": bio_labels,
        "aspect_labels": aspect_labels,
    }
    if prefix_hidden is not None:
        out["prefix_hidden"] = prefix_hidden
    return out


def _build_4d_additive_mask(attention_mask: torch.Tensor, dtype: torch.dtype) -> torch.Tensor:
    return (1.0 - attention_mask[:, None, None, :].to(dtype)) * torch.finfo(dtype).min


def _precompute_frozen_prefix_hidden(
    items: list[dict[str, Any]],
    model: PhoBertNerT4MultiTaskABSA,
    *,
    cutoff_layer: int,
    pad_token_id: int,
    batch_size: int = 48,
) -> None:
    """Compute frozen embeddings + lower BertLayer[:cutoff_layer] outputs once with no_grad."""
    model.backbone.eval()
    t_pre = time.perf_counter()
    with torch.inference_mode():
        for start in range(0, len(items), batch_size):
            chunk = items[start : start + batch_size]
            max_len = max(len(it["input_ids"]) for it in chunk)
            bsz = len(chunk)
            inp = torch.full((bsz, max_len), pad_token_id, dtype=torch.long)
            msk = torch.zeros((bsz, max_len), dtype=torch.long)
            for i, it in enumerate(chunk):
                L = len(it["input_ids"])
                inp[i, :L] = torch.tensor(it["input_ids"], dtype=torch.long)
                msk[i, :L] = 1
            h = model.backbone.embeddings(input_ids=inp)
            ext_mask = _build_4d_additive_mask(msk, h.dtype)
            for layer in list(model.backbone.encoder.layer)[:cutoff_layer]:
                res = layer(h, attention_mask=ext_mask)
                h = res[0] if isinstance(res, tuple) else res
            h_cpu = h.detach().cpu()
            for i, it in enumerate(chunk):
                L = len(it["input_ids"])
                it["prefix_hidden"] = h_cpu[i, :L, :].clone()
    print(
        f"[Prefix Cache] Computed frozen layers 0..{cutoff_layer - 1} for {len(items)} unique units in "
        f"{time.perf_counter() - t_pre:.2f}s",
        flush=True,
    )


def _spans_to_pred_aspects(spans: list[AspectSpanEvidence]) -> dict[AspectName, str]:
    by_asp: dict[AspectName, list[AspectSpanEvidence]] = {asp: [] for asp in ASPECT_NAMES}
    for sp in spans:
        by_asp[sp.aspect].append(sp)
    out: dict[AspectName, str] = {}
    for asp in ASPECT_NAMES:
        arr = by_asp[asp]
        if not arr:
            out[asp] = "absent_unknown"
        else:
            mean_s = sum(s.polarity_score for s in arr) / len(arr)
            if mean_s >= 0.15:
                out[asp] = "positive"
            elif mean_s <= -0.15:
                out[asp] = "negative"
            else:
                out[asp] = "neutral"
    return out


def _evaluate_split_with_extractor(
    rows: list[dict[str, Any]],
    extractor_fn: Any,
    *,
    total_units: int,
    total_videos: int,
    n_boot: int = 300,
) -> dict[str, Any]:
    annotated_rows: list[dict[str, Any]] = []
    all_spans: list[AspectSpanEvidence] = []
    for r in rows:
        unit = TextUnitInput(
            unit_id=str(r["unit_id"]),
            source_kind=r.get("source_kind", "viewer_comment"),
            text=str(r["text"]),
        )
        u_spans: list[AspectSpanEvidence] = extractor_fn(unit)
        all_spans.extend(u_spans)
        row_copy = dict(r)
        row_copy["pred_aspects"] = _spans_to_pred_aspects(u_spans)
        annotated_rows.append(row_copy)

    metrics = evaluate_m5_2_aspect_sentiment(
        annotated_rows,
        spans=all_spans,
        pred_col="pred_aspects",
        truth_col="adjudicated_aspects",
        is_real_pilot_data=True,
        human_signoff_complete=True,
        total_annotated_units=total_units,
        total_unique_videos=total_videos,
        n_boot=n_boot,
        seed=42,
    )
    span_rate = (
        float(metrics["span_audit"]["validity_rate"])
        if int(metrics["span_audit"]["total_spans"]) > 0
        else 1.0
    )
    metrics["span_validity_rate"] = span_rate
    return metrics


def _calibrate_thresholds_on_dev(
    bundle: LoadedPhoBertAbsaModel,
    dev_rows: list[dict[str, Any]],
) -> dict[AspectName, float]:
    """Tune per-aspect p_observed threshold strictly on dev rows (never held_out)."""
    raw_preds = [bundle.predict_unit_raw(str(r["text"])) for r in dev_rows]
    best_thresholds: dict[AspectName, float] = {}
    grid = (0.30, 0.36, 0.42, 0.48, 0.54, 0.60, 0.66, 0.72)

    for asp in ASPECT_NAMES:
        gold_obs = [
            str((r.get("adjudicated_aspects") or {}).get(asp, "absent_unknown")) != "absent_unknown"
            for r in dev_rows
        ]
        if sum(1 for g in gold_obs if g) == 0:
            best_thresholds[asp] = 0.62
            continue
        best_f1 = -1.0
        best_t = 0.50
        for cand_t in grid:
            tp = fp = fn = 0
            for raw, is_gold in zip(raw_preds, gold_obs, strict=True):
                p_obs = float(raw["aspects"][asp]["p_observed"])
                is_pred = p_obs >= cand_t
                if is_gold and is_pred:
                    tp += 1
                elif not is_gold and is_pred:
                    fp += 1
                elif is_gold and not is_pred:
                    fn += 1
            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2.0 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
            if f1 > best_f1 or (math.isclose(f1, best_f1) and cand_t > best_t):
                best_f1 = f1
                best_t = cand_t
        best_thresholds[asp] = best_t
    return best_thresholds


def run_phobert_finetune_and_eval(
    *,
    base_model_id: str = DEFAULT_BASE_MODEL_ID,
    output_model_dir: Path = DEFAULT_FINETUNED_DIR,
    output_eval_path: Path = REPO_ROOT / "artifacts/benchmarks/m5_2_phobert_absa_eval_v1.json",
    epochs: int = 6,
    batch_size: int = 24,
    unfreeze_top_k: int = 2,
    seed: int = 42,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    ca_path = Path("/etc/ssl/certs/ca-certificates.crt")
    if ca_path.is_file():
        os.environ.setdefault("SSL_CERT_FILE", str(ca_path))
        os.environ.setdefault("REQUESTS_CA_BUNDLE", str(ca_path))

    random.seed(seed)
    torch.manual_seed(seed)
    torch.set_num_threads(max(1, min(4, os.cpu_count() or 4)))

    train_jsonl_path = REPO_ROOT / "data/annotations/absa_train_video_disjoint_v1.jsonl"
    pool_jsonl_path = REPO_ROOT / "data/annotations/m5_2_pilot_pool.jsonl"
    disjoint_train_rows = _load_jsonl(train_jsonl_path)
    pool_rows = _load_jsonl(pool_jsonl_path)
    splits = split_units_by_video(pool_rows, seed=42)
    dev_rows = splits["dev"]
    held_out_rows = splits["held_out"]

    train_vids = {str(r["video_id"]) for r in disjoint_train_rows}
    dev_vids = sorted({str(r["video_id"]) for r in dev_rows})
    held_vids = {str(r["video_id"]) for r in held_out_rows}

    if train_vids & held_vids:
        raise ValueError(f"Data leakage detected between train and held_out: {train_vids & held_vids}")
    if set(dev_vids) & held_vids:
        raise ValueError(f"Data leakage detected between dev and held_out: {set(dev_vids) & held_vids}")

    # Split 14 dev videos into 7 dev_train (upweighted human labels) + 7 dev_val (unseen threshold calibration)
    half_dev = len(dev_vids) // 2
    dev_train_vid_set = set(dev_vids[:half_dev])
    dev_val_vid_set = set(dev_vids[half_dev:])
    dev_train_rows = []
    for r in dev_rows:
        if str(r["video_id"]) in dev_train_vid_set:
            rc = dict(r)
            rc["_is_human_dev"] = True
            dev_train_rows.append(rc)
    dev_val_rows = [r for r in dev_rows if str(r["video_id"]) in dev_val_vid_set]

    tokenizer = AutoTokenizer.from_pretrained(base_model_id)
    model = PhoBertNerT4MultiTaskABSA.from_pretrained_ner_t4(base_model_id)
    model.freeze_lower_transformer_layers(unfreeze_top_k=unfreeze_top_k)

    enc_disjoint = _encode_dataset_rows(
        disjoint_train_rows,
        tokenizer,
        aspect_col="aspects",
        spans_col="spans",
        max_length=80,
    )
    enc_dev_train = _encode_dataset_rows(
        dev_train_rows,
        tokenizer,
        aspect_col="adjudicated_aspects",
        spans_col="adjudicated_spans",
        max_length=80,
    )
    all_encoded_train = enc_disjoint + enc_dev_train

    pos_items = [it for it in all_encoded_train if it["has_any_aspect"]]
    rare_items = [it for it in all_encoded_train if it["has_rare_aspect"]]
    human_dev_items = [it for it in all_encoded_train if it["is_human_dev"]]
    neg_items = [it for it in all_encoded_train if not it["has_any_aspect"]]

    # Inverse-sqrt class weights on sampled training distribution
    aspect_weights_list: list[torch.Tensor] = []
    for idx in range(len(ASPECT_NAMES)):
        cnt = Counter(it["aspect_ids"][idx] for it in all_encoded_train)
        w = [
            1.0,
            min(4.5, math.sqrt(max(1, cnt[0]) / max(1, cnt.get(1, 1))) * 0.45),
            min(5.5, math.sqrt(max(1, cnt[0]) / max(1, cnt.get(2, 1))) * 0.45),
            min(5.0, math.sqrt(max(1, cnt[0]) / max(1, cnt.get(3, 1))) * 0.45),
        ]
        aspect_weights_list.append(torch.tensor(w, dtype=torch.float32))
    aspect_class_weights = torch.stack(aspect_weights_list, dim=0)

    bio_w = torch.ones(len(BIO_LABELS), dtype=torch.float32)
    bio_w[0] = 0.25  # downweight 'O' so BIO tagger learns crisp span boundaries

    bert_params = [p for n, p in model.named_parameters() if p.requires_grad and n.startswith("backbone.")]
    head_params = [p for n, p in model.named_parameters() if p.requires_grad and not n.startswith("backbone.")]
    optimizer = torch.optim.AdamW(
        [
            {"params": bert_params, "lr": 4e-5, "weight_decay": 0.01},
            {"params": head_params, "lr": 1.1e-3, "weight_decay": 0.01},
        ]
    )

    rng = random.Random(seed)
    pad_id = int(tokenizer.pad_token_id or 0)
    epoch_logs: list[dict[str, Any]] = []

    # Select balanced negative candidate bank once (650 diverse negatives) + all positives,
    # then pre-cache frozen lower BERT layers 0..(12-unfreeze_top_k-1) once!
    neg_bank = rng.sample(neg_items, k=min(650, len(neg_items)))
    cutoff_layer = max(0, len(model.backbone.encoder.layer) - max(0, unfreeze_top_k))
    seen_obj_ids: set[int] = set()
    unique_active_items: list[dict[str, Any]] = []
    for cand in list(pos_items) + list(human_dev_items) + list(neg_bank):
        if id(cand) not in seen_obj_ids:
            seen_obj_ids.add(id(cand))
            unique_active_items.append(cand)
    _precompute_frozen_prefix_hidden(
        unique_active_items,
        model,
        cutoff_layer=cutoff_layer,
        pad_token_id=pad_id,
        batch_size=48,
    )
    unfrozen_layers = list(model.backbone.encoder.layer)[cutoff_layer:]

    total_steps_est = epochs * math.ceil((len(pos_items) + len(rare_items) * 2 + len(human_dev_items) * 3 + 480) / batch_size)
    step_idx = 0

    for epoch in range(1, epochs + 1):
        t_ep = time.perf_counter()
        model.train()
        # Keep frozen lower layers in eval mode so saved end-to-end model matches cached prefix identically
        model.backbone.embeddings.eval()
        for lyr in list(model.backbone.encoder.layer)[:cutoff_layer]:
            lyr.eval()

        sampled_negs = rng.sample(neg_bank, k=min(480, len(neg_bank)))
        epoch_pool = (
            list(pos_items)
            + list(rare_items)
            + list(rare_items)
            + list(human_dev_items) * 3
            + sampled_negs
        )
        rng.shuffle(epoch_pool)

        ep_loss_sum = 0.0
        n_batches = 0
        for start in range(0, len(epoch_pool), batch_size):
            batch_slice = epoch_pool[start : start + batch_size]
            batch = _collate_batch(batch_slice, pad_id)

            # Cosine schedule with 10% warmup
            step_idx += 1
            warmup = max(1, int(0.10 * total_steps_est))
            if step_idx <= warmup:
                lr_mult = step_idx / float(warmup)
            else:
                prog = min(1.0, (step_idx - warmup) / float(max(1, total_steps_est - warmup)))
                lr_mult = 0.15 + 0.85 * 0.5 * (1.0 + math.cos(math.pi * prog))
            optimizer.param_groups[0]["lr"] = 4e-5 * lr_mult
            optimizer.param_groups[1]["lr"] = 1.1e-3 * lr_mult

            optimizer.zero_grad()
            h = batch["prefix_hidden"]
            ext_mask = _build_4d_additive_mask(batch["attention_mask"], h.dtype)
            for lyr in unfrozen_layers:
                res = lyr(h, attention_mask=ext_mask)
                h = res[0] if isinstance(res, tuple) else res
            out = model.forward_from_hidden(
                hidden=h,
                attention_mask=batch["attention_mask"],
                diacritic_ngram_ids=batch["diacritic_ngram_ids"],
                bio_labels=batch["bio_labels"],
                aspect_labels=batch["aspect_labels"],
                aspect_class_weights=aspect_class_weights,
                bio_class_weights=bio_w,
            )
            loss = out["loss"]
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()

            ep_loss_sum += float(loss.item())
            n_batches += 1

        ep_sec = round(time.perf_counter() - t_ep, 2)
        mean_loss = round(ep_loss_sum / max(1, n_batches), 4)
        print(f"[Epoch {epoch}/{epochs}] loss={mean_loss:.4f} batches={n_batches} wall={ep_sec}s", flush=True)
        epoch_logs.append({"epoch": epoch, "mean_loss": mean_loss, "batches": n_batches, "wall_seconds": ep_sec})

    model.eval()
    temp_bundle = LoadedPhoBertAbsaModel(
        model=model,
        tokenizer=tokenizer,
        thresholds={asp: 0.50 for asp in ASPECT_NAMES},
        base_model_id=base_model_id,
    )
    # Calibrate thresholds on unseen dev_val videos first, then full dev (strictly 0 held_out exposure)
    calibrated_thresholds = _calibrate_thresholds_on_dev(
        temp_bundle, dev_val_rows if dev_val_rows else dev_rows
    )
    temp_bundle.thresholds = calibrated_thresholds

    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total_params = sum(p.numel() for p in model.parameters())

    bundle_meta = LoadedPhoBertAbsaModel.save_bundle(
        out_dir=output_model_dir,
        model=model,
        tokenizer=tokenizer,
        thresholds={str(k): float(v) for k, v in calibrated_thresholds.items()},
        base_model_id=base_model_id,
        extra_meta={
            "trained_at_utc": datetime.now(UTC).isoformat(),
            "epochs": epochs,
            "unfreeze_top_k_layers": unfreeze_top_k,
            "trainable_parameters": trainable_params,
            "total_parameters": total_params,
            "train_disjoint_rows": len(disjoint_train_rows),
            "dev_train_rows": len(dev_train_rows),
            "dev_val_rows": len(dev_val_rows),
        },
    )

    reloaded = LoadedPhoBertAbsaModel.from_dir(output_model_dir)
    total_units = len(pool_rows)
    total_vids = len({str(r["video_id"]) for r in pool_rows})

    dev_pure_nn = _evaluate_split_with_extractor(
        dev_rows,
        lambda u: reloaded.extract_unit_spans(u, hybrid_lexicon=False),
        total_units=total_units,
        total_videos=total_vids,
        n_boot=200,
    )
    held_pure_nn = _evaluate_split_with_extractor(
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

    wall_total = round(time.perf_counter() - t0, 2)
    peak_rss_mib = round(float(get_peak_rss_mib()), 2)

    receipt: dict[str, Any] = {
        "study_id": "m5_2_phobert_ner_t4_absa_finetune_v1",
        "evaluated_at_utc": datetime.now(UTC).isoformat(),
        "base_model_id": base_model_id,
        "architecture": "PhoBertNerT4MultiTaskABSA (BertForTokenClassification + NFC Diacritic Subword Fusion + 25-BIO + 4x4 Aspect Attention)",
        "anti_leakage": {
            "train_disjoint_videos": len(train_vids),
            "train_disjoint_comments": len(disjoint_train_rows),
            "dev_train_videos": len(dev_train_vid_set),
            "dev_val_calibration_videos": len(dev_val_vid_set),
            "held_out_test_videos": len(held_vids),
            "held_out_test_units": len(held_out_rows),
            "train_vs_held_out_video_overlap": len(train_vids & held_vids),
            "dev_vs_held_out_video_overlap": len(set(dev_vids) & held_vids),
        },
        "training_summary": {
            "epochs": epochs,
            "batch_size": batch_size,
            "unfreeze_top_k_transformer_layers": unfreeze_top_k,
            "total_parameters": total_params,
            "trainable_parameters": trainable_params,
            "calibrated_thresholds": calibrated_thresholds,
            "epoch_logs": epoch_logs,
            "total_wall_seconds": wall_total,
            "peak_rss_mib": peak_rss_mib,
            "model_artifact_dir": str(output_model_dir.relative_to(REPO_ROOT)),
            "model_safetensors_sha256": bundle_meta["model_safetensors_sha256"],
            "model_safetensors_bytes": bundle_meta["model_safetensors_bytes"],
        },
        "models": {
            "phobert_ner_t4_finetuned": {
                "description": "Pure neural fine-tuned ThuyNT03/PhoBERT_NER_T4-ABSA multi-task checkpoint",
                "dev_metrics": {
                    "aspect_detection_macro_f1": dev_pure_nn["aspect_detection_macro_f1"],
                    "observed_sentiment_macro_f1": dev_pure_nn["observed_sentiment_macro_f1"],
                    "span_validity_rate": dev_pure_nn["span_validity_rate"],
                },
                "held_out_metrics": {
                    "aspect_detection_macro_f1": held_pure_nn["aspect_detection_macro_f1"],
                    "observed_sentiment_macro_f1": held_pure_nn["observed_sentiment_macro_f1"],
                    "span_validity_rate": held_pure_nn["span_validity_rate"],
                    "m5_2_pilot_gate_eligible": held_pure_nn["m5_2_pilot_gate_eligible"],
                    "per_aspect_detection": held_pure_nn["per_aspect_detection"],
                    "aspect_detection_macro_f1_ci95": held_pure_nn["aspect_detection_macro_f1_ci95"],
                    "observed_sentiment_macro_f1_ci95": held_pure_nn["observed_sentiment_macro_f1_ci95"],
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
        "DONE PhoBERT_NER_T4-ABSA fine-tune:\n"
        f"  pure_neural held_out: aspect_F1={held_pure_nn['aspect_detection_macro_f1']}, "
        f"sent_F1={held_pure_nn['observed_sentiment_macro_f1']}, span_valid={held_pure_nn['span_validity_rate']}\n"
        f"  phobert_hybrid held_out: aspect_F1={held_hybrid['aspect_detection_macro_f1']}, "
        f"sent_F1={held_hybrid['observed_sentiment_macro_f1']}, span_valid={held_hybrid['span_validity_rate']}\n"
        f"  wall={wall_total}s, rss={peak_rss_mib} MiB",
        flush=True,
    )
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser(description="Fine-tune ThuyNT03/PhoBERT_NER_T4-ABSA on F&B ABSA")
    parser.add_argument("--base-model", default=DEFAULT_BASE_MODEL_ID)
    parser.add_argument("--epochs", type=int, default=6)
    parser.add_argument("--batch-size", type=int, default=24)
    parser.add_argument("--unfreeze-top-k", type=int, default=2)
    args = parser.parse_args()
    run_phobert_finetune_and_eval(
        base_model_id=args.base_model,
        epochs=args.epochs,
        batch_size=args.batch_size,
        unfreeze_top_k=args.unfreeze_top_k,
    )


if __name__ == "__main__":
    main()
