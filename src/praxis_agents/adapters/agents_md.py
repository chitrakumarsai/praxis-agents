"""``AGENTS.md`` and ``.agents/skills/``: read by Codex, Cursor, GitHub Copilot, and others."""

from __future__ import annotations

from praxis_agents.adapters.skills import SHARED_SKILLS_DIR, render_skills
from praxis_agents.model import OutputFile, Pack

PATH = "AGENTS.md"


def always_section(pack: Pack) -> str:
    """The always-on rules as one Markdown section, or an empty string if there are none."""
    always = [rule.body for rule in pack.rules if rule.scope == "always"]
    return "## Engineering standards\n\n" + "\n\n".join(always) if always else ""


def render(pack: Pack) -> tuple[OutputFile, ...]:
    scoped = [
        f"### Applies to {', '.join(f'`{glob}`' for glob in rule.globs)}\n\n{rule.body}"
        for rule in pack.rules
        if rule.scope == "glob"
    ]

    always = always_section(pack)
    sections = [always] if always else []
    if scoped:
        sections.append("## File-scoped standards\n\n" + "\n\n".join(scoped))
    return (OutputFile(PATH, "\n\n".join(sections)), *render_skills(pack, SHARED_SKILLS_DIR))
