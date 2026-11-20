"""CPU-feasible dense text encoders for Vietnamese F&B retrieval (M6.1)."""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

import numpy as np
from scipy.sparse import csr_matrix
from scipy.sparse.linalg import svds

from packages.common.exceptions import IndexNotReadyError

WORD_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)


def _dense_tokens(text: str) -> list[str]:
    """Extract normalized unigrams, bigrams, and compact subword 3-grams."""
    nfc = unicodedata.normalize("NFC", text).lower()
    words = WORD_RE.findall(nfc)
    tokens = list(words)
    if len(words) > 1:
        tokens.extend(f"{words[i]}_{words[i + 1]}" for i in range(len(words) - 1))
    for w in words:
        if len(w) >= 3:
            tokens.extend(f"#{w[i:i + 3]}" for i in range(len(w) - 2))
    return tokens


def _l2_normalize_rows(mat: np.ndarray) -> np.ndarray:
    arr = np.asarray(mat, dtype=np.float32)
    if arr.ndim == 1:
        norm = float(np.linalg.norm(arr))
        return arr / norm if norm > 1e-12 else arr
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    safe_norms = np.where(norms > 1e-12, norms, 1.0)
    res: np.ndarray = np.asarray(arr / safe_norms, dtype=np.float32)
    return res


@runtime_checkable
class DenseTextEncoder(Protocol):
    model_id: str
    dimension: int

    def encode_documents(self, texts: list[str]) -> np.ndarray: ...

    def encode_query(self, query: str) -> list[float]: ...


class TruncatedSvdDenseEncoder:
    """Zero-dependency CPU LSA/SVD dense encoder over Vietnamese NFC TF-IDF n-grams."""

    def __init__(
        self,
        vocab: dict[str, int],
        idf: np.ndarray,
        components: np.ndarray,
        model_id: str = "tfidf_svd_vn_v1",
    ) -> None:
        self.vocab = vocab
        self.idf = np.asarray(idf, dtype=np.float32)
        self.components = np.asarray(components, dtype=np.float32)
        self.model_id = model_id
        self.dimension = int(self.components.shape[0])

    @classmethod
    def fit(
        cls,
        documents: list[str],
        dimension: int = 128,
        max_vocab: int = 25000,
        min_df: int | None = None,
    ) -> TruncatedSvdDenseEncoder:
        n_docs = len(documents)
        if n_docs < 2:
            raise ValueError("TruncatedSvdDenseEncoder.fit requires at least 2 documents")
        eff_min_df = min_df if min_df is not None else (2 if n_docs >= 100 else 1)

        doc_counters: list[Counter[str]] = []
        df_counts: Counter[str] = Counter()
        for doc in documents:
            cnt = Counter(_dense_tokens(doc))
            doc_counters.append(cnt)
            for term in cnt:
                df_counts[term] += 1

        eligible = [(term, df) for term, df in df_counts.items() if df >= eff_min_df]
        if not eligible:
            eligible = list(df_counts.items())
        # Keep top vocabulary terms by document frequency, breaking ties deterministically.
        eligible.sort(key=lambda kv: (-kv[1], kv[0]))
        kept = eligible[:max_vocab]
        vocab = {term: idx for idx, (term, _) in enumerate(kept)}
        vocab_size = len(vocab)
        if vocab_size < 2:
            raise ValueError("Insufficient vocabulary terms to fit SVD dense encoder")

        idf = np.zeros(vocab_size, dtype=np.float32)
        for term, idx in vocab.items():
            idf[idx] = float(math.log((1.0 + n_docs) / (1.0 + df_counts[term])) + 1.0)

        rows: list[int] = []
        cols: list[int] = []
        vals: list[float] = []
        for r_idx, cnt in enumerate(doc_counters):
            for term, tf in cnt.items():
                c_idx = vocab.get(term)
                if c_idx is not None:
                    rows.append(r_idx)
                    cols.append(c_idx)
                    vals.append((1.0 + math.log(tf)) * float(idf[c_idx]))

        tfidf = csr_matrix((vals, (rows, cols)), shape=(n_docs, vocab_size), dtype=np.float64)
        eff_k = max(2, min(dimension, min(n_docs, vocab_size) - 1))
        _, _, vt = svds(tfidf, k=eff_k)
        # svds returns singular vectors in ascending order; reverse to descending importance.
        components = np.ascontiguousarray(vt[::-1], dtype=np.float32)
        return cls(
            vocab=vocab,
            idf=idf,
            components=components,
            model_id=f"tfidf_svd_vn_{eff_k}d_v1",
        )

    def _vectorize_sparse(self, texts: list[str]) -> csr_matrix:
        rows: list[int] = []
        cols: list[int] = []
        vals: list[float] = []
        for r_idx, txt in enumerate(texts):
            cnt = Counter(_dense_tokens(txt))
            for term, tf in cnt.items():
                c_idx = self.vocab.get(term)
                if c_idx is not None:
                    rows.append(r_idx)
                    cols.append(c_idx)
                    vals.append((1.0 + math.log(tf)) * float(self.idf[c_idx]))
        return csr_matrix((vals, (rows, cols)), shape=(len(texts), len(self.vocab)), dtype=np.float32)

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        if not texts:
            return np.zeros((0, self.dimension), dtype=np.float32)
        sparse_mat = self._vectorize_sparse(texts)
        projected = sparse_mat @ self.components.T
        return _l2_normalize_rows(projected)

    def encode_query(self, query: str) -> list[float]:
        mat = self.encode_documents([query])
        return [float(x) for x in mat[0]]

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "encoder_meta.json").write_text(
            json.dumps(
                {
                    "backend": "tfidf_svd",
                    "model_id": self.model_id,
                    "dimension": self.dimension,
                    "vocab_size": len(self.vocab),
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (directory / "vocab.json").write_text(
            json.dumps(self.vocab, ensure_ascii=False),
            encoding="utf-8",
        )
        np.savez_compressed(directory / "svd_model.npz", idf=self.idf, components=self.components)

    @classmethod
    def load(cls, directory: Path) -> TruncatedSvdDenseEncoder:
        meta = json.loads((directory / "encoder_meta.json").read_text(encoding="utf-8"))
        vocab = json.loads((directory / "vocab.json").read_text(encoding="utf-8"))
        npz = np.load(directory / "svd_model.npz", allow_pickle=False)
        return cls(
            vocab={str(k): int(v) for k, v in vocab.items()},
            idf=npz["idf"],
            components=npz["components"],
            model_id=str(meta.get("model_id", "tfidf_svd_vn_v1")),
        )


class FastEmbedEncoder:
    """Optional ONNX CPU embedding backend via fastembed (e.g. intfloat/multilingual-e5-small)."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        try:
            from fastembed import TextEmbedding  # type: ignore[import-not-found]
        except ImportError as exc:
            raise IndexNotReadyError(
                "fastembed is not installed; install fastembed or use backend='tfidf_svd'."
            ) from exc
        self._model = TextEmbedding(model_name=model_name)
        self.model_id = model_name
        self._is_e5 = "e5" in model_name.lower()
        sample = self.encode_query("phở bò")
        self.dimension = len(sample)

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        prepared = [f"passage: {t}" for t in texts] if self._is_e5 else texts
        vecs = np.asarray(list(self._model.embed(prepared)), dtype=np.float32)
        return _l2_normalize_rows(vecs)

    def encode_query(self, query: str) -> list[float]:
        prepared = f"query: {query}" if self._is_e5 else query
        vec = next(iter(self._model.embed([prepared])))
        normed = _l2_normalize_rows(np.asarray(vec, dtype=np.float32))
        return [float(x) for x in normed]


class SentenceTransformerEncoder:
    """Optional CPU sentence-transformers backend (e.g. intfloat/multilingual-e5-base)."""

    def __init__(self, model_name: str = "intfloat/multilingual-e5-small") -> None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
        except ImportError as exc:
            raise IndexNotReadyError(
                "sentence-transformers is not installed; use backend='tfidf_svd' or install sentence-transformers."
            ) from exc
        self._model = SentenceTransformer(model_name, device="cpu")
        self.model_id = model_name
        self._is_e5 = "e5" in model_name.lower()
        sample = self.encode_query("phở bò")
        self.dimension = len(sample)

    def encode_documents(self, texts: list[str]) -> np.ndarray:
        prepared = [f"passage: {t}" for t in texts] if self._is_e5 else texts
        vecs = self._model.encode(prepared, normalize_embeddings=True, show_progress_bar=False)
        return _l2_normalize_rows(np.asarray(vecs, dtype=np.float32))

    def encode_query(self, query: str) -> list[float]:
        prepared = f"query: {query}" if self._is_e5 else query
        vec = self._model.encode(prepared, normalize_embeddings=True, show_progress_bar=False)
        return [float(x) for x in np.asarray(vec, dtype=np.float32)]


def build_dense_encoder(
    backend: str,
    documents: list[str] | None = None,
    model_name: str = "intfloat/multilingual-e5-small",
    dimension: int = 128,
) -> DenseTextEncoder:
    """Instantiate a CPU-feasible dense text encoder for the chosen backend."""
    if backend == "tfidf_svd":
        if not documents:
            raise ValueError("documents are required when fitting backend='tfidf_svd'")
        return TruncatedSvdDenseEncoder.fit(documents, dimension=dimension)
    if backend == "fastembed":
        return FastEmbedEncoder(model_name=model_name)
    if backend == "sentence_transformers":
        return SentenceTransformerEncoder(model_name=model_name)
    raise ValueError(f"Unsupported dense encoder backend: {backend!r}")


def load_saved_encoder(index_dir: Path) -> DenseTextEncoder:
    """Load the encoder recorded inside a populated dense index directory."""
    meta_path = index_dir / "encoder_meta.json"
    if not meta_path.is_file():
        raise IndexNotReadyError(f"Missing encoder_meta.json in {index_dir}")
    meta: dict[str, Any] = json.loads(meta_path.read_text(encoding="utf-8"))
    backend = str(meta.get("backend", ""))
    if backend == "tfidf_svd":
        return TruncatedSvdDenseEncoder.load(index_dir)
    if backend == "fastembed":
        return FastEmbedEncoder(model_name=str(meta["model_id"]))
    if backend == "sentence_transformers":
        return SentenceTransformerEncoder(model_name=str(meta["model_id"]))
    raise IndexNotReadyError(f"Unknown saved dense encoder backend: {backend!r}")


__all__ = [
    "DenseTextEncoder",
    "FastEmbedEncoder",
    "SentenceTransformerEncoder",
    "TruncatedSvdDenseEncoder",
    "build_dense_encoder",
    "load_saved_encoder",
]
