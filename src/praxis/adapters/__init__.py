"""Target registry. Each adapter is a pure ``render(pack) -> tuple[OutputFile, ...]``."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from praxis.adapters import agents_md, claude, copilot, cursor
from praxis.model import OutputFile, Pack


@dataclass(frozen=True)
class Target:
    name: str
    render: Callable[[Pack], tuple[OutputFile, ...]]
    requires: tuple[str, ...] = ()


TARGETS: dict[str, Target] = {
    target.name: target
    for target in (
        Target("agents", agents_md.render),
        Target("claude", claude.render, requires=("agents",)),
        # Cursor reads always-on rules from AGENTS.md; its own files carry only glob-scoped rules.
        Target("cursor", cursor.render, requires=("agents",)),
        Target("copilot", copilot.render),
    )
}

# Cursor and Copilot already read AGENTS.md, so their native files are opt-in.
DEFAULT_TARGETS: tuple[str, ...] = ("agents", "claude")


def resolve_targets(names: Iterable[str]) -> tuple[Target, ...]:
    """Return the named targets plus their dependencies, dependencies first, without duplicates."""
    resolved: dict[str, Target] = {}

    def visit(name: str) -> None:
        if name in resolved:
            return
        if name not in TARGETS:
            raise ValueError(f"unknown target {name!r}; expected one of {', '.join(TARGETS)}")
        for dependency in TARGETS[name].requires:
            visit(dependency)
        resolved[name] = TARGETS[name]

    for name in names:
        visit(name)
    return tuple(resolved.values())
