"""Content checks for the packs bundled in ``praxis/packs``."""

import re

import pytest

from praxis.adapters import agents_md
from praxis.bundled import available_packs, pack_source
from praxis.loader import load_pack
from praxis.sync import managed_block

PACK_NAMES = available_packs()

# Always-on rules are loaded on every request; keep them short enough to be followed.
MAX_RULE_LINES = 160
REFERENCE_LINK = re.compile(r"`(references/[^`]+)`")


def test_agent_engineering_pack_is_bundled():
    assert "agent-engineering" in PACK_NAMES


@pytest.mark.parametrize("name", PACK_NAMES)
def test_pack_rules_fit_budget(name):
    with pack_source(name) as source:
        rendered = agents_md.render(load_pack(source))

    (agents,) = [output for output in rendered if output.path == agents_md.PATH]
    assert len(managed_block(agents.content).splitlines()) <= MAX_RULE_LINES


@pytest.mark.parametrize("name", PACK_NAMES)
def test_skill_reference_links_resolve(name):
    with pack_source(name) as source:
        pack = load_pack(source)

    for skill in pack.skills:
        shipped = {reference.path for reference in skill.references}
        assert set(REFERENCE_LINK.findall(skill.body)) <= shipped, skill.name
