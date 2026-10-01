from pathlib import Path

import pytest
from conftest import git

from praxis.gitdiff import GitError, added_lines, parse_diff, unified_diff

DIFF = """\
diff --git a/src/loop.py b/src/loop.py
index 1111111..2222222 100644
--- a/src/loop.py
+++ b/src/loop.py
@@ -3,0 +4,2 @@ def run():
+    while True:
+        step()
@@ -10 +12 @@ def other():
-    old()
+    new()
diff --git a/img.png b/img.png
Binary files a/img.png and b/img.png differ
diff --git a/new.md b/new.md
new file mode 100644
--- /dev/null
+++ b/new.md
@@ -0,0 +1 @@
+hello
"""


def test_parse_diff_maps_added_lines_to_new_line_numbers():
    assert parse_diff(DIFF) == {
        "src/loop.py": ((4, "    while True:"), (5, "        step()"), (12, "    new()")),
        "new.md": ((1, "hello"),),
    }


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "keep.py").write_text("a = 1\n", encoding="utf-8")
    (tmp_path / "gone.py").write_text("x = 1\n", encoding="utf-8")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "base")
    return tmp_path


def test_added_lines_covers_commits_working_tree_and_untracked_files(repo):
    git(repo, "checkout", "-q", "-b", "feature")
    (repo / "keep.py").write_text("a = 1\nb = 2\n", encoding="utf-8")
    git(repo, "commit", "-q", "-am", "add b")
    (repo / "keep.py").write_text("a = 1\nb = 2\nc = 3\n", encoding="utf-8")
    (repo / "gone.py").unlink()
    (repo / "fresh.py").write_text("while True:\n    pass\n", encoding="utf-8")

    assert added_lines(repo, "main") == {
        "keep.py": ((2, "b = 2"), (3, "c = 3")),
        "fresh.py": ((1, "while True:"), (2, "    pass")),
    }


def test_added_lines_ignores_changes_already_on_base(repo):
    git(repo, "checkout", "-q", "-b", "feature")
    git(repo, "checkout", "-q", "main")
    (repo / "keep.py").write_text("a = 1\nmain_only = 1\n", encoding="utf-8")
    git(repo, "commit", "-q", "-am", "main moves on")
    git(repo, "checkout", "-q", "feature")

    assert added_lines(repo, "main") == {}


def test_added_lines_rejects_unknown_base(repo):
    with pytest.raises(GitError, match="unknown base 'nope'"):
        added_lines(repo, "nope")


def test_added_lines_requires_a_git_repository(tmp_path):
    with pytest.raises(GitError, match="not a git repository"):
        added_lines(tmp_path, "main")


def test_parse_diff_keeps_line_numbers_across_unusual_line_breaks():
    diff = (
        "diff --git a/a.txt b/a.txt\n--- a/a.txt\n+++ b/a.txt\n@@ -0,0 +1,2 @@\n"
        "+page\x0cbreak still one line\r\n+second\n"
    )

    assert parse_diff(diff) == {"a.txt": ((1, "page\x0cbreak still one line"), (2, "second"))}


def test_parse_diff_handles_spaced_and_quoted_paths():
    diff = (
        "diff --git a/my file.py b/my file.py\n--- a/my file.py\t\n+++ b/my file.py\t\n"
        "@@ -0,0 +1 @@\n+x\n"
        'diff --git "a/q\\"x.py" "b/q\\"x.py"\n--- "a/q\\"x.py"\n+++ "b/q\\"x.py"\n'
        "@@ -0,0 +1 @@\n+y\n"
        'diff --git "a/caf\\303\\251.py" "b/caf\\303\\251.py"\n+++ "b/caf\\303\\251.py"\n'
        "@@ -0,0 +1 @@\n+z\n"
    )

    assert parse_diff(diff) == {"my file.py": ((1, "x"),), 'q"x.py': ((1, "y"),), "café.py": ((1, "z"),)}


def test_added_lines_handles_real_spaced_and_quoted_paths(repo):
    git(repo, "checkout", "-q", "-b", "feature")
    for name in ("my file.py", 'q"x.py'):
        (repo / name).write_text("before\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "add")
    for name in ("my file.py", 'q"x.py'):
        (repo / name).write_text("before\nafter\n", encoding="utf-8")

    changes = added_lines(repo, "main")

    assert changes["my file.py"] == ((1, "before"), (2, "after"))
    assert changes['q"x.py'] == ((1, "before"), (2, "after"))


def test_added_lines_are_relative_to_a_project_root_below_the_git_top_level(repo):
    git(repo, "checkout", "-q", "-b", "feature")
    project = repo / "proj"
    (project / "src").mkdir(parents=True)
    (project / "src" / "a.py").write_text("inside\n", encoding="utf-8")
    (repo / "outside.py").write_text("outside\n", encoding="utf-8")
    (repo / "keep.py").write_text("a = 1\nchanged = 1\n", encoding="utf-8")

    assert added_lines(project, "main") == {"src/a.py": ((1, "inside"),)}


def test_added_lines_skips_large_untracked_files(repo, monkeypatch):
    monkeypatch.setattr("praxis.gitdiff.MAX_UNTRACKED_BYTES", 10)
    (repo / "small.txt").write_text("ok\n", encoding="utf-8")
    (repo / "big.txt").write_text("x" * 100 + "\n", encoding="utf-8")

    assert set(added_lines(repo, "main")) == {"small.txt"}


def test_unified_diff_has_context_untracked_files_and_exclusions(repo):
    git(repo, "checkout", "-q", "-b", "feature")
    (repo / "keep.py").write_text("a = 2\n", encoding="utf-8")
    (repo / "fresh.py").write_text("new = 1\n", encoding="utf-8")
    (repo / ".praxis").mkdir()
    (repo / ".praxis" / "rule.md").write_text("secret rule text\n", encoding="utf-8")
    (repo / "AGENTS.md").write_text("generated\n", encoding="utf-8")

    diff = unified_diff(repo, "main", exclude=(".praxis", "AGENTS.md"))

    assert "-a = 1" in diff and "+a = 2" in diff
    assert "+++ b/fresh.py" in diff and "+new = 1" in diff
    assert "secret rule text" not in diff and "generated" not in diff


def test_unified_diff_excludes_paths_literally(repo):
    git(repo, "checkout", "-q", "-b", "feature")
    for name in ("a*.py", "ab.py"):
        (repo / name).write_text("x = 1\n", encoding="utf-8")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "add")

    diff = unified_diff(repo, "main", exclude=("a*.py",))

    assert "b/ab.py" in diff and "b/a*.py" not in diff
