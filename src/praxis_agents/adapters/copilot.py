"""GitHub Copilot: ``.github/copilot-instructions.md`` plus path-specific instruction files."""

from __future__ import annotations

import json

from praxis_agents.adapters.agents_md import always_section
from praxis_agents.model import NOTICE, OutputFile, Pack

REPO_PATH = ".github/copilot-instructions.md"
INSTRUCTIONS_DIR = ".github/instructions"


def render(pack: Pack) -> tuple[OutputFile, ...]:
    scoped = tuple(
        OutputFile(
            f"{INSTRUCTIONS_DIR}/praxis-{rule.id}.instructions.md",
            # A JSON string is a valid YAML double-quoted scalar.
            f"---\napplyTo: {json.dumps(','.join(rule.globs))}\n---\n\n{NOTICE}\n\n{rule.body}\n",
            managed=False,
        )
        for rule in pack.rules
        if rule.scope == "glob"
    )
    always = always_section(pack)
    repo = (OutputFile(REPO_PATH, always),) if always else ()
    # Copilot's coding agent also reads AGENTS.md, so with the `agents` target it sees these
    # rules twice; this file is what Copilot Chat and code review read.
    return (*repo, *scoped)
