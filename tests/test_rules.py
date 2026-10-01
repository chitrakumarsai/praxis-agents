from pathlib import Path

import pytest

from praxis.rules import RulesParseError, parse, parse_file, slugify


def test_title_description_and_sections():
    rs = parse(
        "# Standards\n"
        "\n"
        "Intro text.\n"
        "\n"
        "## Testing\n"
        "\n"
        "Why tests matter.\n"
        "\n"
        "- Write tests.\n"
        "- Run them.\n"
        "\n"
        "## Style\n"
        "- Be consistent.\n"
    )
    assert rs.title == "Standards"
    assert rs.description == "Intro text."
    assert [s.title for s in rs.sections] == ["Testing", "Style"]
    testing = rs.sections[0]
    assert testing.description == "Why tests matter."
    assert [r.text for r in testing.rules] == ["Write tests.", "Run them."]
    assert [r.text for r in rs.all_rules()] == ["Write tests.", "Run them.", "Be consistent."]


def test_nested_headings():
    rs = parse("# T\n## A\n- a1\n### B\n- b1\n## C\n- c1\n")
    a, c = rs.sections
    assert a.sections[0].title == "B"
    assert a.sections[0].level == 3
    assert [r.text for r in a.all_rules()] == ["a1", "b1"]
    assert c.rules[0].text == "c1"


def test_details_and_continuations():
    rs = parse(
        "## Testing\n"
        "- Write a test for every bug fix\n"
        "  that reproduces it first.\n"
        "  - Name it after the issue.\n"
        "    Keep it small.\n"
        "* Second rule\n"
    )
    first, second = rs.sections[0].rules
    assert first.text == "Write a test for every bug fix that reproduces it first."
    assert first.details == ["Name it after the issue. Keep it small."]
    assert second.text == "Second rule"


def test_numbered_list_items_are_rules():
    rs = parse("## Steps\n1. First\n2) Second\n")
    assert [r.text for r in rs.sections[0].rules] == ["First", "Second"]


def test_rules_before_any_section_belong_to_ruleset():
    rs = parse("- top-level rule\n# Title\n")
    assert rs.rules[0].text == "top-level rule"
    assert rs.title == "Title"


def test_code_fences_are_not_rules():
    rs = parse(
        "## Shell\n"
        "Example:\n"
        "```sh\n"
        "- not a rule\n"
        "# not a heading\n"
        "```\n"
        "- real rule\n"
    )
    section = rs.sections[0]
    assert [r.text for r in section.rules] == ["real rule"]
    assert "- not a rule" in section.description
    assert len(rs.sections) == 1


def test_unterminated_fence_raises():
    with pytest.raises(RulesParseError, match="code fence"):
        parse("```\n- x\n")


def test_frontmatter():
    rs = parse('---\nname: acme\nversion: "2"\n---\n# Acme\n- rule\n')
    assert rs.metadata == {"name": "acme", "version": "2"}
    assert rs.title == "Acme"


def test_frontmatter_errors():
    with pytest.raises(RulesParseError, match="closing"):
        parse("---\nname: x\n")
    with pytest.raises(RulesParseError, match="invalid frontmatter"):
        parse("---\nnot valid\n---\n")


def test_rule_ids_are_stable_and_unique():
    rs = parse("## Testing\n- Run tests.\n- Run tests.\n## Style\n- Run tests.\n")
    ids = [r.id for r in rs.all_rules()]
    assert ids == ["testing/run-tests", "testing/run-tests-2", "style/run-tests"]


def test_rule_line_numbers():
    rs = parse("# T\n\n## A\n- one\n\n- two\n")
    assert [r.line for r in rs.all_rules()] == [4, 6]


def test_paragraph_ends_rule():
    rs = parse("## A\n- rule\nA paragraph after the list.\n")
    section = rs.sections[0]
    assert section.rules[0].text == "rule"
    assert section.description == "A paragraph after the list."


def test_slugify():
    assert slugify("Use `pytest` **always**!") == "use-pytest-always"
    assert slugify("***") == "rule"


def test_parse_file(tmp_path: Path):
    path = tmp_path / "rules.md"
    path.write_text("# T\n- r\n", encoding="utf-8")
    rs = parse_file(path)
    assert rs.source == path
    assert rs.all_rules()[0].text == "r"


def test_empty_input():
    rs = parse("")
    assert rs.title == "" and rs.sections == [] and rs.all_rules() == []
