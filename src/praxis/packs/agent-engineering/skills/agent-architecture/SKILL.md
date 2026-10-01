---
name: agent-architecture
description: Choose and justify the architecture for an LLM feature or agent (single call, workflow, routing, parallelization, orchestrator-workers, evaluator-optimizer, or bounded agent loop), and plan a new AI project. Use when starting an AI feature, deciding whether an agent or multi-agent system is warranted, picking a framework, or writing a project brief.
---

# Agent architecture

Pick the least autonomous design that meets the acceptance criteria, then add complexity only
when evidence on the same task set shows it helps.

## 1. Frame the problem first

Before naming any pattern, answer:

- What event starts the task and what result ends it?
- What inputs, data, tools, and permissions are available?
- Which steps need interpretation or judgment?
- What happens when a result is wrong, incomplete, or late?
- What improvement justifies building and maintaining this?

Write success along three axes: **user value** (time or effort saved), **task correctness**
(required outputs, evidence, constraints), and **operating viability** (cost, latency, reliability,
security, support burden). Use `references/kickoff-template.md` for the project brief.

## 2. Reduce the most consequential uncertainty first

Give each experiment a hypothesis, time limit, measurement, and decision rule:

| Uncertainty | Small experiment |
|---|---|
| Data access or quality | Retrieve representative inputs through the intended access path |
| Ambiguous correctness | Two reviewers assess the same cases independently |
| Model capability | Minimal baseline on reviewed examples |
| Tool feasibility | Exercise one key integration in a controlled environment |
| User usefulness | Users try the result inside their real workflow |
| Cost and latency | Measure a complete run, including verification and correction |

## 3. Choose the pattern

| Task characteristic | Start with | Evidence needed before adding complexity |
|---|---|---|
| Explicit, stable rules | Conventional code | A real language or judgment requirement |
| One bounded language task | Single call + validation | Repeated failures decomposition would fix |
| Needs external evidence | Retrieval or one narrow tool | Missing information limits quality |
| Predictable stages | Prompt chaining (fixed workflow) | Stages with distinct responsibilities and useful checks |
| Input types need different handling | Routing | Categories can be identified reliably |
| Independent work | Parallelization | Measured gain after aggregation cost |
| Subtasks depend on input | Orchestrator-workers | Dynamic decomposition beats predefined tasks |
| Output improves with feedback | Evaluator-optimizer | Reliable feedback, measurable gain per iteration |
| Path can't be specified in advance | Bounded agent loop | Useful observations, controllable actions, verifiable outcomes |

These compose; they are not a maturity ladder. A fixed workflow can be the right production
architecture indefinitely. Details and failure modes per pattern: `references/workflow-patterns.md`.

## 4. Frameworks come after understanding the runtime

Adopt a framework only if it reduces work without hiding behavior you must control. Check:
visibility into prompts/messages/state/tool calls; explicit retry, timeout, concurrency, and
cancellation; tracing, eval, authorization, and persistence support; swappable models and tools;
testable failure paths; dependency and migration cost. Inspect its actual defaults — never assume
it enforces your policy.

## 5. Deliver in stages

Discover → Define → Test feasibility → Build a complete slice → Improve → Pilot → Operate.
Each stage has an exit decision; record experiments as "We believe change X will improve failure
category Y, measured by Z, within these limits," and keep a short decision log.

Readiness checklists for implementation, pilot, and operation: `references/readiness-checklists.md`.
