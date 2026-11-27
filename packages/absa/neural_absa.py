"""Fine-tuned ThuyNT03/PhoBERT_NER_T4-ABSA multi-task Vietnamese F&B ABSA + NFC span model."""

from __future__ import annotations

import hashlib
import json
import os
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

import torch
import torch.nn as nn
import torch.nn.functional as F
from safetensors.torch import load_file as load_safetensors
from safetensors.torch import save_file as save_safetensors
from transformers import (
    AutoConfig,
    AutoModelForTokenClassification,
    AutoTokenizer,
    BertConfig,
    BertModel,
    PreTrainedTokenizerBase,
)

from packages.absa.spans import TextUnitInput, extract_unit_aspect_spans
from packages.data_contracts.multimodal import (
    ASPECT_NAMES,
    AspectName,
    AspectSpanEvidence,
    ObservedAspectPolarity,
)

AbsaEngineMode = Literal["lexicon_v1", "phobert_ner_t4_finetuned", "phobert_hybrid"]

DEFAULT_BASE_MODEL_ID = "ThuyNT03/PhoBERT_NER_T4-ABSA"
DEFAULT_FINETUNED_DIR = (
    Path(__file__).resolve().parents[2] / "artifacts" / "models" / "phobert-ner-t4-absa-v1"
)

ASPECT_STATE_LABELS: tuple[str, ...] = ("absent_unknown", "positive", "neutral", "negative")
ASPECT_STATE_TO_ID: dict[str, int] = {lbl: idx for idx, lbl in enumerate(ASPECT_STATE_LABELS)}
OBSERVED_POLARITIES: tuple[ObservedAspectPolarity, ...] = ("positive", "neutral", "negative")

BIO_LABELS: tuple[str, ...] = ("O",) + tuple(
    f"{prefix}-{asp}-{pol}"
    for asp in ASPECT_NAMES
    for pol in OBSERVED_POLARITIES
    for prefix in ("B", "I")
)
BIO_LABEL_TO_ID: dict[str, int] = {lbl: idx for idx, lbl in enumerate(BIO_LABELS)}

_WORD_BOUNDARY_RE = re.compile(r"\S+")


def _ensure_ssl_bundle() -> None:
    ca_path = Path("/etc/ssl/certs/ca-certificates.crt")
    if ca_path.is_file():
        os.environ.setdefault("SSL_CERT_FILE", str(ca_path))
        os.environ.setdefault("REQUESTS_CA_BUNDLE", str(ca_path))


def _hash_ngram_bucket(ngram: str, num_buckets: int) -> int:
    """Deterministic 1..num_buckets-1 bucket index (0 reserved for padding)."""
    digest = hashlib.blake2b(ngram.encode("utf-8"), digest_size=4).digest()
    val = int.from_bytes(digest, "little")
    return 1 + (val % max(1, num_buckets - 1))


def _expand_to_full_word(text: str, s: int, e: int) -> str:
    n = len(text)
    ws = max(0, min(s, n))
    we = max(ws, min(e, n))
    while ws > 0 and not text[ws - 1].isspace():
        ws -= 1
    while we < n and not text[we].isspace():
        we += 1
    return text[ws:we]


def encode_token_diacritic_hashes(
    text: str,
    offsets: Sequence[tuple[int, int]],
    *,
    num_buckets: int = 8192,
    max_ngrams: int = 12,
) -> torch.Tensor:
    """Encode accented Vietnamese NFC character n-grams per token offset slice.

    Restores full Vietnamese tone/vowel distinguishability ('dở' vs 'dơ' vs 'do',
    'rẻ' vs 'rẽ', 'mặn' vs 'mận') when paired with WordPiece backbones.
    """
    nfc = unicodedata.normalize("NFC", text or "").lower()
    out = torch.zeros((len(offsets), max_ngrams), dtype=torch.long)
    for idx, (s, e) in enumerate(offsets):
        if e <= s or s < 0 or e > len(nfc):
            continue
        tok_slice = nfc[s:e].strip()
        full_word = _expand_to_full_word(nfc, s, e).strip(".,!?;:\"'()[]{}…")
        if not tok_slice and not full_word:
            continue
        feats: list[str] = []
        if tok_slice:
            feats.append(f"t:{tok_slice}")
        if full_word:
            padded = f"<{full_word}>"
            feats.append(f"w:{padded}")
            for k in (2, 3, 4):
                for j in range(max(0, len(padded) - k + 1)):
                    feats.append(padded[j : j + k])
                    if len(feats) >= max_ngrams:
                        break
                if len(feats) >= max_ngrams:
                    break
        for j, fg in enumerate(feats[:max_ngrams]):
            out[idx, j] = _hash_ngram_bucket(fg, num_buckets)
    return out


def align_char_spans_to_bio_ids(
    offsets: Sequence[tuple[int, int]],
    spans: Sequence[Mapping[str, Any]],
) -> list[int]:
    """Map NFC character-offset spans onto token BIO indices (-100 for special/pad tokens)."""
    labels: list[int] = []
    for s_tok, e_tok in offsets:
        if e_tok <= s_tok:
            labels.append(-100)
        else:
            labels.append(0)  # 'O'

    for sp in spans:
        aspect = str(sp.get("aspect") or "").strip()
        pol = str(sp.get("polarity_label") or "").strip()
        if aspect not in ASPECT_NAMES or pol not in OBSERVED_POLARITIES:
            continue
        sp_s = int(sp.get("start_char", 0))
        sp_e = int(sp.get("end_char", 0))
        if sp_e <= sp_s:
            continue
        b_id = BIO_LABEL_TO_ID[f"B-{aspect}-{pol}"]
        i_id = BIO_LABEL_TO_ID[f"I-{aspect}-{pol}"]
        started = False
        for idx, (s_tok, e_tok) in enumerate(offsets):
            if e_tok <= s_tok:
                continue
            overlap = min(e_tok, sp_e) - max(s_tok, sp_s)
            if overlap > 0:
                labels[idx] = b_id if not started else i_id
                started = True
    return labels


class PhoBertNerT4MultiTaskABSA(nn.Module):
    """Multi-task ABSA initialized from ThuyNT03/PhoBERT_NER_T4-ABSA.

    Combines:
      1. Pretrained Transformer encoder + 5-class NER-T4 Aspect/Opinion head from
         ThuyNT03/PhoBERT_NER_T4-ABSA
      2. Accented Vietnamese NFC character n-gram token embeddings
      3. 25-class unified T4-ABSA BIO sequence tagger (exact span extraction)
      4. 4-aspect query-attention pooling + 4-state aspect sentiment classifiers
    """

    def __init__(
        self,
        *,
        backbone: BertModel,
        pretrained_ner_head: nn.Linear,
        diacritic_buckets: int = 8192,
        diacritic_dim: int = 192,
        fusion_dim: int = 384,
        dropout_prob: float = 0.15,
    ) -> None:
        super().__init__()
        self.backbone = backbone
        self.pretrained_ner_head = pretrained_ner_head
        self.diacritic_buckets = diacritic_buckets
        self.diacritic_dim = diacritic_dim
        self.fusion_dim = fusion_dim

        self.diacritic_emb = nn.Embedding(diacritic_buckets, diacritic_dim, padding_idx=0)
        hidden_size = int(backbone.config.hidden_size)
        ner_dim = int(pretrained_ner_head.out_features)

        self.fusion_proj = nn.Sequential(
            nn.Linear(hidden_size + ner_dim + diacritic_dim, fusion_dim),
            nn.LayerNorm(fusion_dim),
            nn.GELU(),
            nn.Dropout(dropout_prob),
        )
        self.bio_classifier = nn.Linear(fusion_dim, len(BIO_LABELS))
        self.aspect_queries = nn.Parameter(torch.randn(len(ASPECT_NAMES), fusion_dim) * 0.02)
        self.aspect_classifiers = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Linear(fusion_dim * 2, fusion_dim // 2),
                    nn.GELU(),
                    nn.Dropout(dropout_prob),
                    nn.Linear(fusion_dim // 2, len(ASPECT_STATE_LABELS)),
                )
                for _ in ASPECT_NAMES
            ]
        )

    @classmethod
    def from_pretrained_ner_t4(
        cls,
        model_id_or_path: str = DEFAULT_BASE_MODEL_ID,
        *,
        diacritic_buckets: int = 8192,
        diacritic_dim: int = 192,
        fusion_dim: int = 384,
        dropout_prob: float = 0.15,
    ) -> PhoBertNerT4MultiTaskABSA:
        _ensure_ssl_bundle()
        base_tc = AutoModelForTokenClassification.from_pretrained(model_id_or_path)
        backbone: BertModel = base_tc.bert
        backbone.pooler = None
        ner_head = nn.Linear(base_tc.classifier.in_features, base_tc.classifier.out_features)
        with torch.no_grad():
            ner_head.weight.copy_(base_tc.classifier.weight)
            ner_head.bias.copy_(base_tc.classifier.bias)
        return cls(
            backbone=backbone,
            pretrained_ner_head=ner_head,
            diacritic_buckets=diacritic_buckets,
            diacritic_dim=diacritic_dim,
            fusion_dim=fusion_dim,
            dropout_prob=dropout_prob,
        )

    @classmethod
    def from_fresh_config(
        cls,
        bert_config: BertConfig,
        *,
        ner_num_labels: int = 5,
        diacritic_buckets: int = 8192,
        diacritic_dim: int = 192,
        fusion_dim: int = 384,
        dropout_prob: float = 0.15,
    ) -> PhoBertNerT4MultiTaskABSA:
        backbone = BertModel(bert_config, add_pooling_layer=False)
        ner_head = nn.Linear(int(bert_config.hidden_size), ner_num_labels)
        return cls(
            backbone=backbone,
            pretrained_ner_head=ner_head,
            diacritic_buckets=diacritic_buckets,
            diacritic_dim=diacritic_dim,
            fusion_dim=fusion_dim,
            dropout_prob=dropout_prob,
        )

    def freeze_lower_transformer_layers(self, unfreeze_top_k: int = 3) -> None:
        for param in self.backbone.embeddings.parameters():
            param.requires_grad = False
        layers = list(self.backbone.encoder.layer)
        cutoff = max(0, len(layers) - max(0, unfreeze_top_k))
        for idx, layer in enumerate(layers):
            req = idx >= cutoff
            for param in layer.parameters():
                param.requires_grad = req

    def forward_from_hidden(
        self,
        *,
        hidden: torch.Tensor,
        attention_mask: torch.Tensor,
        diacritic_ngram_ids: torch.Tensor,
        bio_labels: torch.Tensor | None = None,
        aspect_labels: torch.Tensor | None = None,
        aspect_class_weights: torch.Tensor | None = None,
        bio_class_weights: torch.Tensor | None = None,
    ) -> dict[str, Any]:
        ner_logits = self.pretrained_ner_head(hidden)  # [B, L, 5]

        emb = self.diacritic_emb(diacritic_ngram_ids)  # [B, L, G, D]
        non_pad = (diacritic_ngram_ids != 0).unsqueeze(-1).to(emb.dtype)
        denom = non_pad.sum(dim=2).clamp(min=1.0)
        diac_vec = (emb * non_pad).sum(dim=2) / denom  # [B, L, D]

        fused = self.fusion_proj(torch.cat([hidden, ner_logits, diac_vec], dim=-1))  # [B, L, F]
        bio_logits = self.bio_classifier(fused)  # [B, L, 25]

        tok_mask = attention_mask.bool()
        scale = float(self.fusion_dim) ** -0.5
        attn_scores = torch.einsum("af,blf->bal", self.aspect_queries, fused) * scale
        attn_scores = attn_scores.masked_fill(~tok_mask.unsqueeze(1), -1e4)
        attn_weights = torch.softmax(attn_scores, dim=-1)  # [B, 4, L]
        attn_pooled = torch.einsum("bal,blf->baf", attn_weights, fused)  # [B, 4, F]

        masked_fused = fused.masked_fill(~tok_mask.unsqueeze(-1), -1e4)
        max_pooled = masked_fused.max(dim=1).values  # [B, F]

        per_aspect_logits: list[torch.Tensor] = []
        for idx, head in enumerate(self.aspect_classifiers):
            combined = torch.cat([attn_pooled[:, idx, :], max_pooled], dim=-1)
            per_aspect_logits.append(head(combined))
        aspect_logits = torch.stack(per_aspect_logits, dim=1)  # [B, 4, 4]

        result: dict[str, Any] = {
            "bio_logits": bio_logits,
            "aspect_logits": aspect_logits,
            "attn_weights": attn_weights,
            "pretrained_ner_logits": ner_logits,
        }

        if bio_labels is not None and aspect_labels is not None:
            bio_loss = F.cross_entropy(
                bio_logits.view(-1, bio_logits.size(-1)),
                bio_labels.view(-1),
                weight=bio_class_weights,
                ignore_index=-100,
            )
            asp_loss_total = torch.tensor(0.0, device=hidden.device)
            for idx in range(len(ASPECT_NAMES)):
                w_idx = aspect_class_weights[idx] if aspect_class_weights is not None else None
                asp_loss_total = asp_loss_total + F.cross_entropy(
                    aspect_logits[:, idx, :],
                    aspect_labels[:, idx],
                    weight=w_idx,
                )
            asp_loss = asp_loss_total / float(len(ASPECT_NAMES))
            result["bio_loss"] = bio_loss
            result["aspect_loss"] = asp_loss
            result["loss"] = 0.45 * bio_loss + 0.55 * asp_loss

        return result

    def forward(
        self,
        *,
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        diacritic_ngram_ids: torch.Tensor,
        bio_labels: torch.Tensor | None = None,
        aspect_labels: torch.Tensor | None = None,
        aspect_class_weights: torch.Tensor | None = None,
        bio_class_weights: torch.Tensor | None = None,
    ) -> dict[str, Any]:
        bert_out = self.backbone(input_ids=input_ids, attention_mask=attention_mask)
        return self.forward_from_hidden(
            hidden=bert_out.last_hidden_state,
            attention_mask=attention_mask,
            diacritic_ngram_ids=diacritic_ngram_ids,
            bio_labels=bio_labels,
            aspect_labels=aspect_labels,
            aspect_class_weights=aspect_class_weights,
            bio_class_weights=bio_class_weights,
        )


def _snap_char_range_to_words(text: str, s: int, e: int) -> tuple[int, int]:
    n = len(text)
    s_clamped = max(0, min(s, n))
    e_clamped = max(s_clamped, min(e, n))
    while s_clamped > 0 and not text[s_clamped - 1].isspace():
        s_clamped -= 1
    while e_clamped < n and not text[e_clamped].isspace():
        e_clamped += 1
    while s_clamped < e_clamped and text[s_clamped].isspace():
        s_clamped += 1
    while e_clamped > s_clamped and text[e_clamped - 1].isspace():
        e_clamped -= 1
    return s_clamped, e_clamped


def _window_around_token_offset(
    text: str,
    offsets: Sequence[tuple[int, int]],
    peak_tok_idx: int,
    *,
    radius_words: int = 2,
) -> tuple[int, int]:
    words = [(m.start(), m.end()) for m in _WORD_BOUNDARY_RE.finditer(text)]
    if not words:
        return (0, len(text))
    if 0 <= peak_tok_idx < len(offsets) and offsets[peak_tok_idx][1] > offsets[peak_tok_idx][0]:
        ts, te = offsets[peak_tok_idx]
        center_w = 0
        for w_i, (ws, we) in enumerate(words):
            if min(te, we) > max(ts, ws):
                center_w = w_i
                break
    else:
        center_w = len(words) // 2
    lo = max(0, center_w - radius_words)
    hi = min(len(words) - 1, center_w + radius_words)
    return _snap_char_range_to_words(text, words[lo][0], words[hi][1])


@dataclass
class LoadedPhoBertAbsaModel:
    model: PhoBertNerT4MultiTaskABSA
    tokenizer: PreTrainedTokenizerBase
    thresholds: dict[AspectName, float]
    base_model_id: str
    max_length: int = 96
    max_ngrams: int = 12

    @classmethod
    def save_bundle(
        cls,
        *,
        out_dir: Path,
        model: PhoBertNerT4MultiTaskABSA,
        tokenizer: PreTrainedTokenizerBase,
        thresholds: Mapping[str, float],
        base_model_id: str = DEFAULT_BASE_MODEL_ID,
        max_length: int = 96,
        max_ngrams: int = 12,
        extra_meta: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        out_dir.mkdir(parents=True, exist_ok=True)
        tokenizer.save_pretrained(str(out_dir))
        model.backbone.config.save_pretrained(str(out_dir))
        state = {k: v.detach().cpu().contiguous() for k, v in model.state_dict().items()}
        weights_path = out_dir / "model.safetensors"
        save_safetensors(state, str(weights_path))
        digest = hashlib.sha256(weights_path.read_bytes()).hexdigest()

        meta: dict[str, Any] = {
            "base_model_id": base_model_id,
            "architecture": "PhoBertNerT4MultiTaskABSA",
            "ner_num_labels": int(model.pretrained_ner_head.out_features),
            "diacritic_buckets": model.diacritic_buckets,
            "diacritic_dim": model.diacritic_dim,
            "fusion_dim": model.fusion_dim,
            "max_length": max_length,
            "max_ngrams": max_ngrams,
            "thresholds": {str(k): float(v) for k, v in thresholds.items()},
            "model_safetensors_sha256": digest,
            "model_safetensors_bytes": weights_path.stat().st_size,
        }
        if extra_meta:
            meta.update(dict(extra_meta))
        (out_dir / "absa_model_meta.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return meta

    @classmethod
    def from_dir(cls, model_dir: Path) -> LoadedPhoBertAbsaModel:
        meta_path = model_dir / "absa_model_meta.json"
        weights_path = model_dir / "model.safetensors"
        if not (meta_path.is_file() and weights_path.is_file()):
            raise FileNotFoundError(
                f"Fine-tuned PhoBERT ABSA bundle missing at {model_dir}; run python -m pipelines.train_absa_phobert"
            )
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        bert_cfg = AutoConfig.from_pretrained(str(model_dir))
        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        model = PhoBertNerT4MultiTaskABSA.from_fresh_config(
            bert_cfg,
            ner_num_labels=int(meta.get("ner_num_labels", 5)),
            diacritic_buckets=int(meta.get("diacritic_buckets", 8192)),
            diacritic_dim=int(meta.get("diacritic_dim", 192)),
            fusion_dim=int(meta.get("fusion_dim", 384)),
        )
        raw_state = load_safetensors(str(weights_path))
        expected_keys = set(model.state_dict().keys())
        optional_buffers = {
            "backbone.embeddings.position_ids",
            "backbone.embeddings.token_type_ids",
            "backbone.pooler.dense.weight",
            "backbone.pooler.dense.bias",
        }
        filtered_state = {
            k: v
            for k, v in raw_state.items()
            if (k in expected_keys or k not in optional_buffers)
        }
        for opt_k in optional_buffers & expected_keys:
            if opt_k not in filtered_state:
                filtered_state[opt_k] = model.state_dict()[opt_k]
        model.load_state_dict(filtered_state, strict=True)
        model.eval()

        raw_thresh = meta.get("thresholds") or {}
        thresholds: dict[AspectName, float] = {
            asp: float(raw_thresh.get(asp, 0.45)) for asp in ASPECT_NAMES
        }
        return cls(
            model=model,
            tokenizer=tokenizer,
            thresholds=thresholds,
            base_model_id=str(meta.get("base_model_id") or DEFAULT_BASE_MODEL_ID),
            max_length=int(meta.get("max_length", 96)),
            max_ngrams=int(meta.get("max_ngrams", 12)),
        )

    def predict_unit_raw(self, text: str) -> dict[str, Any]:
        nfc = unicodedata.normalize("NFC", text or "")
        if not nfc.strip():
            return {"nfc_text": nfc, "aspects": {}, "bio_spans": {}}
        enc = self.tokenizer(
            nfc,
            return_offsets_mapping=True,
            truncation=True,
            max_length=self.max_length,
            return_tensors="pt",
        )
        offsets = [(int(a), int(b)) for a, b in enc["offset_mapping"][0].tolist()]
        diac_ids = encode_token_diacritic_hashes(
            nfc,
            offsets,
            num_buckets=self.model.diacritic_buckets,
            max_ngrams=self.max_ngrams,
        ).unsqueeze(0)
        with torch.inference_mode():
            out = self.model(
                input_ids=enc["input_ids"],
                attention_mask=enc["attention_mask"],
                diacritic_ngram_ids=diac_ids,
            )
            asp_probs = torch.softmax(out["aspect_logits"][0], dim=-1).cpu().tolist()
            bio_pred_ids = out["bio_logits"][0].argmax(dim=-1).cpu().tolist()
            attn_w = out["attn_weights"][0].cpu().tolist()

        # Decode contiguous BIO spans per aspect
        bio_spans: dict[AspectName, list[tuple[int, int, ObservedAspectPolarity]]] = {
            asp: [] for asp in ASPECT_NAMES
        }
        cur_asp: AspectName | None = None
        cur_pol: ObservedAspectPolarity | None = None
        cur_s = -1
        cur_e = -1
        for tok_idx, lbl_id in enumerate(bio_pred_ids):
            s_tok, e_tok = offsets[tok_idx]
            if e_tok <= s_tok or lbl_id <= 0:
                if cur_asp is not None and cur_pol is not None and cur_e > cur_s:
                    bio_spans[cur_asp].append((cur_s, cur_e, cur_pol))
                cur_asp, cur_pol, cur_s, cur_e = None, None, -1, -1
                continue
            tag = BIO_LABELS[lbl_id]
            prefix, asp_raw, pol_raw = tag.split("-", 2)
            asp_t: AspectName = asp_raw  # type: ignore[assignment]
            pol_t: ObservedAspectPolarity = pol_raw  # type: ignore[assignment]
            if prefix == "B" or cur_asp != asp_t:
                if cur_asp is not None and cur_pol is not None and cur_e > cur_s:
                    bio_spans[cur_asp].append((cur_s, cur_e, cur_pol))
                cur_asp, cur_pol, cur_s, cur_e = asp_t, pol_t, s_tok, e_tok
            else:
                cur_e = max(cur_e, e_tok)
        if cur_asp is not None and cur_pol is not None and cur_e > cur_s:
            bio_spans[cur_asp].append((cur_s, cur_e, cur_pol))

        aspects_info: dict[AspectName, dict[str, Any]] = {}
        for idx, asp in enumerate(ASPECT_NAMES):
            probs = asp_probs[idx]
            p_abs = float(probs[0])
            p_pos, p_neu, p_neg = float(probs[1]), float(probs[2]), float(probs[3])
            p_observed = 1.0 - p_abs
            best_obs_idx = max((1, 2, 3), key=lambda k: float(probs[k]))
            best_pol: ObservedAspectPolarity = ASPECT_STATE_LABELS[best_obs_idx]  # type: ignore[assignment]
            polarity_score = round(
                max(-1.0, min(1.0, (p_pos - p_neg) / max(1e-6, p_pos + p_neu + p_neg))),
                4,
            )
            if best_pol == "positive" and polarity_score <= 0.0:
                polarity_score = round(max(0.25, p_pos), 4)
            elif best_pol == "negative" and polarity_score >= 0.0:
                polarity_score = round(-max(0.25, p_neg), 4)
            elif best_pol == "neutral":
                polarity_score = 0.0

            # Pick peak content token index (skipping CLS/SEP where s==e)
            valid_tok_indices = [i for i, (s, e) in enumerate(offsets) if e > s]
            peak_tok = (
                max(valid_tok_indices, key=lambda i: float(attn_w[idx][i]))
                if valid_tok_indices
                else 0
            )
            aspects_info[asp] = {
                "p_observed": round(p_observed, 4),
                "probs": {
                    "absent_unknown": round(p_abs, 4),
                    "positive": round(p_pos, 4),
                    "neutral": round(p_neu, 4),
                    "negative": round(p_neg, 4),
                },
                "best_polarity": best_pol,
                "polarity_score": polarity_score,
                "peak_tok_idx": peak_tok,
            }

        return {
            "nfc_text": nfc,
            "offsets": offsets,
            "aspects": aspects_info,
            "bio_spans": bio_spans,
        }

    def extract_unit_spans(
        self,
        unit: TextUnitInput,
        *,
        hybrid_lexicon: bool = False,
        polarity_tau: float = 0.15,
    ) -> list[AspectSpanEvidence]:
        raw = self.predict_unit_raw(unit.text)
        nfc: str = raw["nfc_text"]
        if not nfc.strip():
            return []
        offsets: list[tuple[int, int]] = raw["offsets"]
        lex_spans = (
            extract_unit_aspect_spans(unit, polarity_tau=polarity_tau) if hybrid_lexicon else []
        )
        lex_by_aspect: dict[AspectName, list[AspectSpanEvidence]] = {asp: [] for asp in ASPECT_NAMES}
        for sp in lex_spans:
            lex_by_aspect[sp.aspect].append(sp)

        emitted: list[AspectSpanEvidence] = []
        for asp in ASPECT_NAMES:
            info = raw["aspects"].get(asp)
            if info is None:
                continue
            thresh = self.thresholds.get(asp, 0.45)
            p_obs = float(info["p_observed"])
            has_lex = len(lex_by_aspect[asp]) > 0

            if hybrid_lexicon:
                # Ensemble: accept high-confidence neural detections OR lexicon anchors confirmed/uncontradicted
                detected = (p_obs >= max(0.68, thresh + 0.14)) or (
                    has_lex and p_obs >= min(0.18, thresh * 0.45)
                ) or has_lex
            else:
                detected = p_obs >= thresh

            if not detected:
                continue

            if hybrid_lexicon and has_lex:
                # Refine polarity using neural classifier when neural confidence is decisive, keeping exact span anchor
                base_sp = lex_by_aspect[asp][0]
                if p_obs >= max(0.62, thresh + 0.10):
                    pol_label: ObservedAspectPolarity = info["best_polarity"]
                    pol_score = float(info["polarity_score"])
                else:
                    pol_label = base_sp.polarity_label
                    pol_score = base_sp.polarity_score
                emitted.append(
                    AspectSpanEvidence(
                        unit_id=unit.unit_id,
                        source_kind=unit.source_kind,
                        aspect=asp,
                        polarity_label=pol_label,
                        polarity_score=pol_score,
                        start_char=base_sp.start_char,
                        end_char=base_sp.end_char,
                        span_text=base_sp.span_text,
                    )
                )
                continue

            pol_label = info["best_polarity"]
            pol_score = float(info["polarity_score"])
            b_spans = raw["bio_spans"].get(asp) or []
            if b_spans:
                bs, be, _ = b_spans[0]
                s_char, e_char = _snap_char_range_to_words(nfc, bs, be)
            else:
                s_char, e_char = _window_around_token_offset(
                    nfc, offsets, int(info["peak_tok_idx"]), radius_words=2
                )
            span_txt = nfc[s_char:e_char]
            if not span_txt.strip():
                s_char, e_char = _snap_char_range_to_words(nfc, 0, len(nfc))
                span_txt = nfc[s_char:e_char]
            if e_char > s_char and span_txt.strip():
                emitted.append(
                    AspectSpanEvidence(
                        unit_id=unit.unit_id,
                        source_kind=unit.source_kind,
                        aspect=asp,
                        polarity_label=pol_label,
                        polarity_score=pol_score,
                        start_char=s_char,
                        end_char=e_char,
                        span_text=span_txt,
                    )
                )
        return emitted


@lru_cache(maxsize=2)
def get_phobert_absa_model(model_dir_str: str | None = None) -> LoadedPhoBertAbsaModel:
    target = Path(model_dir_str) if model_dir_str else DEFAULT_FINETUNED_DIR
    return LoadedPhoBertAbsaModel.from_dir(target)


def is_phobert_absa_available(model_dir: Path | None = None) -> bool:
    target = model_dir or DEFAULT_FINETUNED_DIR
    return (target / "model.safetensors").is_file() and (target / "absa_model_meta.json").is_file()
