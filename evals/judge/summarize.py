"""Summarize judge calibration runs into RESULTS.md: agreement with labels, per provider and rule.

    uv run python evals/judge/summarize.py [--variant baseline] [--write-grades]

Fail is the positive class. Ambiguous labels (either verdict acceptable) are left out of the
fail-vs-not-fail metrics. Every number is computed from results.jsonl and errors.jsonl, and each
stored verdict is re-graded against the current labels in cases.yaml, so a label fix needs no rerun.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median

from cases import EVAL_DIR, load_cases

RUNS_DIR = EVAL_DIR / "runs"
OUTPUT = EVAL_DIR / "RESULTS.md"
# USD per 1M tokens: (input, output, cache read, cache write). Sources: the Claude API model table
# (cache read 0.1x, write 1.25x input) and OpenAI's pricing page (short context).
PRICES = {
    "claude-opus-5-5": (4.00, 20.00, 0.40, 5.00),
    "gpt-6.1-sol": (2.00, 10.00, 0.10, 2.00),
}


def wilson(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    if total == 0:
        return (math.nan, math.nan)
    p = successes / total
    centre = (p + z * z / (2 * total)) / (1 + z * z / total)
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / (1 + z * z / total)
    return centre - half, centre + half


def rate(successes: int, total: int) -> str:
    if total == 0:
        return "n/a (0 pairs)"
    lo, hi = wilson(successes, total)
    return f"{successes / total:.0%} ({successes}/{total}; 95% CI {lo:.0%}-{hi:.0%})"


def cost(row: dict) -> float | None:
    price = next((p for model, p in PRICES.items() if row.get("model", "").startswith(model)), None)
    if price is None:
        return None
    usage = row.get("usage", {})
    tokens = (
        usage.get("input_tokens", 0),
        usage.get("output_tokens", 0),
        usage.get("cache_read_input_tokens", 0),
        usage.get("cache_creation_input_tokens", 0),
    )
    return sum(count * unit for count, unit in zip(tokens, price)) / 1_000_000


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def regrade(rows: list[dict]) -> list[dict]:
    """Grade each stored verdict against the current labels (the runner's grades may be stale)."""
    labels = {(case.id, rule): verdicts for case in load_cases()
              for rule, verdicts in case.expected.items()}
    regraded = []
    for row in rows:
        expected = labels[(row["meta"]["case"], row["meta"]["rule"])]
        verdict = row["meta"]["verdict"]
        expected_fail, expected_ok = expected == {"fail"}, "fail" not in expected
        agree = int(verdict in expected)
        if expected_fail:
            fail_agree = int(verdict == "fail")
        elif expected_ok:
            fail_agree = int(verdict != "fail")
        else:
            fail_agree = agree
        label_class = "fail" if expected_fail else "not_fail" if expected_ok else "ambiguous"
        meta = {**row["meta"], "expected": sorted(expected), "label_class": label_class}
        regraded.append({**row, "grade": {"fail_agree": fail_agree, "agree": agree}, "meta": meta})
    return regraded


def summarize(provider: str, rows: list[dict], errors: list[dict]) -> list[str]:
    ok = [row for row in rows if row["status"] == "ok"]
    truncated = len(rows) - len(ok)
    by_class = defaultdict(list)
    for row in ok:
        by_class[row["meta"]["label_class"]].append(row)
    positives, negatives = by_class["fail"], by_class["not_fail"]
    tp = sum(row["meta"]["verdict"] == "fail" for row in positives)
    fp = sum(row["meta"]["verdict"] == "fail" for row in negatives)
    flagged = tp + fp
    unknown = sum(row["meta"]["verdict"] == "unknown" for row in ok)
    agree = sum(row["grade"]["agree"] for row in ok)

    pairs = defaultdict(set)
    for row in ok:
        pairs[row["prompt_id"]].add(row["meta"]["verdict"])
    repeated = [verdicts for pid, verdicts in pairs.items()
                if sum(r["prompt_id"] == pid for r in ok) > 1]
    stable = sum(len(verdicts) == 1 for verdicts in repeated)

    costs = [cost(row) for row in rows]
    known = [c for c in costs if c is not None]
    models = sorted({row.get("model", "") for row in rows})
    latencies = sorted(row["latency_s"] for row in ok)
    cases = {row["meta"]["case"] for row in rows}
    reps = max((row["rep"] for row in rows), default=-1) + 1

    lines = [
        f"## {provider}",
        "",
        f"Model: {', '.join(models) or 'none'} · {len(cases)} cases × {reps} reps · "
        f"{len(rows)} graded verdicts · {len(errors)} errors · {truncated} truncated",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| **Fail recall** (violations caught) | {rate(tp, len(positives))} |",
        f"| **False-fail rate** (non-violations failed) | {rate(fp, len(negatives))} |",
        f"| Fail precision | {rate(tp, flagged)} |",
        f"| Exact verdict agreement | {rate(agree, len(ok))} |",
        f"| Unknown verdicts | {rate(unknown, len(ok))} |",
        f"| Same verdict across reps | {rate(stable, len(repeated))} |",
        f"| Latency per verdict | median {median(latencies):.1f}s, max {latencies[-1]:.1f}s |"
        if latencies else "| Latency per verdict | not measured |",
        f"| Cost | ${sum(known):.2f} total, ${sum(known) / len(known):.4f} per verdict |"
        if known and len(known) == len(costs) else "| Cost | not measured (unknown model price) |",
        "",
        "| Rule | Caught | False fails | Exact agreement |",
        "|---|---|---|---|",
    ]
    for rule in sorted({row["meta"]["rule"] for row in ok}):
        mine = [row for row in ok if row["meta"]["rule"] == rule]
        pos = [r for r in mine if r["meta"]["label_class"] == "fail"]
        neg = [r for r in mine if r["meta"]["label_class"] == "not_fail"]
        caught = sum(r["meta"]["verdict"] == "fail" for r in pos)
        false = sum(r["meta"]["verdict"] == "fail" for r in neg)
        same = sum(r["grade"]["agree"] for r in mine)
        lines.append(f"| {rule} | {caught}/{len(pos)} | {false}/{len(neg)} | {same}/{len(mine)} |")

    misses = sorted(
        (row["meta"]["case"], row["meta"]["rule"], row["meta"]["verdict"],
         " or ".join(row["meta"]["expected"]))
        for row in ok if not row["grade"]["agree"]
    )
    if misses:
        lines += ["", "Disagreements (case · rule · verdict → expected):", ""]
        counted = Counter(misses)
        lines += [f"- {c} · {r} · {v} → {e}" + (f" (×{n})" if n > 1 else "")
                  for (c, r, v, e), n in sorted(counted.items())]
    if errors:
        lines += ["", "Errors: " + ", ".join(f"{k} ×{n}" for k, n in
                                             Counter(e["class"] for e in errors).items())]
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--variant", default="baseline")
    parser.add_argument("--write-grades", action="store_true",
                        help="store the regraded labels in results.jsonl so report.html matches")
    args = parser.parse_args(argv)
    sections = []
    for flow in sorted(path for path in RUNS_DIR.iterdir() if path.is_dir()):
        out = flow / args.variant
        rows, errors = regrade(load(out / "results.jsonl")), load(out / "errors.jsonl")
        if args.write_grades and rows:
            text = "".join(json.dumps(row) + "\n" for row in rows)
            (out / "results.jsonl").write_text(text)
        if rows or errors:
            sections += summarize(flow.name, rows, errors) + [""]
    if not sections:
        print("no runs found")
        return 1
    header = [
        "# Judge calibration results",
        "",
        f"Variant `{args.variant}`. Generated by `evals/judge/summarize.py`; labels in "
        "`cases.yaml` (human-reviewed). Fail is the positive class; ambiguous labels are left "
        "out of recall, false-fail rate, and precision.",
        "",
    ]
    OUTPUT.write_text("\n".join(header + sections))
    print("\n".join(sections))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
