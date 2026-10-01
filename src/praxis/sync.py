"""Write each target tool's instruction file from a parsed rule set."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .adapters import RuleSet, get_adapter


@dataclass(frozen=True)
class SyncResult:
    target: str
    path: Path
    changed: bool


def parse_targets(value: str | Iterable[str]) -> list[str]:
    """Split ``"claude,codex"`` (or a list of such strings) into target names.

    Validates every name and drops duplicates, keeping the first occurrence.
    """
    items = [value] if isinstance(value, str) else list(value)
    targets: list[str] = []
    for item in items:
        for name in item.split(","):
            name = name.strip().lower()
            if name and name not in targets:
                get_adapter(name)  # raises ValueError for unknown targets
                targets.append(name)
    if not targets:
        raise ValueError("No sync targets given.")
    return targets


def sync(
    ruleset: RuleSet,
    targets: str | Iterable[str],
    root: str | Path = ".",
    *,
    dry_run: bool = False,
) -> list[SyncResult]:
    """Render ``ruleset`` for each target and write the files under ``root``.

    Files whose contents already match are left untouched. With ``dry_run``,
    nothing is written but the results still report what would change.
    """
    root = Path(root)
    results = []
    for name in parse_targets(targets):
        adapter = get_adapter(name)
        path = root / adapter.filename
        content = adapter.render(ruleset)
        current = path.read_text(encoding="utf-8") if path.exists() else None
        changed = current != content
        if changed and not dry_run:
            path.write_text(content, encoding="utf-8")
        results.append(SyncResult(target=name, path=path, changed=changed))
    return results
