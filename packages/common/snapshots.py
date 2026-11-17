"""Publish complete Gold directories without replacing a named snapshot."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory


@contextmanager
def snapshot_workspace(destination: Path) -> Iterator[Path]:
    target = destination.resolve()
    if destination.is_symlink() or target.exists():
        raise FileExistsError(f"Snapshot already exists; choose a new output ID: {destination}")
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.parent / f".{target.name}.publish.lock"
    # Exclusive creation serializes cooperating publishers for the same snapshot ID.
    handle = lock.open("x", encoding="utf-8")
    try:
        with handle:
            with TemporaryDirectory(prefix=f".{target.name}.staging-", dir=target.parent) as stage_name:
                stage = Path(stage_name)
                yield stage
                if not (stage / "manifest.json").is_file():
                    raise ValueError("A complete snapshot manifest is required before publication")
                if target.exists():
                    raise FileExistsError(f"Snapshot appeared during build: {destination}")
                stage.rename(target)
    finally:
        # The owned handle is closed before unlink, including on build failures.
        lock.unlink(missing_ok=True)
