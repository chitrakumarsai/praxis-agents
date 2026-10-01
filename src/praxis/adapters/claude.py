"""Adapter for Claude Code, which reads CLAUDE.md."""

from __future__ import annotations

from .base import MarkdownAdapter


class ClaudeAdapter(MarkdownAdapter):
    name = "claude"
    filename = "CLAUDE.md"
    intro = "Follow these project rules when working in this repository."
