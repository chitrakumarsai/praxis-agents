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

    pip install praxis-agents

## Quick start

    praxis init
    praxis sync --target claude,codex
