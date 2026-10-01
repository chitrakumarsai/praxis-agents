# Fields and diagnostics

## Suggested chunk/document metadata

```text
tenant_id, document_id, document_version, content_hash,
page_index, printed_page_label, section_path, source_span,
parser_version, extraction_method, effective_date, access_policy_ref
```

## Suggested trace fields

```text
request_id, job_id, document_version, configuration_versions,
retrieved_chunk_ids, retrieval_scores, model_identifier,
tokens, latency_by_stage, retry_count, tool_outcomes,
validation_failures, review_reason, final_status
```

Prefer references to restricted artifacts over raw sensitive payloads in general logs.

## Symptom → first checks

| Symptom | First checks |
|---|---|
| Correct passage retrieved, wrong answer | Scope, competing evidence, truncation, prompt, model capability |
| Quality dropped after embedding change | Query/index model compatibility, rebuilt index, ranking changes |
| Value comes from the wrong section | Clause metadata, scope, definitions, amendments |
| Scanned documents perform poorly | OCR quality, page coverage, table reconstruction |
| Intermittent production failures | Quotas, timeouts, concurrency, queue delay, dependency failures |
| Costs grow without better outcomes | Retry loops, duplicate jobs, oversized context, unnecessary calls |

Investigate reproducible failure clusters instead of editing prompts for isolated examples.

## Production engineering

- Queues with bounded concurrency, retry limits, dead-letter handling, and backpressure.
- Design for at-least-once delivery: atomic job claims, uniqueness constraints, idempotent writes.
  A separate "already completed?" check alone can race.
- Checkpoint expensive stages so a crash doesn't repeat successful work.
- Job states: `queued`, `running`, `needs_review`, `succeeded`, `failed`, `cancelled`.
- Measure user-perceived response time separately from total processing time; streaming improves
  responsiveness without reducing completion time.
