# agent-engineering pack

Engineering standards for building LLM features and AI agents: architecture choice, harness design,
evaluation, RAG, and structured extraction.

| Part | Loaded | Contents |
|---|---|---|
| `rules/` | Always (compiled into `AGENTS.md`) | 14 short, checkable rules |
| `skills/` | On demand, picked by description | `agent-architecture`, `harness-design`, `eval-design`, `rag-pipeline`, `structured-extraction` |
| `skills/*/references/` | Read by a skill when it needs depth | Templates, checklists, metric definitions, worked designs |

## Use

Until `praxis init --pack` exists (phase 2), compile the rules directly:

    praxis sync --source path/to/packs/agent-engineering

Skills aren't emitted by praxis yet; they're in the Agent Skills format (`SKILL.md` with `name` and
`description` frontmatter), so they can be copied into a tool's skills directory by hand.

## Sources

Distilled from the author's own guides, which build on these articles:

- Anthropic, [Building effective agents](https://www.anthropic.com/engineering/building-effective-agents)
  (Erik Schluntz and Barry Zhang) — workflow patterns.
- Anthropic, [Demystifying evals for AI agents](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
  — task/trial terminology, grader types, repeated-trial metrics.
- OWASP, [LLM01 Prompt Injection](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM01_PromptInjection.md).

The text here is an original distillation, not a copy of those articles.
