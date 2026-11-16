from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from packages.common.exceptions import IndexNotReadyError

WORD_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)

VN_STOPWORDS: frozenset[str] = frozenset(
    {
        "và",
        "của",
        "là",
        "có",
        "thì",
        "mà",
        "cho",
        "với",
        "này",
        "đó",
        "các",
        "những",
        "một",
        "nhưng",
        "nha",
        "nhé",
        "luôn",
        "rất",
        "cũng",
        "được",
        "trong",
        "trên",
        "khi",
        "để",
        "từ",
        "vào",
        "ra",
        "lại",
        "nên",
        "rồi",
        "ơi",
        "ạ",
        "á",
    }
)


def tokenize_vietnamese(text: str, include_bigrams: bool = True) -> list[str]:
    """NFC-normalized Vietnamese word + adjacent bigram tokenizer preserving diacritics."""
    if not text:
        return []
    nfc = unicodedata.normalize("NFC", text).lower()
    raw_words = [w for w in WORD_RE.findall(nfc) if len(w) >= 2 or w.isdigit()]
    unigrams = [w for w in raw_words if w not in VN_STOPWORDS]
    if not include_bigrams or len(raw_words) < 2:
        return unigrams
    # Build adjacent bigrams over raw_words (preserves phrases like "ăn đêm", "quận 1", "bún bò")
    bigrams = [f"{raw_words[i]}_{raw_words[i + 1]}" for i in range(len(raw_words) - 1)]
    return unigrams + bigrams


class BM25Index:
    """Pickle-free CSR inverted index implementing Okapi BM25 over Vietnamese transcripts."""

    def __init__(
        self,
        video_ids: list[str],
        vocab: dict[str, int],
        idf: np.ndarray,
        indptr: np.ndarray,
        indices: np.ndarray,
        tf_data: np.ndarray,
        doc_len: np.ndarray,
        avgdl: float,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> None:
        self.video_ids = video_ids
        self.vid_to_idx = {vid: idx for idx, vid in enumerate(video_ids)}
        self.vocab = vocab
        self.idf = idf
        self.indptr = indptr
        self.indices = indices
        self.tf_data = tf_data
        self.doc_len = doc_len
        self.avgdl = max(avgdl, 1.0)
        self.k1 = k1
        self.b = b

    @classmethod
    def build(
        cls,
        video_ids: list[str],
        documents: list[str],
        min_bigram_df: int = 2,
        k1: float = 1.5,
        b: float = 0.75,
    ) -> BM25Index:
        n_docs = len(video_ids)
        if n_docs == 0 or n_docs != len(documents):
            raise ValueError("video_ids and documents must be non-empty and equal length")

        doc_counters: list[Counter[str]] = []
        df_counter: Counter[str] = Counter()
        doc_lens = np.zeros(n_docs, dtype=np.float32)

        for idx, doc in enumerate(documents):
            tokens = tokenize_vietnamese(doc, include_bigrams=True)
            unigram_len = sum(1 for t in tokens if "_" not in t)
            doc_lens[idx] = float(max(unigram_len, 1))
            counts = Counter(tokens)
            doc_counters.append(counts)
            for term in counts:
                df_counter[term] += 1

        # Prune ultra-rare 1-off bigrams to keep CSR matrix tiny & fast
        valid_terms = sorted(
            term for term, df in df_counter.items() if ("_" not in term) or (df >= min_bigram_df)
        )
        vocab = {term: tid for tid, term in enumerate(valid_terms)}
        n_terms = len(vocab)

        postings_docs: list[list[int]] = [[] for _ in range(n_terms)]
        postings_tfs: list[list[float]] = [[] for _ in range(n_terms)]

        for doc_idx, counts in enumerate(doc_counters):
            for term, tf in counts.items():
                tid = vocab.get(term)
                if tid is not None:
                    postings_docs[tid].append(doc_idx)
                    postings_tfs[tid].append(float(tf))

        idf = np.zeros(n_terms, dtype=np.float32)
        indptr = np.zeros(n_terms + 1, dtype=np.int64)
        flat_indices: list[int] = []
        flat_tfs: list[float] = []

        cursor = 0
        for tid in range(n_terms):
            df = len(postings_docs[tid])
            idf[tid] = float(math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5)))
            flat_indices.extend(postings_docs[tid])
            flat_tfs.extend(postings_tfs[tid])
            cursor += df
            indptr[tid + 1] = cursor

        return cls(
            video_ids=list(video_ids),
            vocab=vocab,
            idf=idf,
            indptr=indptr,
            indices=np.asarray(flat_indices, dtype=np.int32),
            tf_data=np.asarray(flat_tfs, dtype=np.float32),
            doc_len=doc_lens,
            avgdl=float(doc_lens.mean()),
            k1=k1,
            b=b,
        )

    def save(self, index_dir: Path, corpus_snapshot_id: str = "20261116_v1") -> dict[str, object]:
        index_dir.mkdir(parents=True, exist_ok=True)
        (index_dir / "video_ids.json").write_text(
            json.dumps(self.video_ids, ensure_ascii=False), encoding="utf-8"
        )
        (index_dir / "vocab.json").write_text(
            json.dumps(self.vocab, ensure_ascii=False), encoding="utf-8"
        )
        np.savez_compressed(
            index_dir / "bm25_csr.npz",
            idf=self.idf,
            indptr=self.indptr,
            indices=self.indices,
            tf_data=self.tf_data,
            doc_len=self.doc_len,
            meta=np.asarray([self.avgdl, self.k1, self.b], dtype=np.float64),
        )
        receipt: dict[str, object] = {
            "index_type": "okapi_bm25_vn_nfc_csr",
            "corpus_snapshot_id": corpus_snapshot_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "document_count": len(self.video_ids),
            "vocab_size": len(self.vocab),
            "postings_count": int(len(self.indices)),
            "avgdl": round(self.avgdl, 2),
            "k1": self.k1,
            "b": self.b,
        }
        (index_dir / "bm25-receipt.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        return receipt

    @classmethod
    def load(cls, index_dir: Path) -> BM25Index:
        npz_path = index_dir / "bm25_csr.npz"
        vocab_path = index_dir / "vocab.json"
        vids_path = index_dir / "video_ids.json"
        if not (npz_path.is_file() and vocab_path.is_file() and vids_path.is_file()):
            raise IndexNotReadyError(f"BM25 index artifacts missing in {index_dir}")

        video_ids: list[str] = json.loads(vids_path.read_text(encoding="utf-8"))
        vocab: dict[str, int] = json.loads(vocab_path.read_text(encoding="utf-8"))
        with np.load(npz_path, allow_pickle=False) as arrays:
            meta = arrays["meta"]
            return cls(
                video_ids=video_ids,
                vocab=vocab,
                idf=arrays["idf"],
                indptr=arrays["indptr"],
                indices=arrays["indices"],
                tf_data=arrays["tf_data"],
                doc_len=arrays["doc_len"],
                avgdl=float(meta[0]),
                k1=float(meta[1]),
                b=float(meta[2]),
            )

    def search(
        self,
        query: str,
        top_k: int = 50,
        allowed_video_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        q_tokens = tokenize_vietnamese(query, include_bigrams=True)
        if not q_tokens:
            return []

        n_docs = len(self.video_ids)
        scores = np.zeros(n_docs, dtype=np.float32)
        q_counts = Counter(q_tokens)

        for term, q_weight in q_counts.items():
            tid = self.vocab.get(term)
            if tid is None:
                continue
            start = int(self.indptr[tid])
            end = int(self.indptr[tid + 1])
            if start >= end:
                continue

            doc_idxs = self.indices[start:end]
            tfs = self.tf_data[start:end]
            dl = self.doc_len[doc_idxs]
            denom = tfs + self.k1 * (1.0 - self.b + self.b * (dl / self.avgdl))
            term_boost = 1.35 if "_" in term else 1.0
            contrib = (
                self.idf[tid]
                * ((tfs * (self.k1 + 1.0)) / denom)
                * term_boost
                * min(float(q_weight), 2.0)
            )
            scores[doc_idxs] += contrib

        if allowed_video_ids is not None:
            allowed_idxs = [self.vid_to_idx[vid] for vid in allowed_video_ids if vid in self.vid_to_idx]
            if not allowed_idxs:
                return []
            mask = np.zeros(n_docs, dtype=bool)
            mask[allowed_idxs] = True
            scores = np.where(mask, scores, 0.0)

        nonzero_idxs = np.flatnonzero(scores > 0.0)
        if len(nonzero_idxs) == 0:
            return []

        if len(nonzero_idxs) > top_k:
            sub_scores = scores[nonzero_idxs]
            top_rel = np.argpartition(-sub_scores, top_k - 1)[:top_k]
            cand_idxs = nonzero_idxs[top_rel]
        else:
            cand_idxs = nonzero_idxs

        ordered = cand_idxs[np.argsort(-scores[cand_idxs])]
        return [(self.video_ids[int(i)], round(float(scores[int(i)]), 4)) for i in ordered[:top_k]]
