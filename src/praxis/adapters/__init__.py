"""Adapters that compile rules into each AI coding tool's instruction file.

To support another tool, subclass :class:`Adapter` (or :class:`MarkdownAdapter`)
and pass it to :func:`register_adapter`.
"""

from __future__ import annotations

from .base import GENERATED_NOTICE, Adapter, MarkdownAdapter, Rule, RuleSet
from .claude import ClaudeAdapter
from .codex import CodexAdapter

_REGISTRY: dict[str, type[Adapter]] = {}


def register_adapter(adapter: type[Adapter]) -> type[Adapter]:
    """Register an adapter class under its ``name``. Usable as a decorator."""
    _REGISTRY[adapter.name] = adapter
    return adapter


def get_adapter(name: str) -> Adapter:
    """Return an instance of the adapter registered as ``name``."""
    try:
        return _REGISTRY[name]()
    except KeyError:
        known = ", ".join(available_targets())
        raise ValueError(f"Unknown target '{name}'. Available targets: {known}") from None


def available_targets() -> list[str]:
    return sorted(_REGISTRY)


register_adapter(ClaudeAdapter)
register_adapter(CodexAdapter)

__all__ = [
    "GENERATED_NOTICE",
    "Adapter",
    "ClaudeAdapter",
    "CodexAdapter",
    "MarkdownAdapter",
    "Rule",
    "RuleSet",
    "available_targets",
    "get_adapter",
    "register_adapter",
]
