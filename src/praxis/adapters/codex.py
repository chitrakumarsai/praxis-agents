"""Adapter for OpenAI Codex, which reads AGENTS.md."""

from __future__ import annotations

from .base import MarkdownAdapter


class CodexAdapter(MarkdownAdapter):
    name = "codex"
    filename = "AGENTS.md"
    heading = "AGENTS.md"
    intro = "Follow these project rules when working in this repository."
