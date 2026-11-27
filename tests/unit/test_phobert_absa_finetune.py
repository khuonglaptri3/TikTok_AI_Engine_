from __future__ import annotations

import asyncio
import json
import unicodedata
from pathlib import Path

import httpx
import pytest
import torch
from tokenizers import Tokenizer
from tokenizers.models import WordPiece
from tokenizers.pre_tokenizers import Whitespace
from transformers import BertConfig, PreTrainedTokenizerFast

from apps.api.app.main import create_app
from packages.absa.neural_absa import (
    BIO_LABELS,
    LoadedPhoBertAbsaModel,
    PhoBertNerT4MultiTaskABSA,
    align_char_spans_to_bio_ids,
    encode_token_diacritic_hashes,
)
from packages.absa.spans import TextUnitInput
from packages.common.settings import AppSettings


def _build_tiny_fast_tokenizer() -> PreTrainedTokenizerFast:
    vocab = {
        "[PAD]": 0,
        "[UNK]": 1,
        "[CLS]": 2,
        "[SEP]": 3,
        "nuoc": 4,
        "leo": 5,
        "ngon": 6,
        "do": 7,
        "gia": 8,
        "re": 9,
        "mac": 10,
        "quan": 11,
        "sach": 12,
    }
    tok_obj = Tokenizer(WordPiece(vocab=vocab, unk_token="[UNK]"))
    tok_obj.pre_tokenizer = Whitespace()  # type: ignore[assignment]
    return PreTrainedTokenizerFast(
        tokenizer_object=tok_obj,
        unk_token="[UNK]",
        pad_token="[PAD]",
        cls_token="[CLS]",
        sep_token="[SEP]",
    )


def test_bio_label_alignment_and_nfc_diacritic_hash_features() -> None:
    text = unicodedata.normalize("NFC", "nước lèo ngon giá rẻ")
    offsets = [(0, 0), (0, 4), (5, 8), (9, 13), (14, 17), (18, 20), (0, 0)]
    spans = [
        {"aspect": "taste", "polarity_label": "positive", "start_char": 0, "end_char": 13},
        {"aspect": "price", "polarity_label": "positive", "start_char": 14, "end_char": 20},
    ]
    bio_ids = align_char_spans_to_bio_ids(offsets, spans)
    labels = [BIO_LABELS[idx] if idx >= 0 else "IGN" for idx in bio_ids]
    assert labels == [
        "IGN",
        "B-taste-positive",
        "I-taste-positive",
        "I-taste-positive",
        "B-price-positive",
        "I-price-positive",
        "IGN",
    ]

    # Diacritic hash features MUST distinguish Vietnamese 'dở' (bad taste) vs 'dơ' (dirty) vs 'do'
    h_do_taste = encode_token_diacritic_hashes("món này dở", [(8, 10)], num_buckets=2048)
    h_do_hyg = encode_token_diacritic_hashes("bàn ghế dơ", [(8, 10)], num_buckets=2048)
    h_do_plain = encode_token_diacritic_hashes("do trời mưa", [(0, 2)], num_buckets=2048)
    assert not torch.equal(h_do_taste, h_do_hyg)
    assert not torch.equal(h_do_taste, h_do_plain)


def test_phobert_multitask_model_roundtrip_safetensors_and_valid_nfc_spans(
    tmp_path: Path,
) -> None:
    torch.manual_seed(42)
    tokenizer = _build_tiny_fast_tokenizer()
    cfg = BertConfig(
        vocab_size=len(tokenizer),
        hidden_size=64,
        num_hidden_layers=2,
        num_attention_heads=4,
        intermediate_size=128,
        num_labels=5,
    )
    model = PhoBertNerT4MultiTaskABSA.from_fresh_config(
        cfg,
        diacritic_buckets=512,
        diacritic_dim=32,
        fusion_dim=64,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=5e-3)

    sample_text = "nuoc leo ngon gia re"
    enc = tokenizer(
        sample_text,
        return_offsets_mapping=True,
        padding="max_length",
        truncation=True,
        max_length=12,
        return_tensors="pt",
    )
    offsets_list = [(int(a), int(b)) for a, b in enc["offset_mapping"][0].tolist()]
    diac_ids = encode_token_diacritic_hashes(
        sample_text, offsets_list, num_buckets=512, max_ngrams=8
    ).unsqueeze(0)
    bio_targets = torch.tensor(
        [
            align_char_spans_to_bio_ids(
                offsets_list,
                [
                    {"aspect": "taste", "polarity_label": "positive", "start_char": 0, "end_char": 13},
                    {"aspect": "price", "polarity_label": "positive", "start_char": 14, "end_char": 20},
                ],
            )
        ],
        dtype=torch.long,
    )
    # 0=absent_unknown, 1=positive, 2=neutral, 3=negative
    aspect_targets = torch.tensor([[1, 1, 0, 0]], dtype=torch.long)

    model.train()
    out0 = model(
        input_ids=enc["input_ids"],
        attention_mask=enc["attention_mask"],
        diacritic_ngram_ids=diac_ids,
        bio_labels=bio_targets,
        aspect_labels=aspect_targets,
    )
    loss0 = float(out0["loss"].item())
    for _ in range(12):
        optimizer.zero_grad()
        step_out = model(
            input_ids=enc["input_ids"],
            attention_mask=enc["attention_mask"],
            diacritic_ngram_ids=diac_ids,
            bio_labels=bio_targets,
            aspect_labels=aspect_targets,
        )
        step_out["loss"].backward()
        optimizer.step()
    loss_after = float(step_out["loss"].item())
    assert loss_after < loss0

    out_dir = tmp_path / "tiny_phobert_absa"
    LoadedPhoBertAbsaModel.save_bundle(
        out_dir=out_dir,
        model=model,
        tokenizer=tokenizer,
        thresholds={"taste": 0.35, "price": 0.35, "hygiene": 0.4, "service": 0.4},
        base_model_id="ThuyNT03/PhoBERT_NER_T4-ABSA",
    )
    assert (out_dir / "model.safetensors").is_file()

    loaded = LoadedPhoBertAbsaModel.from_dir(out_dir)
    unit = TextUnitInput(
        unit_id="u_test_1",
        source_kind="viewer_comment",
        text=sample_text,
    )
    spans = loaded.extract_unit_spans(unit, hybrid_lexicon=False)
    assert len(spans) >= 1
    for sp in spans:
        assert 0 <= sp.start_char < sp.end_char <= len(sample_text)
        assert sample_text[sp.start_char : sp.end_char] == sp.span_text


def test_trained_phobert_artifact_zero_leakage_and_trust_api_selection() -> None:
    receipt_path = Path("artifacts/benchmarks/m5_2_phobert_absa_eval_v1.json")
    if not receipt_path.is_file():
        pytest.skip("Fine-tuned PhoBERT evaluation receipt not generated yet")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert receipt["base_model_id"] == "ThuyNT03/PhoBERT_NER_T4-ABSA"
    assert receipt["anti_leakage"]["train_vs_held_out_video_overlap"] == 0
    assert receipt["anti_leakage"]["dev_vs_held_out_video_overlap"] == 0
    assert receipt["models"]["phobert_hybrid"]["held_out_metrics"]["span_validity_rate"] >= 0.95

    settings = AppSettings.from_env().model_copy(update={"gemini_api_key": ""})
    app = create_app(settings=settings, mount_demo=False)

    async def _probe() -> None:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            for eng in ("phobert_ner_t4_finetuned", "phobert_hybrid", "lexicon_v1"):
                resp = await client.post(
                    "/api/v1/trust/audit-video",
                    json={
                        "video_id": "v_phobert_api",
                        "caption": "Bún bò Huế giá 40k",
                        "transcript": "Nước lèo đậm đà thơm ngon cực kỳ",
                        "absa_engine": eng,
                        "comments": [
                            {"comment_id": "c1", "author_handle": "u1", "text": "Nước lèo mặn quá trời"},
                            {"comment_id": "c2", "author_handle": "u2", "text": "Thịt bò dai dở tệ"},
                            {"comment_id": "c3", "author_handle": "u3", "text": "Ăn không ngon xíu nào"},
                        ],
                    },
                )
                assert resp.status_code == 200
                body = resp.json()
                assert body["absa_model_used"] == eng

    asyncio.run(_probe())
