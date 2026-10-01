"""Render skills in the Agent Skills format: ``<base>/<name>/SKILL.md`` plus references."""

from __future__ import annotations

import yaml

from praxis.model import NOTICE, OutputFile, Pack, Skill

# Codex, Cursor, and GitHub Copilot read this project-level directory.
SHARED_SKILLS_DIR = ".agents/skills"


def render_skills(pack: Pack, base: str) -> tuple[OutputFile, ...]:
    return tuple(output for skill in pack.skills for output in _render_skill(skill, base))


def _render_skill(skill: Skill, base: str) -> tuple[OutputFile, ...]:
    frontmatter = yaml.safe_dump(
        {"name": skill.name, "description": skill.description},
        sort_keys=False,
        allow_unicode=True,
        width=float("inf"),
    )
    skill_md = OutputFile(
        f"{base}/{skill.name}/SKILL.md",
        f"---\n{frontmatter}---\n\n{NOTICE}\n\n{skill.body}\n",
        managed=False,
    )
    references = tuple(
        OutputFile(f"{base}/{skill.name}/{ref.path}", f"{NOTICE}\n\n{ref.content}\n", managed=False)
        for ref in skill.references
    )
    return (skill_md, *references)
