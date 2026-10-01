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

Write rules as Markdown files in `.praxis/rules/` (rendered in file-name order):

```markdown
---
scope: glob                # always (default) | glob
globs: ["**/agents/**"]    # required when scope is glob
---
Every agent loop has a max-iteration cap and a deterministic stop condition.
```

Then generate the instruction files:

    praxis sync                     # writes AGENTS.md and CLAUDE.md
    praxis sync --target agents     # only AGENTS.md
    praxis check                    # exit 1 if generated files are stale (for CI)

praxis only edits the section between `<!-- praxis:begin -->` and `<!-- praxis:end -->`;
anything you write outside it is kept.

## Development

This project uses [uv](https://docs.astral.sh/uv/):

    uv sync --extra dev
    uv run pytest

See [ideas.md](ideas.md) for the roadmap and open decisions.
