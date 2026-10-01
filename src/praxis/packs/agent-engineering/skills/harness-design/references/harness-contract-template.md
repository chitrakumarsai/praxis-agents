# Agent harness contract template

Every threshold needs a named owner and a reason tied to the project's consequences.

```markdown
# <Project> — Agent Harness Contract

## Purpose and ownership
- Goal / supported users:
- Supported tasks / non-goals:
- Required outcomes and evidence of completion:
- Runtime owner / eval owner / incident owner:

## Runtime architecture
- Model and version; prompt/config version:
- Workflow and agent decision points:
- State store, checkpoints, and resume policy:
- Context sources, selection rules, provenance, and trust boundaries:
- Memory purpose, access scope, expiry, and deletion policy:

## Tools and security
- Tool contracts and schemas:
- Identities, resource permissions, and execution isolation:
- Side effects, idempotency, and uncertain-write reconciliation:
- Secrets, outbound access, privacy, and trace retention:
- Mandatory guards and prohibited actions:

## Validation and control
- Intermediate validators and final outcome checks:
- Failure classes and permitted recovery by class:
- Time / token / cost / tool-call / correction budgets:
- No-progress detection and cancellation behavior:
- Terminal states and reporting rules:

## Human involvement
- Approval, clarification, and escalation triggers:
- Review packet and approver scope:
- Pending-state storage, expiry, rejection, and resume rules:

## Evaluation contract
- Task schema, fixtures, reference outcomes, and dataset versions:
- Development / held-out / capability / regression sets:
- Positive, negative, fault, and security coverage:
- Graders, rubrics, hard gates, partial credit, and calibration:
- Trial count, sampling settings, internal retry policy, and budgets:
- pass@1 / pass@k / pass^k reporting and aggregation:
- Unknowns, infrastructure failures, exclusions, and uncertainty:

## Observability and metrics
- Correlation IDs, trace fields, artifact/effect evidence:
- Success and safety definitions with denominators:
- Quality thresholds and critical slices:
- Latency SLOs, cost per request, and cost per verified success:
- Alerts, audit sampling, and failure taxonomy:

## Release and maintenance
- Baseline manifest and required CI checks:
- Acceptance thresholds and statistical decision rules:
- Canary plan, rollback triggers, and rollback owner:
- Production failure -> reviewed regression case process:
- Dataset freshness, judge calibration, and review schedule:
- Known limitations and accepted tradeoffs:
```
