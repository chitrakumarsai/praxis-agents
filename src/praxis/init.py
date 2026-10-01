"""`praxis init`: create a starter Markdown rules file."""

from __future__ import annotations

from pathlib import Path

DEFAULT_RULES_FILE = "PRAXIS.md"

STARTER_RULES = """\
---
name: my-standards
version: 1
---

# Engineering standards

These are the best practices every AI coding agent working in this repository
should follow. Headings group rules into sections, and each top-level bullet is
one rule. Indented lines and nested bullets add detail to the rule above them.

## Code style

- Follow the existing conventions of the file you are editing.
- Prefer clear names over comments that explain unclear names.

## Testing

- Add or update tests for every behavior change.
  - Bug fixes start with a test that reproduces the bug.
- Run the test suite before declaring work done.

## Version control

- Keep commits small and focused, with messages that explain why.
- Never commit secrets, credentials, or generated build output.
"""


class InitError(Exception):
    """Raised when the starter rules file cannot be created."""


def init(path: str | Path = DEFAULT_RULES_FILE, *, force: bool = False) -> Path:
    """Write the starter rules file to ``path`` and return its path.

    Refuses to overwrite an existing file unless ``force`` is true.
    """
    path = Path(path)
    if path.is_dir():
        path = path / DEFAULT_RULES_FILE
    if path.exists() and not force:
        raise InitError(f"{path} already exists (use --force to overwrite)")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(STARTER_RULES, encoding="utf-8")
    return path
