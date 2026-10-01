# Evaluation checklists

## Evaluation readiness

- [ ] Cases cover common tasks, edge cases, negative actions, faults, and adversarial inputs.
- [ ] Reference outcomes establish that tasks and graders are valid.
- [ ] Trials start from isolated fixtures with no leaked history or answers.
- [ ] Runtime differences from production are documented.
- [ ] Graders accept valid alternatives and reject known bad outcomes.
- [ ] Semantic judges have human calibration and an unknown option.
- [ ] Hard gates, partial credit, aggregation, and denominators are explicit.
- [ ] Development, held-out, capability, and regression roles are documented.
- [ ] Repeated-trial counts, resource budgets, and uncertainty reporting are defined.
- [ ] Successful and failed traces have been manually inspected.

## Release readiness

- [ ] Candidate and baseline versions, fixtures, graders, and reports are preserved.
- [ ] Required deterministic, regression, security, and integration checks pass.
- [ ] Critical slices and repeated failures are reviewed individually.
- [ ] Quality changes are assessed with uncertainty, cost, and latency.
- [ ] Resume, duplicate-effect prevention, approval, and cancellation paths are checked.
- [ ] Canary scope, monitoring window, rollback thresholds, and owner are set.
- [ ] Sensitive telemetry is redacted and access controlled.
- [ ] Exclusions, degraded dependencies, and unresolved limitations are visible.

## Ongoing operations

- [ ] Review outcome metrics, tail latency, spend, and failure categories regularly.
- [ ] Audit sampled successes, failures, refusals, and human handoffs.
- [ ] Convert important incidents into sanitized, reviewed regression cases.
- [ ] Recalibrate judges and refresh stale reference data.
- [ ] Review dataset saturation, leakage, representativeness, and ownership.
- [ ] Verify retention, deletion, credential scope, and rollback readiness.
