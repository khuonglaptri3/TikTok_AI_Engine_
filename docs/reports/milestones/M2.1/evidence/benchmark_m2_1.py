#!/usr/bin/env python3
"""Measure cold and 100-request warm latency (concurrency=1) for NicheAnalyticsEngine."""

from __future__ import annotations

import json
import os
import platform
import time
from pathlib import Path

import numpy as np

from packages.analytics import NicheAnalyticsEngine
from packages.common.settings import AppSettings
from packages.data_contracts.query import NicheQueryFilter

OUT_JSON = Path(__file__).resolve().parent / "latency_benchmark_100.json"

FIXED_FILTERS: list[NicheQueryFilter] = [
    NicheQueryFilter(),
    NicheQueryFilter(video_format="Review quán ăn", city_norm="hồ chí minh"),
    NicheQueryFilter(food_category="Món nước & Sợi", city_norm="hà nội"),
    NicheQueryFilter(price_tier="budget_lt50k", occasion="an_dem"),
    NicheQueryFilter(video_format="Hướng dẫn nấu ăn", duration_bucket="medium_45_90s"),
    NicheQueryFilter(food_category="Lẩu & Nướng", region="south", price_tier="casual_150_500k"),
    NicheQueryFilter(food_category="Ăn vặt & Đường phố", city_norm="hồ chí minh", duration_bucket="short_20_45s"),
    NicheQueryFilter(video_format="Mukbang", occasion="tu_tap_ban_be"),
    NicheQueryFilter(food_category="Đồ ngọt, Trà & Cà phê", city_norm="đà lạt"),
    NicheQueryFilter(video_format="Review sản phẩm ăn uống", price_tier="mid_50_150k"),
]


def _cpu_model() -> str:
    try:
        for line in Path("/proc/cpuinfo").read_text(encoding="utf-8").splitlines():
            if line.lower().startswith("model name"):
                return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or platform.machine()


def _mem_total_gb() -> float:
    try:
        for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
            if line.startswith("MemTotal:"):
                kb = int(line.split()[1])
                return round(kb / (1024 * 1024), 2)
    except OSError:
        pass
    return 0.0


def main() -> None:
    corpus_dir = AppSettings().corpus_dir
    t_load0 = time.perf_counter()
    engine = NicheAnalyticsEngine.from_corpus_dir(corpus_dir)
    load_ms = round((time.perf_counter() - t_load0) * 1000.0, 2)

    # Cold request (first query after initialization)
    t_cold0 = time.perf_counter()
    cold_res = engine.compute_benchmark(FIXED_FILTERS[1])
    cold_wall_ms = round((time.perf_counter() - t_cold0) * 1000.0, 2)

    # 100 fixed warm requests at concurrency=1
    warm_wall_ms: list[float] = []
    warm_internal_ms: list[float] = []
    for idx in range(100):
        q = FIXED_FILTERS[idx % len(FIXED_FILTERS)]
        t0 = time.perf_counter()
        res = engine.compute_benchmark(q)
        elapsed = round((time.perf_counter() - t0) * 1000.0, 2)
        warm_wall_ms.append(elapsed)
        warm_internal_ms.append(float(res.timings_ms.get("total_ms", elapsed)))

    arr_wall = np.array(warm_wall_ms, dtype=np.float64)
    arr_int = np.array(warm_internal_ms, dtype=np.float64)
    p95_wall = round(float(np.percentile(arr_wall, 95)), 2)

    report = {
        "corpus_snapshot_id": engine.manifest.snapshot_id,
        "total_videos": len(engine.df_videos),
        "concurrency": 1,
        "warm_request_count": len(warm_wall_ms),
        "provisional_p95_budget_ms": 250.0,
        "budget_met": bool(p95_wall <= 250.0),
        "hardware": {
            "os": platform.platform(),
            "python": platform.python_version(),
            "cpu_model": _cpu_model(),
            "logical_cpus": os.cpu_count(),
            "ram_total_gb": _mem_total_gb(),
        },
        "load_and_preindex_ms": load_ms,
        "cold_request": {
            "wall_ms": cold_wall_ms,
            "internal_total_ms": cold_res.timings_ms.get("total_ms", 0.0),
            "matched_videos": cold_res.matched_videos,
        },
        "warm_wall_ms": {
            "min": round(float(arr_wall.min()), 2),
            "p50": round(float(np.percentile(arr_wall, 50)), 2),
            "mean": round(float(arr_wall.mean()), 2),
            "p95": p95_wall,
            "max": round(float(arr_wall.max()), 2),
        },
        "warm_internal_ms": {
            "p50": round(float(np.percentile(arr_int, 50)), 2),
            "mean": round(float(arr_int.mean()), 2),
            "p95": round(float(np.percentile(arr_int, 95)), 2),
            "max": round(float(arr_int.max()), 2),
        },
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
