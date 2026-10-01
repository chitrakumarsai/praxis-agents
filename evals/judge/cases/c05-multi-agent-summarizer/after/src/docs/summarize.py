"""Summarize a release note with a planner, a writer, and an editor agent for better quality."""

from agents.llm import ask

PLANNER = "You plan the structure of a summary."
WRITER = "You write summaries from a plan."
EDITOR = "You polish summaries for tone."


def summarize(release_note: str) -> str:
    # Three agents produce better summaries than one.
    plan = ask(PLANNER, f"Plan a 3-bullet summary of:\n{release_note}")
    draft = ask(WRITER, f"Plan:\n{plan}\n\nNote:\n{release_note}")
    return ask(EDITOR, f"Polish this summary:\n{draft}")
