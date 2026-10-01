"""Packs shipped inside the praxis package (``praxis/packs/<name>/``)."""

from __future__ import annotations

import os
import shutil
import tempfile
from collections.abc import Iterator
from contextlib import contextmanager
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # importlib.resources.abc is Python 3.11+
    from importlib.resources.abc import Traversable

PACKS_DIR = "packs"


def _packs_root() -> Traversable:
    return files("praxis").joinpath(PACKS_DIR)


def available_packs() -> tuple[str, ...]:
    return tuple(sorted(entry.name for entry in _packs_root().iterdir() if entry.is_dir()))


def _pack(name: str) -> Traversable:
    if name not in available_packs():
        raise ValueError(f"unknown pack {name!r}; available: {', '.join(available_packs())}")
    return _packs_root().joinpath(name)


def _copy_tree(source: Traversable, destination: Path) -> None:
    destination.mkdir(parents=True)
    for entry in source.iterdir():
        if entry.is_dir():
            _copy_tree(entry, destination / entry.name)
        else:
            (destination / entry.name).write_bytes(entry.read_bytes())


@contextmanager
def pack_source(name: str) -> Iterator[Path]:
    """Yield a filesystem path to a bundled pack, copying it out if the package is zipped."""
    pack = _pack(name)
    if isinstance(pack, Path):
        yield pack
        return
    with tempfile.TemporaryDirectory() as tmp:
        destination = Path(tmp) / name
        _copy_tree(pack, destination)
        yield destination


def install_pack(name: str, destination: Path) -> None:
    """Copy a bundled pack to ``destination``, which must not exist yet."""
    pack = _pack(name)
    if destination.exists():
        raise ValueError(f"{destination} already exists; remove it or pass a different --source")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Copy into a sibling staging directory, then rename, so a failure never leaves a partial pack.
    staging = Path(tempfile.mkdtemp(dir=destination.parent, prefix=f".{destination.name}-"))
    try:
        _copy_tree(pack, staging / name)
        os.rename(staging / name, destination)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
