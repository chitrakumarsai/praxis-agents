"""Command-line entry point for the ``praxis`` command."""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from collections.abc import Sequence
from pathlib import Path

from praxis import __version__
from praxis.adapters import DEFAULT_TARGETS, TARGETS, resolve_targets
from praxis.bundled import available_packs, install_pack
from praxis.gitdiff import added_lines, unified_diff
from praxis.judge import DEFAULT_MODEL, Judge, Verdict, clean_text
from praxis.loader import load_pack
from praxis.sync import FileChange, apply, plan, plan_stale
from praxis.verify import RuleResult, exclude_paths, paths_in_scope, verify

DEFAULT_SOURCE = Path(".praxis")
DEFAULT_BASE = "main"
EXIT_OK, EXIT_STALE, EXIT_ERROR = 0, 1, 2
EXIT_FAILED = EXIT_STALE

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

    verify_help = "Run rule checks against lines added since the base branch; exit 1 on failure."
    verify_command = commands.add_parser("verify", help=verify_help, description=verify_help)
    _add_location_arguments(verify_command)
    verify_command.add_argument(
        "--base", default=DEFAULT_BASE, help=f"git ref to compare against (default: {DEFAULT_BASE})"
    )
    verify_command.add_argument(
        "--judge",
        action="store_true",
        help="also have Claude grade rules without checks (advisory; needs praxis-agents[judge])",
    )
    verify_command.add_argument(
        "--judge-model", help=f"judge model, with --judge (default: {DEFAULT_MODEL})"
    )
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
    if args.command == "verify" and args.judge_model and not args.judge:
        parser.error("--judge-model requires --judge")
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
    if args.command == "verify":
        judge_model = (args.judge_model or DEFAULT_MODEL) if args.judge else None
        return run_verify(args.root, args.source, args.base, judge_model)
    if args.command == "init":
        install_pack(args.pack, args.root / args.source)
        print(f"installed pack '{args.pack}' into {args.source}; run `praxis sync` next")
        return EXIT_OK

    changes = plan_changes(args.root, args.source, args.target)
    if args.command == "check":
        return report_check(changes)
    return report_sync(changes, apply(changes))


def _praxis_paths(source: Path) -> list[str]:
    """Rule sources and generated instruction files quote rule text; never check them."""
    generated = [
        path for target in TARGETS.values() for path in (*target.owned_dirs, *target.managed_paths)
    ]
    return [*([] if source.is_absolute() else [source.as_posix()]), *generated]


def run_verify(root: Path, source: Path, base: str, judge_model: str | None = None) -> int:
    """Run deterministic checks; with ``judge_model``, also run the advisory LLM judge."""
    excluded = _praxis_paths(source)
    pack = load_pack(root / source)
    changes = exclude_paths(added_lines(root, base), excluded)
    exit_code = report_verify(verify(pack, changes, root))
    if judge_model:
        rules = [rule for rule in pack.rules if not rule.checks]
        scope = {rule.id: paths_in_scope(rule, changes) for rule in rules}
        verdicts = Judge(model=judge_model).grade(rules, unified_diff(root, base, excluded), scope)
        report_judge(verdicts, len(rules), judge_model)
    return exit_code


def report_judge(verdicts: Sequence[Verdict], judged: int, model: str) -> None:
    for verdict in verdicts:
        if verdict.status in ("pass", "fail", "unknown"):
            print(f"JUDGE {verdict.status.upper()} {verdict.rule_id}")
            if verdict.status != "pass":
                for line in (verdict.explanation, *verdict.evidence):
                    print(f"  {clean_text(line)}")
    counts = Counter(verdict.status for verdict in verdicts)
    not_applicable = counts["not_applicable"] + judged - len(verdicts)
    print(
        f"judge ({model}, advisory): {counts['fail']} failed, {counts['pass']} passed, "
        f"{counts['unknown']} unknown, {not_applicable} not applicable"
    )


def report_verify(results: Sequence[RuleResult]) -> int:
    for result in results:
        if result.status == "skip":
            print(f"SKIP {result.rule_id} ({'; '.join(result.details)})")
        elif result.status in ("pass", "fail"):
            print(f"{result.status.upper()} {result.rule_id}")
            for detail in result.details:
                print("\n".join(f"  {line}" for line in detail.splitlines()))
    counts = Counter(result.status for result in results)
    print(
        f"{counts['fail']} failed, {counts['pass']} passed, {counts['skip']} skipped, "
        f"{counts['unchecked']} unchecked"
    )
    return EXIT_FAILED if counts["fail"] else EXIT_OK


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
