"""Target registry. Each adapter is a pure ``render(pack) -> tuple[OutputFile, ...]``."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from praxis.adapters import agents_md, claude, copilot, cursor
from praxis.adapters.skills import SHARED_SKILLS_DIR
from praxis.model import OutputFile, Pack


@dataclass(frozen=True)
class Target:
    name: str
    render: Callable[[Pack], tuple[OutputFile, ...]]
    requires: tuple[str, ...] = ()
    owned_dirs: tuple[str, ...] = ()  # where it writes praxis-owned files
    managed_paths: tuple[str, ...] = ()  # files where it writes a managed block


TARGETS: dict[str, Target] = {
    target.name: target
    for target in (
        Target(
            "agents",
            agents_md.render,
            owned_dirs=(SHARED_SKILLS_DIR,),
            managed_paths=(agents_md.PATH,),
        ),
        Target(
            "claude",
            claude.render,
            requires=("agents",),
            owned_dirs=(claude.SKILLS_DIR,),
            managed_paths=(claude.PATH,),
        ),
        # Cursor reads always-on rules from AGENTS.md; its own files carry only glob-scoped rules.
        Target("cursor", cursor.render, requires=("agents",), owned_dirs=(cursor.RULES_DIR,)),
        Target(
            "copilot",
            copilot.render,
            owned_dirs=(copilot.INSTRUCTIONS_DIR,),
            managed_paths=(copilot.REPO_PATH,),
        ),
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
