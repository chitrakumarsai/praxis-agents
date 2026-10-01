---
name: eval-design
description: Design, build, or review evaluations for LLM features and agents - tasks and trials, datasets (golden, regression, capability, held-out), graders and LLM judges, repeated-trial metrics (pass@k, pass^k), and release gates. Use when writing evals or test suites for model behavior, choosing metrics, calibrating a judge, comparing a candidate against a baseline, or deciding whether a change can ship.
---

# Eval design

An eval measures the deployed system — model **and** harness together — on reviewed tasks, with
graders you have tested.

## Vocabulary

- **Task:** inputs, initial environment, permissions, required outcomes, prohibited effects, grading rules.
- **Trial:** one complete attempt under a declared policy, including allowed internal retries.
- **Suite:** tasks grouped around a capability or behavior.
- **Transcript** is what happened; **outcome** is what actually exists or changed afterward.

Grade outcomes plus the process constraints that matter. A completion message is never a substitute
for an artifact or state check. Don't require one exact tool sequence unless it encodes a real
safety or product requirement.

## Build the cases

Start small with real tasks, manual acceptance checks, and known failures. Cover: ordinary use,
difficult-but-valid inputs, missing data, tool faults, interruption/resume, permission boundaries,
malicious content, and **paired cases** where an action should and should not happen (proceed vs.
ask, act vs. abstain).

Each case records: input, initial fixture, allowed capabilities, required outcomes, prohibited
effects, reference evidence, grading rules, tags, owner. Prove solvability with a reference solution
or human-validated outcome. A zero-pass case may be ambiguous, environment-limited, or mis-graded —
investigate before changing it.

Dataset roles (golden, regression, capability, development, held-out, production-derived) and their
maintenance rules: `references/datasets-and-metrics.md`.

## Keep trials fair

Fresh isolated fixture per trial — reset files, databases, caches, memory, history. Pin dependencies.
Match the production runtime and config; document mocks and deviations. Control concurrency so
infrastructure contention doesn't look like agent failure. Protect graders, reference answers, and
hidden tests from the agent under evaluation.

## Graders

| Grader | Best use | Control |
|---|---|---|
| Deterministic code | Schemas, invariants, numeric tolerances, executable checks, external state | Test valid variants and known-bad outcomes |
| Model judge | Semantic correctness, completeness, groundedness, interaction quality | Narrow rubric, evidence, calibration, `unknown` option |
| Human review | Ambiguous criteria, specialist judgment, judge calibration | Shared rubric, blinding, adjudication |

- Grade dimensions separately: outcome, constraint compliance, factual support, interaction quality, efficiency.
- All mandatory invariants must pass before a task counts as success. A high average never cancels
  an unauthorized action.
- Judge prompts specify dimension, evidence, scoring anchors, exclusions, and allowed statuses;
  require evidence references. Content being graded can't override the rubric.
- Calibrate on clear passes, clear failures, edge cases, and adversarial outputs. Measure false
  accepts and false rejects separately. Randomize pairwise order; check verbosity bias.
- Version judge model, prompt, rubric, thresholds, and aggregation. A new judge's score shift is not
  an agent improvement.

## Non-determinism

Run repeated trials. For per-trial success probability `p`: pass@1 = `p`; pass@k = `1 - (1-p)^k`
(at least one success); pass^k = `p^k` (all succeed). At p = 0.8, k = 3: pass@3 = 0.992 but
pass^3 = 0.512. Compute per task, then aggregate with declared weights. pass@k doesn't prove the
product can pick the successful candidate. Estimators and reporting rules: `references/datasets-and-metrics.md`.

## Release gates

1. On each change: deterministic and contract checks plus a fast regression subset.
2. Before release: full regression, capability, security, and integration suites with repeated trials.
3. Compare to baseline per slice — critical failures, uncertainty, cost, and latency together.
4. Deploy gradually (canary) with predeclared outcome and rollback rules; shadow runs never duplicate writes.
5. Expand, hold, or roll back on the same criteria; add new cases to reviewed datasets.

Set gates **before** looking at candidate results. Never rerun a noisy suite until it passes.
Checklists: `references/eval-checklists.md`.
