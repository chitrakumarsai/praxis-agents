"""Cursor: one ``.cursor/rules/praxis-<id>.mdc`` per glob-scoped rule."""

from __future__ import annotations

from praxis_agents.model import NOTICE, OutputFile, Pack

RULES_DIR = ".cursor/rules"


def render(pack: Pack) -> tuple[OutputFile, ...]:
    # Cursor parses `globs` as an unquoted, comma-separated string, not a YAML list.
    return tuple(
        OutputFile(
            f"{RULES_DIR}/praxis-{rule.id}.mdc",
            f"---\nglobs: {', '.join(rule.globs)}\nalwaysApply: false\n---\n\n"
            f"{NOTICE}\n\n{rule.body}\n",
            managed=False,
        )
        for rule in pack.rules
        if rule.scope == "glob"
    )
