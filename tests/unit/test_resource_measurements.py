from __future__ import annotations

import importlib
import math
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest


def test_dense_pipelines_import_when_unix_resource_is_unavailable() -> None:
    code = """
import builtins
original_import = builtins.__import__
def no_resource(name, *args, **kwargs):
    if name == 'resource':
        raise ModuleNotFoundError('resource intentionally unavailable')
    return original_import(name, *args, **kwargs)
builtins.__import__ = no_resource
import pipelines.build_dense_sparse_index.dense
import pipelines.benchmark_retrieval.dense_hybrid_pilot
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_windows_peak_bytes_are_reported_in_mib(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("packages.common.resources")
    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(module, "_windows_peak_working_set_bytes", lambda: 134217728)
    assert module.get_peak_rss_mib() == 128.0


def test_linux_peak_kib_are_reported_in_mib(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("packages.common.resources")
    monkeypatch.setattr(module.sys, "platform", "linux")
    fake = ModuleType("resource")
    fake.RUSAGE_SELF = 0  # type: ignore[attr-defined]
    fake.getrusage = lambda who: SimpleNamespace(ru_maxrss=131072)  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "resource", fake)
    assert module.get_peak_rss_mib() == 128.0


@pytest.mark.parametrize("bad_peak", [-1, float("nan"), float("inf")])
def test_invalid_native_measurements_raise_instead_of_faking_zero(
    bad_peak: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    module = importlib.import_module("packages.common.resources")
    monkeypatch.setattr(module.sys, "platform", "win32")
    monkeypatch.setattr(module, "_windows_peak_working_set_bytes", lambda: bad_peak)
    with pytest.raises(OSError, match="peak|memory"):
        module.get_peak_rss_mib()


def test_native_measurement_error_propagates(monkeypatch: pytest.MonkeyPatch) -> None:
    module = importlib.import_module("packages.common.resources")
    monkeypatch.setattr(module.sys, "platform", "win32")

    def denied() -> int:
        raise OSError("native memory query denied")

    monkeypatch.setattr(module, "_windows_peak_working_set_bytes", denied)
    with pytest.raises(OSError, match="query denied"):
        module.get_peak_rss_mib()


def test_current_process_has_a_real_finite_peak_measurement() -> None:
    module = importlib.import_module("packages.common.resources")
    measured = module.get_peak_rss_mib()
    assert math.isfinite(measured)
    assert measured > 0
