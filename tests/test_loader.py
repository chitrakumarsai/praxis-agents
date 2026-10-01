from pathlib import Path

import pytest

from praxis.loader import PackError, load_pack, parse_rule
from praxis.model import Rule

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


def test_load_pack_requires_rules_directory(tmp_path):
    with pytest.raises(PackError, match="rules directory not found"):
        load_pack(tmp_path)


@pytest.mark.parametrize("marker", ["<!-- praxis:begin -->", "<!-- praxis:end -->"])
def test_rule_body_cannot_contain_praxis_markers(marker):
    with pytest.raises(PackError, match="must not contain praxis markers"):
        parse_rule(f"Docs mention {marker} here.", SOURCE)


def test_non_string_frontmatter_keys_raise_pack_error():
    with pytest.raises(PackError, match="unknown frontmatter key"):
        parse_rule("---\n1: x\ntrue: y\n---\nBody", SOURCE)


@pytest.mark.parametrize("yaml_glob", ['"src/`x`/*.py"', '"a\\nb"'])
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
