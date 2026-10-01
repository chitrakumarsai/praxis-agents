"""Match POSIX paths against gitignore-style globs (``**`` spans directories, ``*`` doesn't)."""

from __future__ import annotations

import re
from collections.abc import Iterable
from functools import lru_cache


def matches(path: str, globs: Iterable[str]) -> bool:
    """True if ``path`` (POSIX, relative to the project root) matches any of ``globs``."""
    return any(compile_glob(glob).fullmatch(path) for glob in globs)


@lru_cache(maxsize=None)
def compile_glob(glob: str) -> re.Pattern[str]:
    """Compile ``glob`` to a regex; raises ``re.error`` for an invalid one such as ``[z-a]``."""
    return re.compile(_translate(glob))


def _translate(glob: str) -> str:
    parts = []
    index = 0
    while index < len(glob):
        if glob.startswith("**/", index):
            parts.append("(?:.*/)?")  # zero or more directories
            index += 3
        elif glob.startswith("**", index):
            parts.append(".*")
            index += 2
        elif glob[index] == "*":
            parts.append("[^/]*")
            index += 1
        elif glob[index] == "?":
            parts.append("[^/]")
            index += 1
        elif glob[index] == "[" and (end := glob.find("]", index + 2)) != -1:
            content = glob[index + 1 : end].replace("\\", "\\\\")
            if content.startswith("!"):
                content = "^" + content[1:]
            parts.append(f"[{content}]")
            index = end + 1
        else:
            parts.append(re.escape(glob[index]))
            index += 1
    return "".join(parts)
