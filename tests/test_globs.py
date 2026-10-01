import pytest

from praxis.globs import matches

CASES = [
    ("**/agents/**", "agents/loop.py", True),
    ("**/agents/**", "src/agents/loop.py", True),
    ("**/agents/**", "src/agents/deep/x.py", True),
    ("**/agents/**", "src/agentsx/loop.py", False),
    ("*.py", "loop.py", True),
    ("*.py", "src/loop.py", False),
    ("**/*.py", "loop.py", True),
    ("**/*.py", "src/a/loop.py", True),
    ("src/*.py", "src/a/loop.py", False),
    ("src/**/*.py", "src/loop.py", True),
    ("src/[!_]*.py", "src/loop.py", True),
    ("src/[!_]*.py", "src/_private.py", False),
    ("src/?.py", "src/a.py", True),
    ("src/?.py", "src/ab.py", False),
    ("docs/a+b.md", "docs/a+b.md", True),
]


@pytest.mark.parametrize(("glob", "path", "expected"), CASES)
def test_matches(glob, path, expected):
    assert matches(path, (glob,)) is expected


def test_matches_any_of_several_globs():
    assert matches("README.md", ("*.py", "*.md"))
    assert not matches("README.txt", ("*.py", "*.md"))
