"""``AGENTS.md``: the shared instruction file read by Codex, Cursor, Copilot, and others."""

from __future__ import annotations

from praxis.model import OutputFile, Pack

PATH = "AGENTS.md"


def render(pack: Pack) -> tuple[OutputFile, ...]:
    always = [rule.body for rule in pack.rules if rule.scope == "always"]
    scoped = [
        f"### Applies to {', '.join(f'`{glob}`' for glob in rule.globs)}\n\n{rule.body}"
        for rule in pack.rules
        if rule.scope == "glob"
    ]

    sections = []
    if always:
        sections.append("## Engineering standards\n\n" + "\n\n".join(always))
    if scoped:
        sections.append("## File-scoped standards\n\n" + "\n\n".join(scoped))
    return (OutputFile(PATH, "\n\n".join(sections)),)
