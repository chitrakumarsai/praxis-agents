"""Command-line entry point for the ``praxis`` command."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from praxis import __version__
from praxis.init import DEFAULT_RULES_FILE, InitError, init


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
    return parser


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
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
