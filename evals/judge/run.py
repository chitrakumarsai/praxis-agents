"""Run the LLM judge over the calibration cases and grade each verdict against its label.

    uv run --extra dev python evals/judge/run.py --provider anthropic [--reps 2] [--cases c01,c02]

Writes runs/<provider>/<variant>/results.jsonl (one row per case x rule x rep), traces/, and
errors.jsonl. The harness gate refuses to run until the harness files are approved with
--approve-harness (a change to the runner, cases, labels, or judge requires re-approval).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as CaseTimeout
from pathlib import Path

from cases import EVAL_DIR, Case, judged_rules, load_cases

from praxis_agents.judge import PROVIDERS, Judge, JudgeError, Verdict, make_backend

REPO = EVAL_DIR.parent.parent
RUNS_DIR = EVAL_DIR / "runs"
VARIANT_NAME = re.compile(r"^(baseline|v[1-9][0-9]*)$")
HARNESS_GLOBS = ("evals/judge/*.py", "evals/judge/cases.yaml", "evals/judge/cases/**/*",
                 "src/praxis_agents/judge/*.py")
METRICS = [
    {"id": "fail_agree", "label": "fail vs not", "kind": "binary"},
    {"id": "agree", "label": "exact verdict", "kind": "binary"},
]
PERF_FIELDS = [
    {"id": "latency_s", "label": "latency", "unit": "s"},
    {"id": "in_tokens", "label": "in tok"},
    {"id": "out_tokens", "label": "out tok"},
]
REQUEST_FAILED = "judge request failed"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    flow = RUNS_DIR / args.provider
    if not gate(flow, args.approve_harness):
        return 2
    out = flow / args.variant
    (out / "traces").mkdir(parents=True, exist_ok=True)

    rules = judged_rules()
    cases = select(load_cases(), args.cases)
    done = finished(out / "results.jsonl", len(rules))
    todo = [(case, rep) for case in cases for rep in range(args.reps) if (case.id, rep) not in done]
    print(f"{args.provider}: {len(todo)} case-reps to run ({len(done)} already done)")

    backend = make_backend(args.provider, args.model)
    judge = Judge(backend)
    with ThreadPoolExecutor(max_workers=args.concurrency) as pool:
        futures = [(case, rep, pool.submit(judge.grade, rules, case.diff, scope(case, rules)))
                   for case, rep in todo]
        for case, rep, future in futures:
            try:
                verdicts = future.result(timeout=args.timeout_s)
            except CaseTimeout:
                record_error(out, case, rep, "timeout", f"no result within {args.timeout_s}s")
                continue
            except JudgeError as exc:
                record_error(out, case, rep, "harness-or-serving", str(exc))
                continue
            record(out, case, rep, verdicts, backend.model)
    print(f"wrote {out.relative_to(REPO)}")
    return 0


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--provider", choices=PROVIDERS, required=True)
    parser.add_argument("--model", help="judge model (default: the provider's default)")
    parser.add_argument("--variant", default="baseline")
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--cases", help="comma-separated case ids or prefixes (default: all)")
    parser.add_argument("--timeout-s", type=float, default=600, help="wall-clock ceiling per case")
    parser.add_argument("--concurrency", type=int, default=2, help="cases in flight at once")
    parser.add_argument("--approve-harness", action="store_true",
                        help="record the current harness files as approved (the owner's call)")
    args = parser.parse_args(argv)
    if not VARIANT_NAME.match(args.variant):
        parser.error("--variant must be 'baseline' or v<N> (the report builder ignores others)")
    return args


def gate(flow: Path, approve: bool) -> bool:
    """Refuse to run on harness files the owner hasn't approved."""
    state_path = flow / "_state.json"
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    digest = harness_digest()
    if approve:
        flow.mkdir(parents=True, exist_ok=True)
        state.update(metrics=METRICS, perf_fields=PERF_FIELDS, harness_sha=digest)
        state_path.write_text(json.dumps(state, indent=2) + "\n")
        print(f"approved harness {digest[:12]} for {flow.relative_to(REPO)}")
        return True
    if state.get("harness_sha") != digest:
        print(
            f"harness files changed or not yet approved (sha {digest[:12]}); review them, then "
            "rerun with --approve-harness",
            file=sys.stderr,
        )
        return False
    return True


def harness_digest() -> str:
    hasher = hashlib.sha256()
    paths = sorted({p for pattern in HARNESS_GLOBS for p in REPO.glob(pattern) if p.is_file()})
    for path in paths:
        hasher.update(path.relative_to(REPO).as_posix().encode())
        hasher.update(hashlib.sha256(path.read_bytes()).digest())
    return hasher.hexdigest()


def select(cases: list[Case], wanted: str | None) -> list[Case]:
    if not wanted:
        return cases
    prefixes = [item.strip() for item in wanted.split(",") if item.strip()]
    chosen = [case for case in cases if any(case.id.startswith(p) for p in prefixes)]
    if not chosen:
        raise SystemExit(f"no cases match {wanted!r}")
    return chosen


def scope(case: Case, rules) -> dict[str, list[str]]:
    # The bundled pack's judged rules are all always-on, so every changed file is in scope.
    return {rule.id: list(case.paths) for rule in rules}


def finished(results: Path, rules_per_case: int) -> set[tuple[str, int]]:
    """(case, rep) keys whose rows are all present, so a restart skips exactly those."""
    counts: dict[tuple[str, int], int] = {}
    if results.exists():
        for line in results.read_text().splitlines():
            row = json.loads(line)
            key = (row["meta"]["case"], row["rep"])
            counts[key] = counts.get(key, 0) + 1
    return {key for key, count in counts.items() if count == rules_per_case}


def record(out: Path, case: Case, rep: int, verdicts: tuple[Verdict, ...], model: str) -> None:
    """Write one row per rule, or error rows for verdicts that never got a usable answer."""
    by_rule = {verdict.rule_id: verdict for verdict in verdicts}
    rows, errors = [], []
    for rule_id, expected in sorted(case.expected.items()):
        verdict = by_rule.get(rule_id)
        if verdict is None:
            errors.append((rule_id, "harness-or-serving", "no verdict returned"))
        elif verdict.explanation.startswith(REQUEST_FAILED):
            errors.append((rule_id, "harness-or-serving", verdict.explanation))
        elif verdict.model and not verdict.model.startswith(model):
            errors.append((rule_id, "served-model-mismatch", f"asked {model}, got {verdict.model}"))
        else:
            rows.append(result_row(case, rep, rule_id, expected, verdict))
    if errors:  # keep the (case, rep) slot open so a resume reruns it whole
        for rule_id, cls, detail in errors:
            append(out / "errors.jsonl", {"case": case.id, "rule": rule_id, "rep": rep,
                                          "class": cls, "detail": detail})
        return
    (out / "traces").mkdir(parents=True, exist_ok=True)
    for row, trace in rows:
        (out / "traces" / f"{row['prompt_id']}_rep{rep}.json").write_text(json.dumps(trace, indent=2))
        append(out / "results.jsonl", row)


def result_row(case: Case, rep: int, rule_id: str, expected, verdict: Verdict):
    expected_fail, expected_ok = expected == {"fail"}, "fail" not in expected
    predicted_fail = verdict.status == "fail"
    agree = int(verdict.status in expected)
    if expected_fail:
        fail_agree = int(predicted_fail)
    elif expected_ok:
        fail_agree = int(not predicted_fail)
    else:  # ambiguous label: either verdict is acceptable
        fail_agree = agree
    truncated = verdict.status == "unknown" and "cut off" in verdict.explanation
    prompt_id = f"{case.id}__{rule_id}"
    row = {
        "prompt_id": prompt_id,
        "prompt": f"{case.title}\n\nRule: {rule_id}",
        "tags": [rule_id, *case.tags],
        "rep": rep,
        "status": "truncated" if truncated else "ok",
        "stop_reason": "max_tokens" if truncated else "end_turn",
        "grade": {"fail_agree": fail_agree, "agree": agree},
        "explanation": {"agree": verdict.explanation},
        "model": verdict.model,
        "usage": dict(verdict.usage),
        "latency_s": verdict.latency_s,
        "in_tokens": verdict.usage.get("input_tokens", 0)
        + verdict.usage.get("cache_read_input_tokens", 0)
        + verdict.usage.get("cache_creation_input_tokens", 0),
        "out_tokens": verdict.usage.get("output_tokens", 0),
        "meta": {
            "case": case.id,
            "rule": rule_id,
            "expected": sorted(expected),
            "verdict": verdict.status,
            "evidence": list(verdict.evidence),
            "label_class": "fail" if expected_fail else "not_fail" if expected_ok else "ambiguous",
        },
    }
    trace = [
        {"role": "user", "content": f"Rule: {rule_id}\n\n```diff\n{case.diff}```"},
        {"role": "assistant", "content": json.dumps(
            {"status": verdict.status, "explanation": verdict.explanation,
             "evidence": list(verdict.evidence)}, indent=2)},
    ]
    return row, trace


def record_error(out: Path, case: Case, rep: int, cls: str, detail: str) -> None:
    append(out / "errors.jsonl", {"case": case.id, "rule": None, "rep": rep, "class": cls,
                                  "detail": detail})
    print(f"  error {case.id} rep {rep}: {cls}: {detail}", file=sys.stderr)


def append(path: Path, row: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row) + "\n")


if __name__ == "__main__":
    raise SystemExit(main())
