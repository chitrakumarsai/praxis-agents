# Workflow patterns

## Prompt chaining

**Shape:** input → stage A → check → stage B → final verification.

Use when the task breaks into a stable sequence and intermediate outputs can be checked. Give each
stage a clear input/output contract; pass verified information forward with evidence references.
Watch for error propagation and serial latency. If an upstream artifact changes, revalidate
dependents. Evaluate stage-level correctness and end-to-end outcomes.

## Routing

**Shape:** input → route selection → specialized path → outcome check.

Use when input categories benefit from different handling. Start with deterministic rules if they
suffice. Give ambiguous or unsupported inputs a defined fallback. Measure routing errors separately
from downstream quality — a strong specialist can't fix requests sent to the wrong path. Check rare
categories and distribution drift.

## Parallelization

**Shape:** input → independent calls → aggregation → verification.

Two forms: independent subtasks, or multiple attempts/reviews of the same task. Specify what the
aggregator does on disagreement or branch failure. Bound concurrency and total cost. Outputs may
share the same error; majority agreement is not proof. If a parallel branch performs a required
safety check, wait for it before committing the protected action. Serialize conflicting writes.

## Orchestrator-workers

**Shape:** task → dynamic decomposition → bounded workers → verified synthesis.

Use when subtasks can't be specified beforehand. Give workers explicit scope, evidence access,
output contracts, and local budgets within a global budget. The orchestrator owns coverage, conflict
resolution, and final verification. Worker completion claims need evidence. Avoid overlapping
ownership of mutable state and unbounded recursive delegation. Compare gains against coordination
overhead, duplicated context, missed subtasks, and synthesis failures.

## Evaluator-optimizer

**Shape:** candidate → evaluation → targeted revision → re-evaluation.

Use when success criteria are clear and feedback demonstrably improves output. Prefer deterministic
checks for encodable properties; semantic feedback for judgment. Set an iteration limit, cost/time
budget, and no-progress rule. Preserve valid work; repair only the failing part. Track whether gains
on one dimension cause regressions on another. The runtime critic is part of the system under test —
an independent evaluation must confirm its preferred revisions actually improve quality.

## Bounded agent loop

**Shape:** observe → propose → authorize → act → verify → update state → continue or stop.

Use when the next action depends on intermediate observations. Require authoritative feedback from
tools or the environment, not the model's narrative. Enforce permissions, deadlines, cost and
iteration limits, and cancellation outside the model. The agent may propose completion; the harness
verifies required outcomes. Provide explicit paths for partial completion, unavailable prerequisites,
human intervention, and exhausted budgets. Test in controlled environments before widening scope.

## Anti-patterns

| Anti-pattern | Better approach |
|---|---|
| Choosing a framework before defining the task | Establish workflow, criteria, and baseline first |
| Assuming every AI feature needs an agent | Match autonomy to actual decision requirements |
| Building a general platform before one use case | Deliver one measurable end-to-end slice |
| Adding agents to improve a demo | Measure against coordination overhead and a simpler baseline |
| Optimizing model cost in isolation | Measure cost and effort per verified successful task |
