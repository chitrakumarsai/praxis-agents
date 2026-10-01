# Datasets and metrics

## Dataset roles

| Dataset or suite | Purpose | Maintenance rule |
|---|---|---|
| Golden | Reviewed cases with trusted expected behavior or evidence | Revalidate labels and freshness; allow equivalent correct outputs |
| Regression | Protect supported behavior, including past incidents | Keep critical cases stable; track per-case failures |
| Capability | Measure difficult or newly desired behavior | Keep headroom; add harder cases as it saturates |
| Development | Prompt, tool, and harness iteration | Expect heavy use; never present its score as generalization |
| Held-out | Estimate behavior beyond tuning examples | Restrict access, prevent leakage, rotate deliberately |
| Production-derived | Recent usage and new failures | Sanitize, preserve provenance, review before promotion |

Roles can overlap. "Golden" doesn't mean exact string match. Capability tasks graduate to regression
once reliably solved. Keep safety-critical slices visible even when rare. Prevent near-duplicates
leaking across splits — split by source, family, user/session, or time. Correct labels through an
explicit process without silently rewriting historical scores.

## Repeated-trial estimators

With `n` exchangeable trials and `c` successes (`n >= k`):

```text
pass@k estimate = 1 - C(n-c, k) / C(n, k)
pass^k estimate = C(c, k) / C(n, k)
C(a, k) = 0 when a < k
```

Apply per task, then aggregate with declared weights — never to a suite-average `p` when difficulty
varies. Shared outages, shared state, adaptive retries, or changing policies break independence;
report them. Keep internal self-correction (inside a trial) distinct from independent trials. Report
sample counts, per-task results, confidence intervals, and paired baseline comparisons; cluster
uncertainty by task.

## Metrics

Define population, time window, eligibility, and denominator before comparing numbers. Segment by
task family, risk tier, version, tool, and relevant input slices.

| Metric | Definition |
|---|---|
| Verified task success | Trials meeting all required outcomes and invariants / eligible trials |
| End-to-end completion | Verified completed requests / eligible production requests, incl. operational failures |
| pass@1, pass@k, pass^k | Per-task, with declared k, policy, and aggregation |
| Hard-constraint violation rate | Trials with ≥1 actual mandatory violation / eligible trials |
| Grading coverage | Trials with valid grading evidence / attempted trials |
| Unknown/ungradable rate | Trials without a defensible verdict / attempted trials |
| Correction recovery rate | Initially failed, correction-eligible trials that pass / correction-eligible trials |
| Tool error rate | Failed tool attempts / tool attempts, by error class |
| Duplicate-effect rate | Confirmed unintended duplicate effects / write operations |
| Escalation rate and quality | Escalations / requests; audited unnecessary and missed escalations |
| Latency | p50/p95/p99 end-to-end; model, tool, queue, and human-wait components separately |
| Cost per successful task | Total cost across successes and failures / verified successes |
| Regression delta | Candidate minus baseline, with sample counts and uncertainty |
| Judge false accept/reject | Accepted human-fail cases / human-fail; rejected human-pass / human-pass |
| Outcome-claim mismatch | Audited completion claims lacking verified outcomes / audited claims |

A zero denominator is "undefined", not zero. Report blocked attack attempts separately from
successful attacks. Track stop reasons and failure categories as distributions.
