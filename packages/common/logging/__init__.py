"""Per-stage latency timing and structured telemetry helpers."""

from __future__ import annotations

import time
from collections.abc import Iterator
from contextlib import contextmanager


class StageTimer:
    """Records measured stage latencies in milliseconds."""

    def __init__(self) -> None:
        self._start_total = time.perf_counter()
        self.stages_ms: dict[str, float] = {}

    @contextmanager
    def measure(self, stage_name: str) -> Iterator[None]:
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            self.stages_ms[stage_name] = elapsed_ms

    def finalize(self) -> dict[str, float]:
        out = dict(self.stages_ms)
        out["total_ms"] = round((time.perf_counter() - self._start_total) * 1000.0, 2)
        return out
