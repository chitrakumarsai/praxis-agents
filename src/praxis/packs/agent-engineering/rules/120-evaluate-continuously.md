### Evaluate the model and harness together

- Grade outcomes, not one exact call sequence, unless the sequence is a real requirement.
- Prefer deterministic graders; use model judges for semantic properties with a rubric, evidence,
  and an `unknown` option; calibrate judges against human-reviewed cases.
- Test graders on known-good and known-bad outputs before trusting them.
- Run repeated trials when outcomes vary; report pass@1 and pass^k, not only pass@k.
- Turn every material production failure into a reviewed regression case.
- Never rerun a noisy suite until it passes, and never tune on the held-out set.
