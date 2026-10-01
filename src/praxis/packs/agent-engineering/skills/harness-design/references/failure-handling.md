# Failure handling

## Recovery by failure class

| Failure | Default recovery | Do not |
|---|---|---|
| Transient transport failure on a safe operation | Bounded backoff with jitter; respect server retry guidance | Retry indefinitely |
| Rate limit or overloaded dependency | Back off, reduce concurrency, draw from a shared retry budget | Let all workers retry at once |
| Invalid arguments or output schema | Precise validation feedback; repair the affected part | Repeat the identical bad request |
| Semantic failure | Supply missing evidence or the specific discrepancy; retry locally | Assume another sample is an explanation |
| Permission denial or policy block | Stop that action; request authorized intervention if appropriate | Try another tool to evade it |
| Missing prerequisite or data | Acquire it if authorized; otherwise report or escalate | Invent the missing input |
| Timeout after a write | Query operation status and reconcile | Assume the write didn't happen |
| Persistent dependency failure | Fail explicitly or use an approved fallback | Present degraded results as complete |

Terminal statuses: `completed`, `partial`, `needs_human`, `failed`, `cancelled`, `budget_exhausted`.
On every terminal path: checkpoint known state, identify uncertain effects, release resources, and
return an honest summary of completed and unfinished work.

## Failure taxonomy

Assign one primary cause with optional contributing tags; keep `unknown` when evidence is insufficient.

| Category | Typical symptom | First check |
|---|---|---|
| Specification | Conflicting or impossible acceptance criteria | Task, policy, reference solution |
| Context/retrieval | Missing, stale, irrelevant, or truncated evidence | Retrieved sources and assembled context |
| Model decision | Wrong plan, unsupported claim, wrong action | First incorrect proposal and its evidence |
| Tool contract | Invalid arguments or misread results | Schemas, descriptions, error mapping |
| Dependency/infrastructure | Timeout, rate limit, resource exhaustion | Service status, contention, timing |
| State/orchestration | Duplicate writes, bad resume, race, stale checkpoint | Operation IDs and state transitions |
| Validation/guardrail | Bad output accepted or valid action blocked | Validator inputs, rule version, false-positive rate |
| Security/authorization | Injection followed, scope exceeded, data exposed | Trust boundary and enforcement point |
| Human handoff | Missing context, stale approval, stalled queue | Review packet and approval lifecycle |
| Budget/stopping | Loops, early completion, wasted retries | Progress record and stop policy |
| Evaluation defect | Wrong label, leaky fixture, broken grader | Reference outcome and isolated rerun |

## Incident procedure

Preserve safe evidence → reproduce the smallest useful case → establish the cause → add a regression
case → fix the appropriate layer → verify related behavior → monitor after release. Don't patch every
failure with a longer prompt.
