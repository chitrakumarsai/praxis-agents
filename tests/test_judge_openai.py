import json
import sys
from types import SimpleNamespace

import httpx2
import openai
import pytest

from praxis_agents.judge import Judge, JudgeError, make_backend
from praxis_agents.judge.openai_backend import DEFAULT_MODEL, OpenAIBackend
from praxis_agents.model import Rule

STATE = Rule(id="state", body="Keep state explicit.")
HANDOFF = Rule(id="human-handoff", body="Bind approval to the specific action.")
DIFF = "diff --git a/src/a.py b/src/a.py\n+++ b/src/a.py\n@@ -0,0 +1 @@\n+approved = True\n"
SCOPE = {"state": ["src/a.py"], "human-handoff": ["src/a.py"]}
PASS = {"status": "pass", "explanation": "fine", "evidence": ["src/a.py:1: approved = True"]}


def response(payload=PASS, status="completed", reason=None, refusal=False):
    text = json.dumps(payload)
    content = [SimpleNamespace(type="refusal", refusal="no")] if refusal else [
        SimpleNamespace(type="output_text", text=text)
    ]
    return SimpleNamespace(
        status=status,
        incomplete_details=SimpleNamespace(reason=reason) if reason else None,
        output=[SimpleNamespace(type="message", content=content)],
        output_text="" if refusal else text,
    )


class FakeOpenAI:
    def __init__(self, reply=None, input_tokens=1_000, error=None):
        self.calls, self.counted = [], []
        self.reply, self.error = reply or response(), error
        self.responses = SimpleNamespace(
            create=self._create,
            input_tokens=SimpleNamespace(count=self._count),
        )
        self.tokens = input_tokens

    def _create(self, **kwargs):
        if self.error:
            raise self.error
        self.calls.append(kwargs)
        return self.reply

    def _count(self, **kwargs):
        self.counted.append(kwargs)
        return SimpleNamespace(input_tokens=self.tokens)


def test_request_uses_strict_schema_effort_and_a_shared_cache_key():
    client = FakeOpenAI()

    Judge(OpenAIBackend(client=client)).grade((STATE, HANDOFF), DIFF, SCOPE)

    first, second = client.calls
    assert first["model"] == DEFAULT_MODEL
    assert first["text"]["format"]["type"] == "json_schema"
    assert first["text"]["format"]["strict"] is True
    assert first["reasoning"] == {"effort": "medium"}
    diff_part, rule_part = first["input"][0]["content"]
    assert DIFF in diff_part["text"] and 'id="state"' in rule_part["text"]
    assert first["instructions"] == second["instructions"]
    assert first["input"][0]["content"][0] == second["input"][0]["content"][0]
    assert first["prompt_cache_key"] == second["prompt_cache_key"]


def test_grounded_verdict_is_returned():
    (verdict,) = Judge(OpenAIBackend(client=FakeOpenAI())).grade((STATE,), DIFF, SCOPE)

    assert verdict.status == "pass" and verdict.evidence == ("src/a.py:1: approved = True",)


@pytest.mark.parametrize(
    ("reply", "explanation"),
    [
        (response(refusal=True), "declined"),
        (response(status="incomplete", reason="content_filter"), "declined"),
        (response(status="incomplete", reason="max_output_tokens"), "cut off"),
        (SimpleNamespace(), "invalid verdict"),
    ],
)
def test_refusals_and_incomplete_answers_become_unknown(reply, explanation):
    (verdict,) = Judge(OpenAIBackend(client=FakeOpenAI(reply))).grade((STATE,), DIFF, SCOPE)

    assert verdict.status == "unknown" and explanation in verdict.explanation


def test_large_inputs_are_counted_and_refused_over_the_limit(monkeypatch):
    monkeypatch.setattr("praxis_agents.judge.MAX_INPUT_TOKENS", 10)
    client = FakeOpenAI(input_tokens=10_000)

    with pytest.raises(JudgeError, match="over the judge's limit"):
        Judge(OpenAIBackend(client=client)).grade((STATE,), DIFF, SCOPE)

    assert client.counted and client.calls == []


def test_api_errors_become_judge_errors():
    error = openai.APIConnectionError(request=httpx2.Request("POST", "https://api.openai.com"))

    with pytest.raises(JudgeError, match="judge request failed"):
        Judge(OpenAIBackend(client=FakeOpenAI(error=error))).grade((STATE,), DIFF, SCOPE)


def test_missing_sdk_explains_how_to_install(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)

    with pytest.raises(JudgeError, match=r"praxis-agents\[judge-openai\]"):
        make_backend("openai")


def test_make_backend_rejects_unknown_providers():
    with pytest.raises(JudgeError, match="unknown judge provider 'gemini'"):
        make_backend("gemini")


def test_usage_reports_cached_input_separately():
    reply = response()
    reply.model = "gpt-6.1-sol"
    reply.usage = SimpleNamespace(
        input_tokens=1000, output_tokens=50, input_tokens_details=SimpleNamespace(cached_tokens=800)
    )

    (verdict,) = Judge(OpenAIBackend(client=FakeOpenAI(reply))).grade((STATE,), DIFF, SCOPE)

    assert verdict.model == "gpt-6.1-sol"
    assert verdict.usage["input_tokens"] == 200 and verdict.usage["cache_read_input_tokens"] == 800
