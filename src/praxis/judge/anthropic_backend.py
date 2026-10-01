"""Claude via the Anthropic SDK (``praxis-agents[judge]``)."""

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

DEFAULT_MODEL = "claude-opus-5-5"
# Server-side refusal fallback: a declined request is retried on a model chosen by category.
FALLBACK_BETA = "server-side-fallback-2026-07-01"


class AnthropicBackend:
    provider = "anthropic"

    def __init__(
        self, client: Any = None, model: str | None = None, effort: str = DEFAULT_EFFORT
    ) -> None:
        self._client = client if client is not None else _default_client()
        self.model = model or DEFAULT_MODEL
        self._effort = effort

    def input_tokens(self, request: JudgeRequest) -> int:
        counted = _call(
            self._client.messages.count_tokens,
            model=self.model,
            system=request.system,
            messages=self._messages(request),
        )
        return counted.input_tokens

    def complete(self, request: JudgeRequest) -> Completion:
        response = _call(
            self._client.beta.messages.create,
            model=self.model,
            max_tokens=MAX_OUTPUT_TOKENS,
            system=request.system,
            messages=self._messages(request),
            output_config={
                "effort": self._effort,
                "format": {"type": "json_schema", "schema": VERDICT_SCHEMA},
            },
            betas=[FALLBACK_BETA],
            fallbacks="default",
        )
        meta = {"model": getattr(response, "model", "") or "", "usage": _usage(response)}
        stop_reason = getattr(response, "stop_reason", None)
        if stop_reason == "refusal":
            return Completion("", "refused", **meta)
        if stop_reason == "max_tokens":
            return Completion("", "truncated", **meta)
        blocks = getattr(response, "content", None) or []
        texts = (getattr(b, "text", "") for b in blocks if getattr(b, "type", "") == "text")
        return Completion(next(texts, ""), **meta)

    @staticmethod
    def _messages(request: JudgeRequest) -> list[dict[str, Any]]:
        # The diff block carries the cache breakpoint: system + diff are shared by every rule.
        return [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": request.diff_text,
                        "cache_control": {"type": "ephemeral"},
                    },
                    {"type": "text", "text": request.rule_text},
                ],
            }
        ]


def _usage(response: Any) -> dict[str, int]:
    usage = getattr(response, "usage", None)
    fields = (
        "input_tokens",
        "output_tokens",
        "cache_read_input_tokens",
        "cache_creation_input_tokens",
    )
    return {name: int(getattr(usage, name, 0) or 0) for name in fields} if usage else {}


def _call(method: Any, **kwargs: Any) -> Any:
    try:
        return method(**kwargs)
    except _api_errors() as exc:  # the SDK already retried 429s, 5xx, and timeouts
        raise JudgeError(f"judge request failed: {exc}") from exc


def _api_errors() -> tuple[type[BaseException], ...]:
    try:
        import anthropic
    except ImportError:  # an injected client without the SDK; let its errors propagate
        return ()
    return (anthropic.APIError,)


def _default_client() -> Any:
    try:
        import anthropic
    except ImportError as exc:
        raise JudgeError(
            "the Anthropic judge needs the Anthropic SDK: install praxis-agents[judge] "
            "(or `uv sync --extra judge` in a checkout)"
        ) from exc
    return anthropic.Anthropic()
