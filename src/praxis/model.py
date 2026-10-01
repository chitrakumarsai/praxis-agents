"""Core data model: a pack of rules, and the files adapters render from it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Scope = Literal["always", "glob"]
SCOPES: tuple[Scope, ...] = ("always", "glob")

BEGIN_MARKER = "<!-- praxis:begin -->"
END_MARKER = "<!-- praxis:end -->"


@dataclass(frozen=True)
class Rule:
    """One instruction an agent should follow."""

    id: str
    body: str
    scope: Scope = "always"
    globs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Pack:
    """Everything loaded from a praxis source directory."""

    rules: tuple[Rule, ...] = ()


@dataclass(frozen=True)
class OutputFile:
    """Content of the praxis-managed block in one generated file."""

    path: str  # POSIX path relative to the project root
    content: str
