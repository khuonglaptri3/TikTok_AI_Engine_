"""Pickle-free local dense vector index with exact metadata filtering (M6.1)."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from packages.common.exceptions import IndexNotReadyError
from packages.common.snapshots import snapshot_workspace
from packages.retrieval.dense.encoder import _l2_normalize_rows


def _sha256_file(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


class LocalDenseIndex:
    """In-memory cosine similarity dense index matching QdrantDenseAdapter search semantics."""

    def __init__(
        self,
        video_ids: list[str],
        embeddings: np.ndarray,
        model_id: str,
    ) -> None:
        if len(video_ids) != len(embeddings):
            raise ValueError("video_ids length must match embeddings row count")
        self.video_ids = [str(v) for v in video_ids]
        self.embeddings = np.ascontiguousarray(_l2_normalize_rows(embeddings), dtype=np.float32)
        self.model_id = model_id
        self.dimension = int(self.embeddings.shape[1]) if self.embeddings.ndim == 2 else 0
        self.vid_to_row: dict[str, int] = {vid: idx for idx, vid in enumerate(self.video_ids)}

    @classmethod
    def build(
        cls,
        video_ids: list[str],
        embeddings: np.ndarray,
        model_id: str,
    ) -> LocalDenseIndex:
        return cls(video_ids=video_ids, embeddings=embeddings, model_id=model_id)

    def check_collection_ready(self) -> tuple[bool, int]:
        count = len(self.video_ids)
        return count > 0, count

    def search_vectors(
        self,
        query_vector: list[float],
        top_k: int = 50,
        allowed_video_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        if not self.video_ids or top_k <= 0:
            return []
        q = _l2_normalize_rows(np.asarray(query_vector, dtype=np.float32))
        if q.shape[0] != self.dimension:
            raise ValueError(
                f"Query vector dimension {q.shape[0]} does not match index dimension {self.dimension}"
            )

        if allowed_video_ids is not None:
            row_indices = np.array(
                [self.vid_to_row[vid] for vid in allowed_video_ids if vid in self.vid_to_row],
                dtype=np.int64,
            )
            if len(row_indices) == 0:
                return []
            scores = self.embeddings[row_indices] @ q
            k = min(top_k, len(row_indices))
            if k == len(row_indices):
                order = np.argsort(-scores)
            else:
                top_local = np.argpartition(-scores, k - 1)[:k]
                order = top_local[np.argsort(-scores[top_local])]
            return [
                (self.video_ids[int(row_indices[pos])], round(float(scores[pos]), 4))
                for pos in order
            ]

        scores = self.embeddings @ q
        k = min(top_k, len(self.video_ids))
        if k == len(self.video_ids):
            order = np.argsort(-scores)
        else:
            top_local = np.argpartition(-scores, k - 1)[:k]
            order = top_local[np.argsort(-scores[top_local])]
        return [(self.video_ids[int(pos)], round(float(scores[pos]), 4)) for pos in order]

    def save(
        self,
        index_dir: Path,
        corpus_snapshot_id: str,
        extra_receipt: dict[str, Any] | None = None,
        encoder: Any | None = None,
    ) -> dict[str, Any]:
        """Persist embeddings, video IDs, optional encoder artifacts, and SHA256 receipt atomically."""
        target = index_dir.resolve()
        if index_dir.is_symlink() or target.exists():
            raise FileExistsError(f"Dense index already exists: {index_dir}")
        target.parent.mkdir(parents=True, exist_ok=True)
        with snapshot_workspace(index_dir) as stage:
            emb_path = stage / "embeddings.npy"
            ids_path = stage / "video_ids.json"
            np.save(emb_path, self.embeddings, allow_pickle=False)
            ids_path.write_text(json.dumps(self.video_ids, ensure_ascii=False), encoding="utf-8")

            tracked_names = ["embeddings.npy", "video_ids.json"]
            if encoder is not None:
                if hasattr(encoder, "save"):
                    encoder.save(stage)
                else:
                    backend = (
                        "fastembed"
                        if encoder.__class__.__name__ == "FastEmbedEncoder"
                        else "sentence_transformers"
                    )
                    (stage / "encoder_meta.json").write_text(
                        json.dumps(
                            {
                                "backend": backend,
                                "model_id": self.model_id,
                                "dimension": self.dimension,
                            },
                            indent=2,
                            ensure_ascii=False,
                        ),
                        encoding="utf-8",
                    )
                for extra_name in ("encoder_meta.json", "vocab.json", "svd_model.npz"):
                    if (stage / extra_name).is_file():
                        tracked_names.append(extra_name)

            files = {
                name: {
                    "sha256": _sha256_file(stage / name),
                    "size_bytes": (stage / name).stat().st_size,
                }
                for name in tracked_names
            }
            receipt: dict[str, Any] = {
                "index_type": "dense_cosine_f32_local",
                "corpus_snapshot_id": corpus_snapshot_id,
                "model_id": self.model_id,
                "created_at": datetime.now(UTC).isoformat(),
                "document_count": len(self.video_ids),
                "dimension": self.dimension,
                "index_bytes": sum(item["size_bytes"] for item in files.values()),
                "files": files,
            }
            if extra_receipt:
                receipt.update(extra_receipt)
            (stage / "dense-receipt.json").write_text(
                json.dumps(receipt, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            (stage / "manifest.json").write_text(
                json.dumps({"receipt_file": "dense-receipt.json"}, indent=2),
                encoding="utf-8",
            )
        return receipt

    @classmethod
    def load(cls, index_dir: Path) -> LocalDenseIndex:
        receipt_path = index_dir / "dense-receipt.json"
        if not receipt_path.is_file():
            raise IndexNotReadyError(f"Dense index receipt missing at {receipt_path}")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            for fname, meta in receipt.get("files", {}).items():
                fp = index_dir / fname
                if not fp.is_file():
                    raise IndexNotReadyError(f"Dense index file missing: {fp}")
                if _sha256_file(fp) != meta["sha256"]:
                    raise IndexNotReadyError(f"Dense index checksum mismatch for {fname}")
            video_ids = json.loads((index_dir / "video_ids.json").read_text(encoding="utf-8"))
            embeddings = np.load(index_dir / "embeddings.npy", allow_pickle=False)
            if len(video_ids) != int(embeddings.shape[0]):
                raise IndexNotReadyError("Dense index row count mismatch between IDs and embeddings")
            return cls(
                video_ids=video_ids,
                embeddings=embeddings,
                model_id=str(receipt.get("model_id", "unknown")),
            )
        except IndexNotReadyError:
            raise
        except Exception as exc:
            raise IndexNotReadyError(f"Failed to load dense index at {index_dir}: {exc}") from exc


__all__ = ["LocalDenseIndex"]
