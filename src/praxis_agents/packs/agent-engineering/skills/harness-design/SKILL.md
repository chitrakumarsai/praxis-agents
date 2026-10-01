---
name: harness-design
description: Design or review the runtime harness around an LLM agent - state and context, tool contracts, validators and guardrails, retries and self-correction, stopping rules, human approval, and tracing. Use when implementing an agent loop, adding tools or side effects, handling retries or timeouts, adding human-in-the-loop, or debugging an agent run.
---

# Harness design

**Core principle:** the model proposes actions and content; the harness enforces execution
boundaries, preserves state, verifies results, and controls termination. Evaluate both together.

## Reference loop

```text
Request + identity + authorized scope
  -> input checks and admission
  -> durable state / context builder
  -> model proposal  <---------------------------+
  -> schema + policy + budget checks             |
  -> approval gate (if required)                 |
  -> tool router -> bounded execution            |
  -> normalize results / verify effects          |
  -> checkpoint + validate + classify            |
  -> continue / targeted correction -------------+
  -> final verification / stop / escalate
  -> result + evidence + completion status
Cross-cutting: authorization, secrets, isolation, tracing, cancellation.
```

Per request: authenticate and set goal, scope, criteria, budgets → load state and reconcile
unresolved writes → build context with provenance → ask for one bounded next action → validate
proposal, authorization, budget, prerequisites → get approval only when required → execute with
deadlines and operation IDs → observe actual effects and checkpoint → validate, classify, repair
only affected work → continue or stop/escalate → verify completion and return explicit status.

## State

Keep in structured state: run/session/tenant/task IDs; goal and acceptance criteria; authorized
operations and approval records; current step, completed artifacts, validation results, unresolved
issues; evidence references with timestamps; tool operation IDs, idempotency keys, attempt counts,
uncertain effects; token/cost/time/retry budgets; model, prompt, tool-schema, and context versions.

Checkpoint at meaningful boundaries. After a crash, reconcile external effects before resuming —
a local checkpoint and a remote write are not atomic. For concurrent work, define who owns each
state field and invalidate dependent results when inputs change.

## Tools

Each tool contract defines: purpose, inputs, outputs, effects, authorization, execution limits,
recovery, and verification. Full table: `references/tool-contract.md`.

## Validation layers

1. **Admission** — identity, scope, input shape, resource limits.
2. **Before actions** — tool schema, resource permissions, policy, required approvals.
3. **After actions** — output shape, error semantics, actual external effects.
4. **Before completion** — required outcomes, constraints, evidence, unresolved failures.

Deterministic checks for encodable properties; semantic checks with an explicit uncertainty path.
A semantic judge is never the sole security boundary for privileged actions.

## Retries and self-correction

Classify first, then recover by class — see `references/failure-handling.md`. Self-correction runs
**candidate → validate → classify → targeted feedback → bounded repair → revalidate**, preserving
correct work. Stop on verified completion, any budget limit, repeated action/error signatures without
state change, no progress across a window, policy block, missing prerequisite, denied approval, or
cancellation.

## Human-in-the-loop

Separate approval-before-action, result review, and ambiguity resolution. A review packet holds: the
goal and decision needed; exact action, target, parameters, consequences; evidence, failures,
alternatives, uncertainty; completed work, rollback options, resume behavior. Persist pending state;
bind approval to action + parameter version; record approver, scope, timestamp, expiry; define
timeout, rejection, and cancellation behavior. Track unnecessary and missed escalations.

## Tracing and debugging

One correlation ID across model calls, tools, workers, approvals, and external operations. Capture
versions, context source references, action proposals, tool results, state transitions, validation
verdicts, retry/stop reasons, approvals, timing, tokens, cost, and final outcome evidence. No hidden
chain-of-thought is needed. Debug from the **earliest divergence** and its upstream inputs; classify
with `references/failure-handling.md`.

For a written design, fill in `references/harness-contract-template.md`.
