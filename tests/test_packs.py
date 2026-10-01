"""Content checks for the packs in ``packs/``, until the skills loader exists (phase 2)."""

import re
from pathlib import Path

import pytest

from praxis.adapters import agents_md
from praxis.loader import load_pack, split_frontmatter
from praxis.sync import managed_block

PACKS_DIR = Path(__file__).resolve().parent.parent / "packs"
PACKS = sorted(path for path in PACKS_DIR.iterdir() if path.is_dir())
SKILLS = sorted(skill for pack in PACKS for skill in (pack / "skills").glob("*/SKILL.md"))

# Always-on rules are loaded on every request; keep them short enough to be followed.
MAX_RULE_LINES = 160
SKILL_NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
MAX_SKILL_NAME = 64
MAX_DESCRIPTION = 1024
REFERENCE_LINK = re.compile(r"`(references/[^`]+)`")


def test_packs_exist():
    assert PACKS


@pytest.mark.parametrize("pack", PACKS, ids=lambda path: path.name)
def test_pack_rules_load_and_fit_budget(pack):
    (output,) = agents_md.render(load_pack(pack))

    assert len(managed_block(output.content).splitlines()) <= MAX_RULE_LINES


@pytest.mark.parametrize("skill_md", SKILLS, ids=lambda path: path.parent.name)
def test_skill_frontmatter_follows_agent_skills_format(skill_md):
    meta, body = split_frontmatter(skill_md.read_text(encoding="utf-8"), skill_md)

    assert set(meta) == {"name", "description"}
    assert meta["name"] == skill_md.parent.name
    assert SKILL_NAME.match(meta["name"]) and len(meta["name"]) <= MAX_SKILL_NAME
    assert 0 < len(meta["description"]) <= MAX_DESCRIPTION
    assert body.strip()


@pytest.mark.parametrize("skill_md", SKILLS, ids=lambda path: path.parent.name)
def test_skill_reference_links_resolve(skill_md):
    links = REFERENCE_LINK.findall(skill_md.read_text(encoding="utf-8"))

    assert [link for link in links if not (skill_md.parent / link).is_file()] == []
