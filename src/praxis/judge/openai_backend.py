"""OpenAI models via the OpenAI SDK's Responses API (``praxis-agents[judge-openai]``)."""

from __future__ import annotations

from typing import Any

from praxis.judge import (
    DEFAULT_EFFORT,
    MAX_OUTPUT_TOKENS,
    VERDICT_SCHEMA,
    Completion,
    JudgeError,
    JudgeRequest,
)

DEFAULT_MODEL = "gpt-6.1-sol"


class OpenAIBackend:
    provider = "openai"

    def __init__(
        self, client: Any = None, model: str | None = None, effort: str = DEFAULT_EFFORT
    ) -> None:
        self._client = client if client is not None else _default_client()
        self.model = model or DEFAULT_MODEL
        self._effort = effort

    def input_tokens(self, request: JudgeRequest) -> int:
        counted = _call(
            self._client.responses.input_tokens.count,
            model=self.model,
            instructions=request.system,
            input=self._input(request),
        )
        return counted.input_tokens

    def complete(self, request: JudgeRequest) -> Completion:
        response = _call(
            self._client.responses.create,
            model=self.model,
            instructions=request.system,
            input=self._input(request),
            text={
                "format": {
                    "type": "json_schema",
                    "name": "verdict",
                    "schema": VERDICT_SCHEMA,
                    "strict": True,
                }
            },
            reasoning={"effort": self._effort},
            max_output_tokens=MAX_OUTPUT_TOKENS,
            # Same key for every request in a run, so OpenAI's automatic prefix cache is reused.
            prompt_cache_key=request.cache_key,
        )
        if _refused(response):
            return Completion("", "refused")
        if getattr(response, "status", None) == "incomplete":
            details = getattr(response, "incomplete_details", None)
            reason = getattr(details, "reason", None)
            return Completion("", "refused" if reason == "content_filter" else "truncated")
        return Completion(getattr(response, "output_text", "") or "")

    @staticmethod
    def _input(request: JudgeRequest) -> list[dict[str, Any]]:
        return [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": request.diff_text},
                    {"type": "input_text", "text": request.rule_text},
                ],
            }
        ]


def _refused(response: Any) -> bool:
    return any(
        getattr(item, "type", None) == "refusal"
        for output in getattr(response, "output", None) or []
        if getattr(output, "type", None) == "message"
        for item in getattr(output, "content", None) or []
    )


def _call(method: Any, **kwargs: Any) -> Any:
    try:
        return method(**kwargs)
    except _api_errors() as exc:  # the SDK already retried 429s, 5xx, and timeouts
        raise JudgeError(f"judge request failed: {exc}") from exc


def _api_errors() -> tuple[type[BaseException], ...]:
    try:
        import openai
    except ImportError:  # an injected client without the SDK; let its errors propagate
        return ()
    return (openai.APIError,)


def _default_client() -> Any:
    try:
        import openai
    except ImportError as exc:
        raise JudgeError(
            "the OpenAI judge needs the OpenAI SDK: install praxis-agents[judge-openai] "
            "(or `uv sync --extra judge-openai` in a checkout)"
        ) from exc
    return openai.OpenAI()
