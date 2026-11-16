#!/usr/bin/env python3
"""Scan tracked/workspace source files to block leaked API keys before commit or CI."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

SKIP_DIRS = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "data",
    "artifacts",
}

TEXT_EXTENSIONS = {
    ".py",
    ".ipynb",
    ".md",
    ".txt",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".ini",
    ".tex",
    ".env.example",
}

SECRET_PATTERNS = [
    ("Google/Gemini API Key", re.compile(r"AIzaSy[A-Za-z0-9_-]{33}")),
    ("Legacy Hardcoded Third-Party Key", re.compile(r"210167a3" + r"06e2affee74535654c4b8ed5")),
]


def scan_workspace(root: Path = ROOT_DIR) -> list[tuple[str, int, str]]:
    findings: list[tuple[str, int, str]] = []
    for path in root.rglob("*"):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.name == ".env":
            continue
        if path.suffix not in TEXT_EXTENSIONS and path.name != ".env.example":
            continue
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        for line_no, line in enumerate(content.splitlines(), start=1):
            for label, regex in SECRET_PATTERNS:
                if regex.search(line):
                    rel = path.relative_to(root).as_posix()
                    findings.append((rel, line_no, label))
    return findings


def main() -> int:
    findings = scan_workspace()
    if findings:
        print(f"FAIL: Detected {len(findings)} secret leak(s):")
        for rel, line_no, label in findings:
            print(f"  - {rel}:{line_no} [{label}]")
        return 1
    print("PASS: Zero secret leaks detected across workspace.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
