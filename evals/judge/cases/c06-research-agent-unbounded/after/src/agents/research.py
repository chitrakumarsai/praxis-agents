"""Research agent: searches until the model says it has enough to answer."""

from agents.llm import next_step
from agents.tools import search, validate_query


def research(question: str) -> str:
    notes = []
    while True:
        step = next_step(question, notes)
        if step.kind == "answer":
            return step.text
        query = validate_query(step.query)
        notes.append(search(query))
