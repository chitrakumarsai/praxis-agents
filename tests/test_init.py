from pathlib import Path

import pytest

from praxis.init import DEFAULT_RULES_FILE, InitError, init
from praxis.rules import parse_file


def test_init_writes_parseable_starter(tmp_path: Path):
    path = init(tmp_path / DEFAULT_RULES_FILE)
    assert path.exists()
    rs = parse_file(path)
    assert rs.title == "Engineering standards"
    assert rs.metadata["name"] == "my-standards"
    assert [s.title for s in rs.sections] == ["Code style", "Testing", "Version control"]
    assert len(rs.all_rules()) == 6
    assert rs.sections[1].rules[0].details == ["Bug fixes start with a test that reproduces the bug."]


def test_init_into_directory(tmp_path: Path):
    assert init(tmp_path) == tmp_path / DEFAULT_RULES_FILE


def test_init_creates_parent_dirs(tmp_path: Path):
    path = init(tmp_path / "docs" / "rules.md")
    assert path.exists()


def test_init_refuses_to_overwrite(tmp_path: Path):
    path = tmp_path / "rules.md"
    path.write_text("mine", encoding="utf-8")
    with pytest.raises(InitError, match="already exists"):
        init(path)
    assert path.read_text(encoding="utf-8") == "mine"


def test_init_force_overwrites(tmp_path: Path):
    path = tmp_path / "rules.md"
    path.write_text("mine", encoding="utf-8")
    init(path, force=True)
    assert path.read_text(encoding="utf-8") != "mine"


def test_cli_init(tmp_path: Path, capsys):
    from praxis.cli import main

    target = tmp_path / "rules.md"
    assert main(["init", str(target)]) == 0
    assert target.exists()
    assert "Created" in capsys.readouterr().out

    assert main(["init", str(target)]) == 1
    assert "already exists" in capsys.readouterr().err

    assert main(["init", "--force", str(target)]) == 0
