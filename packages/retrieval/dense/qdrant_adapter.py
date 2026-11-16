from __future__ import annotations

from typing import Any

import httpx

from packages.common.exceptions import IndexNotReadyError


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

    def search_vectors(
        self,
        query_vector: list[float],
        top_k: int = 50,
        allowed_video_ids: set[str] | None = None,
    ) -> list[tuple[str, float]]:
        url = f"{self.base_url}/collections/{self.collection_name}/points/search"
        payload: dict[str, Any] = {
            "vector": query_vector,
            "limit": top_k,
            "with_payload": ["video_id"],
        }
        if allowed_video_ids is not None and len(allowed_video_ids) <= 5000:
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
            if vid:
                results.append((vid, round(float(hit.get("score") or 0.0), 4)))
        return results
