import json
from pathlib import Path

import pytest

from praxis.loader import PackError, load_pack, parse_rule
from praxis.model import ForbidCheck, Reference, Rule, RunCheck, Skill

SOURCE = Path("rules/020-bounded-loops.md")


def test_rule_without_frontmatter_uses_defaults():
    rule = parse_rule("Cap every agent loop.\n", Path("rules/bounded-loops.md"))

    assert rule == Rule(id="bounded-loops", body="Cap every agent loop.")


def test_rule_id_defaults_to_stem_without_numeric_prefix():
    rule = parse_rule("Cap every agent loop.", SOURCE)

    assert rule.id == "bounded-loops"


def test_rule_reads_frontmatter():
    text = "---\nid: loops\nscope: glob\nglobs: ['**/agents/**']\n---\n\nCap loops.\n"

    rule = parse_rule(text, SOURCE)

    assert rule == Rule(id="loops", body="Cap loops.", scope="glob", globs=("**/agents/**",))


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("---\nscope: glob\n---\nBody", "requires a non-empty 'globs'"),
        ("---\nglobs: ['*.py']\n---\nBody", "'globs' is only allowed with scope 'glob'"),
        ("---\nscope: sometimes\n---\nBody", "invalid scope 'sometimes'"),
        ("---\ncolour: red\n---\nBody", "unknown frontmatter key(s): colour"),
        ("---\nid: Not_Valid\n---\nBody", "invalid id 'Not_Valid'"),
        ("---\nglobs: '*.py'\nscope: glob\n---\nBody", "'globs' must be a list"),
        ("---\nid: empty\n---\n   \n", "rule body is empty"),
        ("---\nid: open\nBody", "frontmatter is not closed"),
        ("---\nid: [unclosed\n---\nBody", "invalid YAML frontmatter"),
        ("---\n- a\n- b\n---\nBody", "frontmatter must be a mapping"),
    ],
)
def test_invalid_rules_raise_with_source_path(text, message):
    with pytest.raises(PackError) as exc:
        parse_rule(text, SOURCE)

    assert str(SOURCE) in str(exc.value)
    assert message in str(exc.value)


def write_rule(root: Path, name: str, text: str) -> None:
    rules = root / "rules"
    rules.mkdir(parents=True, exist_ok=True)
    (rules / name).write_text(text, encoding="utf-8")


def test_load_pack_orders_rules_by_file_name(tmp_path):
    write_rule(tmp_path, "020-second.md", "Second.")
    write_rule(tmp_path, "010-first.md", "First.")
    write_rule(tmp_path, "notes.txt", "Ignored.")

    pack = load_pack(tmp_path)

    assert [rule.id for rule in pack.rules] == ["first", "second"]


def test_load_pack_rejects_duplicate_ids(tmp_path):
    write_rule(tmp_path, "010-loops.md", "One.")
    write_rule(tmp_path, "020-loops.md", "Two.")

    with pytest.raises(PackError, match="duplicate rule id 'loops'"):
        load_pack(tmp_path)


def test_load_pack_requires_rules_or_skills(tmp_path):
    with pytest.raises(PackError, match="no rules/ or skills/ directory"):
        load_pack(tmp_path)


@pytest.mark.parametrize("marker", ["<!-- praxis:begin -->", "<!-- praxis:end -->"])
def test_rule_body_cannot_contain_praxis_markers(marker):
    with pytest.raises(PackError, match="must not contain praxis markers"):
        parse_rule(f"Docs mention {marker} here.", SOURCE)


def test_non_string_frontmatter_keys_raise_pack_error():
    with pytest.raises(PackError, match="unknown frontmatter key"):
        parse_rule("---\n1: x\ntrue: y\n---\nBody", SOURCE)


@pytest.mark.parametrize("yaml_glob", ['"src/`x`/*.py"', '"a\\nb"', '"*.{ts,tsx}"', "'say \"hi\"'"])
def test_globs_reject_backticks_and_newlines(yaml_glob):
    with pytest.raises(PackError, match="'globs' must be a list"):
        parse_rule(f"---\nscope: glob\nglobs: [{yaml_glob}]\n---\nBody", SOURCE)


def test_load_pack_orders_numeric_prefixes_numerically(tmp_path):
    write_rule(tmp_path, "10-tenth.md", "Ten.")
    write_rule(tmp_path, "2-second.md", "Two.")
    write_rule(tmp_path, "unprefixed.md", "Last.")

    assert [rule.id for rule in load_pack(tmp_path).rules] == ["second", "tenth", "unprefixed"]


def test_load_pack_reads_frontmatter_after_utf8_bom(tmp_path):
    write_rule(tmp_path, "bom.md", "﻿---\nid: with-bom\n---\nBody.")

    assert load_pack(tmp_path).rules[0].id == "with-bom"


def test_load_pack_skips_hidden_files_and_directories(tmp_path):
    write_rule(tmp_path, "real.md", "Body.")
    write_rule(tmp_path, ".#real.md", "Editor lock file.")
    (tmp_path / "rules" / "folder.md").mkdir()

    assert [rule.id for rule in load_pack(tmp_path).rules] == ["real"]


def write_skill(root: Path, name: str, skill_md: str, files: dict[str, str] | None = None) -> Path:
    skill_dir = root / "skills" / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(skill_md, encoding="utf-8")
    for relpath, text in (files or {}).items():
        (skill_dir / relpath).parent.mkdir(parents=True, exist_ok=True)
        (skill_dir / relpath).write_text(text, encoding="utf-8")
    return skill_dir


SKILL_MD = "---\nname: eval-design\ndescription: Design evals. Use when writing evals.\n---\n\n# Evals\n"


def test_load_pack_without_skills_directory_has_no_skills(tmp_path):
    write_rule(tmp_path, "rule.md", "Body.")

    assert load_pack(tmp_path).skills == ()


def test_load_pack_reads_skills_and_nested_references(tmp_path):
    write_rule(tmp_path, "rule.md", "Body.")
    write_skill(
        tmp_path,
        "eval-design",
        SKILL_MD,
        {"references/metrics.md": "# Metrics\n", "references/deep/pass-at-k.md": "# pass@k\n"},
    )

    (skill,) = load_pack(tmp_path).skills

    assert skill == Skill(
        name="eval-design",
        description="Design evals. Use when writing evals.",
        body="# Evals",
        references=(
            Reference("references/deep/pass-at-k.md", "# pass@k"),
            Reference("references/metrics.md", "# Metrics"),
        ),
    )


def test_load_pack_orders_skills_by_name(tmp_path):
    write_rule(tmp_path, "rule.md", "Body.")
    for name in ("zeta", "alpha"):
        write_skill(tmp_path, name, f"---\nname: {name}\ndescription: Does {name}.\n---\nBody.")

    assert [skill.name for skill in load_pack(tmp_path).skills] == ["alpha", "zeta"]


@pytest.mark.parametrize(
    ("dir_name", "skill_md", "message"),
    [
        ("evals", SKILL_MD, "name 'eval-design' must match its directory 'evals'"),
        ("Bad_Name", "---\nname: Bad_Name\ndescription: x\n---\nBody", "invalid skill name"),
        ("x" * 65, f"---\nname: {'x' * 65}\ndescription: x\n---\nBody", "invalid skill name"),
        ("s", "---\nname: s\n---\nBody", "'description' must be a string of 1-1024 characters"),
        ("s", f"---\nname: s\ndescription: {'d' * 1025}\n---\nBody", "1-1024 characters"),
        ("s", "---\nname: s\ndescription: x\nlicense: MIT\n---\nBody", "unknown frontmatter key(s): license"),
        ("s", "---\nname: s\ndescription: x\n---\n  \n", "skill body is empty"),
        ("s", "---\nname: s\ndescription: x\n---\n<!-- praxis:end -->", "must not contain praxis markers"),
    ],
)
def test_invalid_skills_raise(tmp_path, dir_name, skill_md, message):
    write_rule(tmp_path, "rule.md", "Body.")
    write_skill(tmp_path, dir_name, skill_md)

    with pytest.raises(PackError) as exc:
        load_pack(tmp_path)

    assert message in str(exc.value)
    assert "SKILL.md" in str(exc.value)


def test_skill_directory_requires_skill_md(tmp_path):
    write_rule(tmp_path, "rule.md", "Body.")
    (tmp_path / "skills" / "empty").mkdir(parents=True)

    with pytest.raises(PackError, match="SKILL.md not found"):
        load_pack(tmp_path)


def test_skill_rejects_unsupported_files(tmp_path):
    write_rule(tmp_path, "rule.md", "Body.")
    write_skill(tmp_path, "eval-design", SKILL_MD, {"scripts/run.sh": "echo hi"})

    with pytest.raises(PackError, match="unsupported file 'scripts/run.sh'"):
        load_pack(tmp_path)


def test_skill_ignores_hidden_files(tmp_path):
    write_rule(tmp_path, "rule.md", "Body.")
    write_skill(tmp_path, "eval-design", SKILL_MD, {".DS_Store": "", "references/.#lock.md": ""})

    assert load_pack(tmp_path).skills[0].references == ()


def test_indented_fence_inside_frontmatter_does_not_close_it():
    text = "---\nid: fenced\nscope: glob\nglobs:\n  - '*.py'\n  ---\n---\nBody"

    with pytest.raises(PackError, match="invalid YAML frontmatter"):
        parse_rule(text, SOURCE)


def test_skill_description_whitespace_is_normalized(tmp_path):
    write_rule(tmp_path, "rule.md", "Body.")
    write_skill(tmp_path, "s", "---\nname: s\ndescription: |\n  Line one.\n  Line two.\n---\nBody")

    assert load_pack(tmp_path).skills[0].description == "Line one. Line two."


def test_skill_rejects_symlinked_references(tmp_path):
    write_rule(tmp_path, "rule.md", "Body.")
    skill_dir = write_skill(tmp_path, "eval-design", SKILL_MD, {"references/real.md": "x"})
    secret = tmp_path / "secret.md"
    secret.write_text("secret", encoding="utf-8")
    (skill_dir / "references" / "link.md").symlink_to(secret)

    with pytest.raises(PackError, match="symlinks are not allowed"):
        load_pack(tmp_path)


def test_load_pack_allows_skills_without_rules(tmp_path):
    write_skill(tmp_path, "eval-design", SKILL_MD)

    pack = load_pack(tmp_path)

    assert pack.rules == () and [skill.name for skill in pack.skills] == ["eval-design"]


@pytest.mark.parametrize(
    "glob",
    ["#tmp/*.py", "src/a #b", "a: b", "[abc]*.ts", "{a}*.ts", "!x", "&x", "%x", "@x", "|x", ">x",
     " src/**", "src/** ", "a b"],
)
def test_globs_reject_yaml_unsafe_values(glob):
    rule_file = f"---\nscope: glob\nglobs: {json.dumps([glob])}\n---\nBody"

    with pytest.raises(PackError, match="'globs' must be a list"):
        parse_rule(rule_file, SOURCE)


@pytest.mark.parametrize("glob", ["*.ts", "**/*.tsx", "src/[!_]*.py", "docs/**/*.md"])
def test_globs_accept_common_patterns(glob):
    rule_file = f"---\nscope: glob\nglobs: {json.dumps([glob])}\n---\nBody"

    assert parse_rule(rule_file, SOURCE).globs == (glob,)


def test_rule_reads_checks():
    text = (
        "---\nchecks:\n"
        "  - forbid: 'while True:'\n    message: loops need a cap\n"
        "  - run: uv run pytest -q 'tests/my agents'\n"
        "---\nBody"
    )

    assert parse_rule(text, SOURCE).checks == (
        ForbidCheck(pattern="while True:", message="loops need a cap"),
        RunCheck(command=("uv", "run", "pytest", "-q", "tests/my agents")),
    )


@pytest.mark.parametrize(
    ("checks", "message"),
    [
        ("checks: nope", "'checks' must be a list"),
        ("checks: [nope]", "check 1 must be a mapping"),
        ("checks: [{message: x}]", "check 1 needs exactly one of 'forbid' or 'run'"),
        ("checks: [{forbid: a, run: b}]", "check 1 needs exactly one of 'forbid' or 'run'"),
        ("checks: [{forbid: a, when: b}]", "check 1 has unknown key(s): when"),
        ("checks: [{forbid: '('}]", "check 1 has an invalid regex"),
        ("checks: [{forbid: ''}]", "check 1 'forbid' must be a non-empty string"),
        ("checks: [{run: \"echo 'open\"}]", "check 1 'run' can't be parsed"),
        ("checks: [{run: '  '}]", "check 1 'run' must be a non-empty string"),
        ("checks: [{forbid: a, message: 3}]", "check 1 'message' must be a string"),
    ],
)
def test_invalid_checks_raise(checks, message):
    with pytest.raises(PackError) as exc:
        parse_rule(f"---\n{checks}\n---\nBody", SOURCE)

    assert message in str(exc.value)


def test_globs_must_compile():
    with pytest.raises(PackError, match="invalid glob"):
        parse_rule("---\nscope: glob\nglobs: ['src/[z-a].py']\n---\nBody", SOURCE)


def test_rule_judge_flag_defaults_to_true_and_can_be_disabled():
    assert parse_rule("Body", SOURCE).judge is True
    assert parse_rule("---\njudge: false\n---\nBody", SOURCE).judge is False


def test_rule_judge_flag_must_be_boolean():
    with pytest.raises(PackError, match="'judge' must be true or false"):
        parse_rule("---\njudge: 'no'\n---\nBody", SOURCE)
