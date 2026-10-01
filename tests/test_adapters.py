import pytest

from praxis.adapters import DEFAULT_TARGETS, TARGETS, resolve_targets
from praxis.adapters import agents_md, claude, copilot, cursor
from praxis.loader import split_frontmatter
from praxis.model import NOTICE, OutputFile, Pack, Reference, Rule, Skill

PACK = Pack(
    rules=(
        Rule(id="simplest", body="Start with the simplest workflow."),
        Rule(id="loops", body="Cap every loop.", scope="glob", globs=("**/agents/**", "*.py")),
        Rule(id="retries", body="Classify errors before retrying."),
    )
)


def test_agents_md_renders_always_rules_then_scoped_rules():
    (output,) = agents_md.render(PACK)

    assert output == OutputFile(
        "AGENTS.md",
        "## Engineering standards\n\n"
        "Start with the simplest workflow.\n\n"
        "Classify errors before retrying.\n\n"
        "## File-scoped standards\n\n"
        "### Applies to `**/agents/**`, `*.py`\n\n"
        "Cap every loop.",
    )


def test_agents_md_omits_empty_sections():
    (output,) = agents_md.render(Pack(rules=(Rule(id="one", body="Only rule."),)))

    assert output.content == "## Engineering standards\n\nOnly rule."


def test_claude_imports_agents_md():
    assert claude.render(PACK) == (OutputFile("CLAUDE.md", "@AGENTS.md"),)


def test_resolve_targets_adds_dependencies_first_without_duplicates():
    targets = resolve_targets(["claude", "agents", "claude"])

    assert [target.name for target in targets] == ["agents", "claude"]


def test_resolve_targets_rejects_unknown_names():
    with pytest.raises(ValueError, match="unknown target 'vim'"):
        resolve_targets(["vim"])


def test_every_target_dependency_is_registered():
    for target in TARGETS.values():
        assert set(target.requires) <= set(TARGETS)


SKILL = Skill(
    name="eval-design",
    description="Design evals: graders, datasets. Use when #writing evals.",
    body="# Evals\n\nGrade outcomes.",
    references=(Reference("references/metrics.md", "# Metrics"),),
)
SKILL_PACK = Pack(rules=PACK.rules, skills=(SKILL,))


@pytest.mark.parametrize(
    ("render", "base"),
    [(agents_md.render, ".agents/skills"), (claude.render, ".claude/skills")],
)
def test_targets_write_skills_as_owned_files(render, base):
    outputs = {output.path: output for output in render(SKILL_PACK)}

    skill_md = outputs[f"{base}/eval-design/SKILL.md"]
    reference = outputs[f"{base}/eval-design/references/metrics.md"]
    assert not skill_md.managed and not reference.managed
    assert skill_md.content.startswith("---\nname: eval-design\n")
    assert skill_md.content.endswith(f"{NOTICE}\n\n# Evals\n\nGrade outcomes.\n")
    assert reference.content == f"{NOTICE}\n\n# Metrics\n"


def test_rendered_skill_round_trips_through_the_loader(tmp_path):
    for output in agents_md.render(SKILL_PACK):
        if output.path.endswith("SKILL.md"):
            meta, body = split_frontmatter(output.content, tmp_path / output.path)

    assert meta == {"name": SKILL.name, "description": SKILL.description}
    assert body.strip().endswith(SKILL.body)


def test_cursor_writes_one_mdc_per_glob_rule():
    (output,) = cursor.render(PACK)

    assert output == OutputFile(
        ".cursor/rules/praxis-loops.mdc",
        f"---\nglobs: **/agents/**, *.py\nalwaysApply: false\n---\n\n{NOTICE}\n\nCap every loop.\n",
        managed=False,
    )


def test_cursor_writes_nothing_without_glob_rules():
    assert cursor.render(Pack(rules=(Rule(id="one", body="Only rule."),))) == ()


def test_copilot_writes_repo_instructions_and_path_instructions():
    repo, scoped = copilot.render(PACK)

    assert repo == OutputFile(
        ".github/copilot-instructions.md",
        "## Engineering standards\n\n"
        "Start with the simplest workflow.\n\n"
        "Classify errors before retrying.",
    )
    assert scoped == OutputFile(
        ".github/instructions/praxis-loops.instructions.md",
        f'---\napplyTo: "**/agents/**,*.py"\n---\n\n{NOTICE}\n\nCap every loop.\n',
        managed=False,
    )


def test_copilot_apply_to_is_valid_yaml(tmp_path):
    _, scoped = copilot.render(PACK)

    meta, _ = split_frontmatter(scoped.content, tmp_path / scoped.path)

    assert meta == {"applyTo": "**/agents/**,*.py"}


def test_default_targets_are_agents_and_claude():
    assert DEFAULT_TARGETS == ("agents", "claude")


def test_cursor_requires_agents():
    assert [target.name for target in resolve_targets(["cursor"])] == ["agents", "cursor"]


def test_copilot_skips_repo_instructions_without_always_rules():
    only_scoped = Pack(rules=(Rule(id="loops", body="Cap.", scope="glob", globs=("*.py",)),))

    assert [output.path for output in copilot.render(only_scoped)] == [
        ".github/instructions/praxis-loops.instructions.md"
    ]
