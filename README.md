# praxis-agents

> Put your engineering best practices into practice, across every AI coding agent.

**praxis-agents** is a Python library that takes your Markdown files of best practices, conventions, and engineering standards and applies them to AI coding tools such as Claude Code, Codex, and others.

Write your standards once. Every agent follows them.

## Why

Engineering guidance usually sits in docs that agents never read, or in tool-specific files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`) that drift out of sync. praxis-agents makes your Markdown the single source of truth.

## Features

- **Single source of truth:** author rules in plain Markdown
- **Multi-tool adapters:** compile and sync to Claude, Codex, and more
- **Verification:** check that agent output follows your rules
- **Extensible:** add an adapter for any tool

## Install

    uv tool install praxis-agents    # not yet published to PyPI

## Quick start

Start from a bundled pack, or write your own source in `.praxis/`:

    praxis packs                        # list bundled packs
    praxis init agent-engineering       # copy a pack into .praxis/
    praxis sync                         # write AGENTS.md, CLAUDE.md, and skills

### Rules

Always-on rules live in `.praxis/rules/*.md`, ordered by their numeric file-name prefix:

```markdown
---
scope: glob                # always (default) | glob
globs: ["**/agents/**"]    # required when scope is glob
---
Every agent loop has a max-iteration cap and a deterministic stop condition.
```

### Skills

On-demand skills use the [Agent Skills](https://agentskills.io) format:
`.praxis/skills/<name>/SKILL.md` (frontmatter `name` and `description`) plus optional
`references/**/*.md`.

### Targets

| Target | Writes | Read by |
|---|---|---|
| `agents` | `AGENTS.md`, `.agents/skills/` | Codex, Cursor, GitHub Copilot, and others |
| `claude` | `CLAUDE.md` (imports `AGENTS.md`), `.claude/skills/` | Claude Code |

    praxis sync                     # all targets
    praxis sync --target agents     # only AGENTS.md
    praxis check                    # exit 1 if generated files are stale (for CI)

In `AGENTS.md` and `CLAUDE.md`, praxis only edits the section between `<!-- praxis:begin -->` and
`<!-- praxis:end -->`; anything you write outside it is kept. Skill files are owned by praxis and
marked with a generated-file comment; praxis refuses to overwrite a skill file it didn't write.

## Development

This project uses [uv](https://docs.astral.sh/uv/):

    uv sync --extra dev
    uv run pytest

See [ideas.md](ideas.md) for the roadmap and open decisions.
