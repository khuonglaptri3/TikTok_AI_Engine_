"""OS-backed process-lifetime peak resident memory, normalized to MiB."""

from __future__ import annotations

import math
import sys


def _windows_peak_working_set_bytes() -> int:
    if sys.platform != "win32":
        raise OSError("Windows peak memory measurement is unavailable on this platform.")

    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    current_process = kernel.GetCurrentProcess
    current_process.argtypes = []
    current_process.restype = wintypes.HANDLE
    query_memory = psapi.GetProcessMemoryInfo
    query_memory.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    ]
    query_memory.restype = wintypes.BOOL
    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    if not query_memory(current_process(), ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.PeakWorkingSetSize)


def get_peak_rss_mib() -> float:
    """Read a real process peak; propagate unavailable/invalid OS measurements."""
    if sys.platform == "win32":
        value = _windows_peak_working_set_bytes() / (1024.0 * 1024.0)
    else:
        import resource

        peak = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        # macOS reports bytes; Linux reports KiB.
        value = peak / (1024.0 * 1024.0 if sys.platform == "darwin" else 1024.0)
    if not math.isfinite(value) or value < 0:
        raise OSError("The OS returned an invalid peak memory measurement.")
    return value
