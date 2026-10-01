"""Claude Code: ``CLAUDE.md`` imports ``AGENTS.md``; skills go to ``.claude/skills/``."""

from __future__ import annotations

from praxis_agents.adapters import agents_md
from praxis_agents.adapters.skills import render_skills
from praxis_agents.model import OutputFile, Pack

PATH = "CLAUDE.md"
SKILLS_DIR = ".claude/skills"


def render(pack: Pack) -> tuple[OutputFile, ...]:
    return (OutputFile(PATH, f"@{agents_md.PATH}"), *render_skills(pack, SKILLS_DIR))
