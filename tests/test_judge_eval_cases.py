"""Keep the judge calibration set (evals/judge) well-formed; no API calls."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "evals" / "judge"))

from cases import judged_rules, load_cases  # noqa: E402


def test_cases_load_with_valid_labels_and_nonempty_diffs():
    cases = load_cases()

    assert len(cases) >= 15
    assert all(case.diff.startswith("diff --git ") and case.paths for case in cases)
    assert len({case.id for case in cases}) == len(cases)


def test_every_judged_rule_has_fail_and_pass_examples():
    cases = load_cases()

    for rule in judged_rules():
        labels = [case.expected[rule.id] for case in cases]
        assert {"fail"} in labels, f"{rule.id} has no clear fail case"
        assert {"pass"} in labels, f"{rule.id} has no clear pass case"


def test_modified_files_produce_context_diffs():
    (typo,) = [case for case in load_cases() if case.id == "c16-readme-typo"]

    assert "-The support bot routs tickets" in typo.diff
    assert "+The support bot routes tickets" in typo.diff
    assert " # Support Bot" in typo.diff


# Oracle / null / error checks for the runner and grader, with no API calls.
import run  # noqa: E402
import summarize  # noqa: E402

from praxis.judge import Verdict  # noqa: E402


def _verdicts(case, pick):
    return tuple(pick(rule, expected) for rule, expected in sorted(case.expected.items()))


def _run_offline(tmp_path, pick, model="claude-opus-5-5"):
    for case in load_cases():
        run.record(tmp_path, case, 0, _verdicts(case, pick), model)
    return summarize.load(tmp_path / "results.jsonl"), summarize.load(tmp_path / "errors.jsonl")


def test_oracle_judge_scores_perfectly(tmp_path):
    def oracle(rule, expected):
        status = "fail" if expected == {"fail"} else sorted(expected)[0]
        return Verdict(rule, status, "oracle", model="claude-opus-5-5")

    rows, errors = _run_offline(tmp_path, oracle)

    assert not errors and len(rows) == 16 * 7
    assert all(row["grade"] == {"fail_agree": 1, "agree": 1} for row in rows)


def test_null_judge_catches_nothing(tmp_path):
    rows, _ = _run_offline(tmp_path, lambda rule, _: Verdict(rule, "unknown", "", model="claude-opus-5-5"))

    positives = [row for row in rows if row["meta"]["label_class"] == "fail"]
    assert positives and all(row["grade"]["fail_agree"] == 0 for row in positives)
    assert all(row["grade"]["agree"] == 0 for row in rows)


def test_always_fail_judge_is_caught_by_false_fail_rate(tmp_path):
    rows, _ = _run_offline(tmp_path, lambda rule, _: Verdict(rule, "fail", "", model="claude-opus-5-5"))

    negatives = [row for row in rows if row["meta"]["label_class"] == "not_fail"]
    assert negatives and all(row["grade"]["fail_agree"] == 0 for row in negatives)


def test_request_failures_and_model_mismatch_go_to_errors_not_scores(tmp_path):
    def failing(rule, _):
        return Verdict(rule, "unknown", "judge request failed: overloaded", model="claude-opus-5-5")

    rows, errors = _run_offline(tmp_path, failing)
    assert rows == [] and errors and all(e["class"] == "harness-or-serving" for e in errors)

    mismatch = tmp_path / "mismatch"
    mismatch.mkdir()
    rows, errors = _run_offline(mismatch, lambda rule, _: Verdict(rule, "pass", "", model="claude-sonnet-5-5"))
    assert rows == [] and {e["class"] for e in errors} == {"served-model-mismatch"}


def test_summary_regrades_stored_verdicts_against_current_labels(tmp_path):
    def oracle(rule, expected):
        status = "fail" if expected == {"fail"} else sorted(expected)[0]
        return Verdict(rule, status, "oracle", model="claude-opus-5-5")

    rows, _ = _run_offline(tmp_path, oracle)
    stale = [{**row, "grade": {"fail_agree": 0, "agree": 0}} for row in rows]

    assert all(row["grade"] == {"fail_agree": 1, "agree": 1} for row in summarize.regrade(stale))
