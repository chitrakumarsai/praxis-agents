"""Command-line entry point for the ``praxis`` command."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from praxis import __version__
from praxis.adapters import DEFAULT_TARGETS, TARGETS, resolve_targets
from praxis.bundled import available_packs, install_pack
from praxis.loader import load_pack
from praxis.sync import FileChange, apply, plan, plan_stale

DEFAULT_SOURCE = Path(".praxis")
EXIT_OK, EXIT_STALE, EXIT_ERROR = 0, 1, 2

COMPILE_COMMANDS = {
    "sync": "Write instruction files and skills for each target.",
    "check": "Exit 1 if generated files are out of date with the source.",
}


def _add_location_arguments(command: argparse.ArgumentParser) -> None:
    command.add_argument(
        "--root", type=Path, default=Path("."), help="project root (default: current directory)"
    )
    command.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_SOURCE,
        help=f"source directory, relative to the root (default: {DEFAULT_SOURCE})",
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="praxis",
        description="Apply your Markdown engineering standards to AI coding agents.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")

    for name, help_text in COMPILE_COMMANDS.items():
        command = commands.add_parser(name, help=help_text, description=help_text)
        _add_location_arguments(command)
        command.add_argument(
            "--target",
            default=",".join(DEFAULT_TARGETS),
            help=f"comma-separated targets: {', '.join(TARGETS)} "
            f"(default: {','.join(DEFAULT_TARGETS)})",
        )

    init_help = "Copy a bundled pack into the source directory."
    init = commands.add_parser("init", help=init_help, description=init_help)
    init.add_argument("pack", help="pack name (see `praxis packs`)")
    _add_location_arguments(init)

    packs_help = "List bundled packs."
    commands.add_parser("packs", help=packs_help, description=packs_help)
    return parser


def plan_changes(root: Path, source: Path, target_list: str) -> tuple[FileChange, ...]:
    pack = load_pack(root / source)
    names = [name.strip() for name in target_list.split(",") if name.strip()]
    if not names:
        raise ValueError(f"no targets selected; expected one or more of {', '.join(TARGETS)}")
    targets = resolve_targets(names)
    outputs = [output for target in targets for output in target.render(pack)]
    stale = plan_stale(
        root,
        outputs,
        owned_dirs=[owned for target in targets for owned in target.owned_dirs],
        managed_paths=[path for target in targets for path in target.managed_paths],
    )
    return (*plan(root, outputs), *stale)


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return EXIT_OK

    try:
        return run_command(args)
    except (ValueError, OSError) as exc:
        print(f"praxis: error: {exc}", file=sys.stderr)
        return EXIT_ERROR


def run_command(args: argparse.Namespace) -> int:
    if args.command == "packs":
        print("\n".join(available_packs()))
        return EXIT_OK
    if args.command == "init":
        install_pack(args.pack, args.root / args.source)
        print(f"installed pack '{args.pack}' into {args.source}; run `praxis sync` next")
        return EXIT_OK

    changes = plan_changes(args.root, args.source, args.target)
    if args.command == "check":
        return report_check(changes)
    return report_sync(changes, apply(changes))


def report_sync(changes: Sequence[FileChange], written: Sequence[Path]) -> int:
    written_paths = set(written)
    for change in changes:
        if change.path in written_paths:
            print(f"{'removed' if change.deleted else 'wrote'} {change.relpath}")
    if not written:
        print("already up to date")
    return EXIT_OK


def report_check(changes: Sequence[FileChange]) -> int:
    stale = [change for change in changes if change.changed]
    for change in stale:
        print(f"{'stale' if change.deleted else 'out of date'}: {change.relpath}")
    if stale:
        print("run `praxis sync` to update")
        return EXIT_STALE
    print("up to date")
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
