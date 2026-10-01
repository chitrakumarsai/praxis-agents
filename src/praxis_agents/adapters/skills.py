"""Render skills in the Agent Skills format: ``<base>/<name>/SKILL.md`` plus references."""

from __future__ import annotations

import yaml

from praxis_agents.model import NOTICE, OutputFile, Pack, Skill
from praxis_agents.sync import MANIFEST_NAME, manifest_text

# Codex, Cursor, and GitHub Copilot read this project-level directory.
SHARED_SKILLS_DIR = ".agents/skills"


def render_skills(pack: Pack, base: str) -> tuple[OutputFile, ...]:
    outputs = [output for skill in pack.skills for output in _render_skill(skill, base)]
    # Scripts and assets can't carry the generated notice, so a manifest of their hashes in the
    # skills directory records which files praxis wrote.
    resources = {
        f"{skill.name}/{resource.path}": resource.data
        for skill in pack.skills
        for resource in skill.resources
    }
    if resources:
        manifest = manifest_text(resources)
        outputs.append(OutputFile(f"{base}/{MANIFEST_NAME}", manifest, managed=False))
    return tuple(outputs)


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
    resources = tuple(
        OutputFile(
            f"{base}/{skill.name}/{resource.path}",
            resource.data,
            managed=False,
            executable=resource.executable,
        )
        for resource in skill.resources
    )
    return (skill_md, *references, *resources)
