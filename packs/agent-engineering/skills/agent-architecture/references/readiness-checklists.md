# Readiness checklists

## Before implementation

- [ ] A specific user workflow and useful outcome are defined.
- [ ] Current effort, failure modes, and constraints are understood.
- [ ] Data and tool access have been checked with representative examples.
- [ ] Acceptance criteria and reviewed evaluation cases exist.
- [ ] The main uncertainties have small, decision-oriented experiments.
- [ ] A simple baseline and explicit non-goals are agreed.

## Before a pilot

- [ ] A complete path from realistic input to verified result works.
- [ ] Tool contracts, permissions, timeouts, and retry limits are enforced.
- [ ] State, context, failure status, and human handoffs are explicit.
- [ ] Actual effects are verified and uncertain writes are reconciled.
- [ ] Representative, negative, and adversarial cases have been evaluated.
- [ ] Quality, user effort, cost, and latency are acceptable for the pilot.
- [ ] Traces provide useful evidence without exposing unnecessary sensitive data.
- [ ] Release scope, monitoring, rollback triggers, and owners are named.

## During operation

- [ ] Sample both successful and unsuccessful runs for review.
- [ ] Track critical violations and false completion separately.
- [ ] Convert material incidents into reviewed regression cases.
- [ ] Reassess data freshness, grader quality, and changing usage.
- [ ] Re-evaluate meaningful model, prompt, tool, and policy changes.
- [ ] Check that user value still justifies operating and review costs.
