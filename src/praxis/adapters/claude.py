"""Claude Code: ``CLAUDE.md`` imports ``AGENTS.md``; skills go to ``.claude/skills/``."""

from __future__ import annotations

from praxis.adapters import agents_md
from praxis.adapters.skills import render_skills
from praxis.model import OutputFile, Pack

PATH = "CLAUDE.md"
SKILLS_DIR = ".claude/skills"


def render(pack: Pack) -> tuple[OutputFile, ...]:
    return (OutputFile(PATH, f"@{agents_md.PATH}"), *render_skills(pack, SKILLS_DIR))
