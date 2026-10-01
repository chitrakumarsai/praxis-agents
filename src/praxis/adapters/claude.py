"""``CLAUDE.md``: imports ``AGENTS.md`` so Claude Code reads the same rules without a copy."""

from __future__ import annotations

from praxis.adapters import agents_md
from praxis.model import OutputFile, Pack

PATH = "CLAUDE.md"


def render(pack: Pack) -> tuple[OutputFile, ...]:
    return (OutputFile(PATH, f"@{agents_md.PATH}"),)
