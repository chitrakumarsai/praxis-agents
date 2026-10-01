"""Command-line entry point for the ``praxis`` command."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from praxis import __version__
from praxis.adapters import TARGETS, resolve_targets
from praxis.loader import load_pack
from praxis.sync import FileChange, apply, plan

DEFAULT_SOURCE = Path(".praxis")
EXIT_OK, EXIT_STALE, EXIT_ERROR = 0, 1, 2

COMMANDS = {
    "sync": "Write instruction files for each target.",
    "check": "Exit 1 if instruction files are out of date with the source.",
}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="praxis",
        description="Apply your Markdown engineering standards to AI coding agents.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")
    for name, help_text in COMMANDS.items():
        command = commands.add_parser(name, help=help_text, description=help_text)
        command.add_argument(
            "--root", type=Path, default=Path("."), help="project root (default: current directory)"
        )
        command.add_argument(
            "--source",
            type=Path,
            default=DEFAULT_SOURCE,
            help=f"source directory, relative to the root (default: {DEFAULT_SOURCE})",
        )
        command.add_argument(
            "--target",
            default=",".join(TARGETS),
            help=f"comma-separated targets: {', '.join(TARGETS)} (default: all)",
        )
    return parser


def plan_changes(root: Path, source: Path, target_list: str) -> tuple[FileChange, ...]:
    pack = load_pack(root / source)
    names = [name.strip() for name in target_list.split(",") if name.strip()]
    if not names:
        raise ValueError(f"no targets selected; expected one or more of {', '.join(TARGETS)}")
    outputs = [output for target in resolve_targets(names) for output in target.render(pack)]
    return plan(root, outputs)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_OK

    try:
        changes = plan_changes(args.root, args.source, args.target)
        if args.command == "check":
            return report_check(changes)
        written = apply(changes)
    except (ValueError, OSError) as exc:
        print(f"praxis: error: {exc}", file=sys.stderr)
        return EXIT_ERROR

    written_paths = set(written)
    for change in changes:
        if change.path in written_paths:
            print(f"wrote {change.relpath}")
    if not written:
        print("already up to date")
    return EXIT_OK


def report_check(changes: Sequence[FileChange]) -> int:
    stale = [change for change in changes if change.changed]
    for change in stale:
        print(f"out of date: {change.relpath}")
    if stale:
        print("run `praxis sync` to update")
        return EXIT_STALE
    print("up to date")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
