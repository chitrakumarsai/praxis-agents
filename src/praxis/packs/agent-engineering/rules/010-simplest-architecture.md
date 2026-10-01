### Choose the simplest architecture that works

- Prefer, in order: conventional code → one validated model call → retrieval or one narrow tool →
  fixed workflow → routing / parallel / orchestrator-workers → bounded agent loop.
- Use an agent only when the next action genuinely depends on intermediate observations.
  Use multiple agents only when a measured gain beats a single-agent baseline.
- Keep a baseline and measure every added layer against it on the same tasks and budget.
- Build one complete, measurable end-to-end slice before any reusable platform or framework.
