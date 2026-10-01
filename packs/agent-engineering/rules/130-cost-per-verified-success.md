### Optimize cost per verified success

- Measure cost per verified successful task, including failures, retries, tools, and human review,
  not cost per call.
- Profile each stage before optimizing; report p50 and p95 latency.
- Route work to cheaper models only after evals show quality holds for that task type.
- Bound parallelism; it can cut elapsed time while raising total spend and contention.
