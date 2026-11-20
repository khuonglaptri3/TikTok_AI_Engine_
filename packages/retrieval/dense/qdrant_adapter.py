from __future__ import annotations

import uuid
from typing import Any

import httpx

from packages.common.exceptions import IndexNotReadyError


def _qdrant_point_id(video_id: str) -> int | str:
    if video_id.isdigit():
        return int(video_id)
    return str(uuid.uuid5(uuid.NAMESPACE_URL, video_id))


class QdrantDenseAdapter:
    """HTTP adapter for Qdrant dense vector collection (docker-compose Qdrant v1.20+)."""

    def __init__(self, qdrant_url: str, collection_name: str, timeout_sec: float = 1.5) -> None:
        self.base_url = qdrant_url.rstrip("/")
        self.collection_name = collection_name
        self.timeout_sec = timeout_sec

    def check_collection_ready(self) -> tuple[bool, int]:
        """Return (is_ready, points_count) without raising when Qdrant container is offline."""
        url = f"{self.base_url}/collections/{self.collection_name}"
        try:
            resp = httpx.get(url, timeout=0.6)
            if resp.status_code != 200:
                return False, 0
            data: dict[str, Any] = resp.json().get("result", {})
            pts = int(data.get("points_count") or 0)
            return pts > 0, pts
        except Exception:
            return False, 0

    def ensure_collection(self, vector_size: int, distance: str = "Cosine") -> None:
        """Create or confirm the target Qdrant vector collection over HTTP."""
        url = f"{self.base_url}/collections/{self.collection_name}"
        payload = {"vectors": {"size": int(vector_size), "distance": distance}}
        try:
            resp = httpx.put(url, json=payload, timeout=self.timeout_sec)
        except Exception as exc:
            raise IndexNotReadyError(
                f"Unable to reach Qdrant at {self.base_url} while creating collection: {exc}"
            ) from exc
        if resp.status_code not in (200, 201):
            raise IndexNotReadyError(
                f"Failed to ensure Qdrant collection '{self.collection_name}' (HTTP {resp.status_code})"
            )

    def upsert_vectors(
        self,
        points: list[tuple[str, list[float], dict[str, Any]]],
        batch_size: int = 256,
    ) -> int:
        """Upsert vector points in bounded batches into Qdrant."""
        if not points:
            return 0
        url = f"{self.base_url}/collections/{self.collection_name}/points?wait=true"
        written = 0
        for start in range(0, len(points), max(1, batch_size)):
            chunk = points[start : start + max(1, batch_size)]
            body = {
                "points": [
                    {
                        "id": _qdrant_point_id(vid),
                        "vector": [float(x) for x in vec],
                        "payload": {"video_id": vid, **payload},
                    }
                    for vid, vec, payload in chunk
                ]
            }
            try:
                resp = httpx.put(url, json=body, timeout=max(self.timeout_sec, 10.0))
            except Exception as exc:
                raise IndexNotReadyError(
                    f"Qdrant upsert failed at {self.base_url}: {exc}"
                ) from exc
            if resp.status_code not in (200, 201):
                raise IndexNotReadyError(
                    f"Qdrant upsert rejected (HTTP {resp.status_code}) for '{self.collection_name}'"
                )
            written += len(chunk)
        return written

    def search_vectors(
        self,
        query_vector: list[float],
        top_k: int = 50,
        allowed_video_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        if allowed_video_ids is not None and len(allowed_video_ids) == 0:
            return []
        url = f"{self.base_url}/collections/{self.collection_name}/points/search"
        server_side_filter = allowed_video_ids is not None and len(allowed_video_ids) <= 5000
        req_limit = top_k if (allowed_video_ids is None or server_side_filter) else max(top_k * 6, 300)
        payload: dict[str, Any] = {
            "vector": query_vector,
            "limit": req_limit,
            "with_payload": ["video_id"],
        }
        if server_side_filter and allowed_video_ids is not None:
            payload["filter"] = {
                "must": [{"key": "video_id", "match": {"any": list(allowed_video_ids)}}]
            }
        try:
            resp = httpx.post(url, json=payload, timeout=self.timeout_sec)
        except Exception as exc:
            raise IndexNotReadyError(f"Qdrant vector service unreachable at {self.base_url}: {exc}") from exc

        if resp.status_code != 200:
            raise IndexNotReadyError(
                f"Qdrant collection '{self.collection_name}' not ready (HTTP {resp.status_code})"
            )

        hits = resp.json().get("result", [])
        results: list[tuple[str, float]] = []
        for hit in hits:
            vid = str((hit.get("payload") or {}).get("video_id") or hit.get("id") or "")
            if not vid:
                continue
            if allowed_video_ids is not None and vid not in allowed_video_ids:
                continue
            results.append((vid, round(float(hit.get("score") or 0.0), 4)))
            if len(results) >= top_k:
                break
        return results
