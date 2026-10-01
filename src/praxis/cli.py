"""Command-line entry point for the ``praxis`` command."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from praxis import __version__
from praxis.adapters import available_targets
from praxis.init import DEFAULT_RULES_FILE, InitError, init
from praxis.rules import parse_file
from praxis.sync import parse_targets, sync


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="praxis",
        description="Apply your Markdown engineering standards to AI coding agents.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")

    init_parser = commands.add_parser("init", help="create a starter Markdown rules file")
    init_parser.add_argument(
        "path",
        nargs="?",
        default=DEFAULT_RULES_FILE,
        help=f"file or directory to create it in (default: {DEFAULT_RULES_FILE})",
    )
    init_parser.add_argument(
        "-f", "--force", action="store_true", help="overwrite an existing file"
    )

    sync_parser = commands.add_parser(
        "sync", help="write each tool's instruction file from your rules"
    )
    sync_parser.add_argument(
        "rules",
        nargs="?",
        default=DEFAULT_RULES_FILE,
        help=f"rules file to read (default: {DEFAULT_RULES_FILE})",
    )
    sync_parser.add_argument(
        "-t",
        "--target",
        action="append",
        help="comma-separated tools to sync, repeatable "
        f"(available: {', '.join(available_targets())}; default: all)",
    )
    sync_parser.add_argument(
        "-o",
        "--output-dir",
        help="directory to write files in (default: the rules file's directory)",
    )
    sync_parser.add_argument(
        "-n", "--dry-run", action="store_true", help="show what would change without writing"
    )
    return parser


def _run_sync(args: argparse.Namespace) -> int:
    try:
        targets = parse_targets(args.target or available_targets())
        ruleset = parse_file(args.rules)
    except FileNotFoundError:
        print(
            f"praxis sync: {args.rules} not found (run `praxis init` to create it)",
            file=sys.stderr,
        )
        return 1
    except ValueError as exc:  # includes RulesParseError
        print(f"praxis sync: {exc}", file=sys.stderr)
        return 1
    root = args.output_dir or ruleset.source.parent
    for result in sync(ruleset, targets, root, dry_run=args.dry_run):
        if not result.changed:
            status = "Up to date"
        elif args.dry_run:
            status = "Would write"
        else:
            status = "Wrote"
        print(f"{status} {result.path} ({result.target})")
    return 0


def _run_init(args: argparse.Namespace) -> int:
    try:
        path = init(args.path, force=args.force)
    except InitError as exc:
        print(f"praxis init: {exc}", file=sys.stderr)
        return 1
    print(f"Created {path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "init":
        return _run_init(args)
    if args.command == "sync":
        return _run_sync(args)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
