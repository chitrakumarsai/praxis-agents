"""Run state for the claims agent: the authoritative record, separate from model context."""

from dataclasses import dataclass, field


@dataclass
class Evidence:
    source: str  # document id or tool call id
    excerpt: str
    retrieved_at: str


@dataclass
class ClaimRunState:
    tenant_id: str
    claim_id: str
    goal: str
    constraints: list[str]
    completed_steps: list[str] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    attempts: int = 0
    budget_remaining_usd: float = 1.0

    def context(self, max_evidence: int = 5) -> str:
        """Selected view for the model: goal, constraints, recent evidence with sources."""
        recent = self.evidence[-max_evidence:]
        cited = "\n".join(f"- [{e.source}] {e.excerpt}" for e in recent)
        return (
            f"Goal: {self.goal}\nConstraints: {'; '.join(self.constraints)}\n"
            f"Done: {', '.join(self.completed_steps) or 'nothing yet'}\n"
            f"Open questions: {'; '.join(self.open_questions) or 'none'}\nEvidence:\n{cited}"
        )
