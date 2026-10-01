---
# A process rule: a diff can't show it, so the LLM judge skips it.
judge: false
---
### Diagnose before changing prompts

- Find the earliest divergence in the trace, then check its inputs. Classify the cause: specification,
  context/retrieval, model decision, tool contract, infrastructure, state, validation, security,
  handoff, budget, or evaluation defect.
- Fix the layer that failed. Don't patch every failure with a longer prompt.
- Version prompts, models, tools, policies, and context assembly like code, and re-evaluate on change.
