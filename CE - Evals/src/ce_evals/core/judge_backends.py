"""Multi-provider judge backends for LLM-as-a-Judge evaluation."""

from __future__ import annotations

from typing import Protocol

from ce_evals.config import get_settings


class JudgeBackend(Protocol):
    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str,
        temperature: float = 0.0,
    ) -> tuple[str, int, int]:
        """Return (raw_text, input_tokens, output_tokens)."""
        ...


class AnthropicBackend:
    def __init__(self) -> None:
        import anthropic
        self._client = anthropic.Anthropic(api_key=get_settings().anthropic_api_key)

    def call(
        self, system_prompt: str, user_prompt: str, model: str, temperature: float = 0.0
    ) -> tuple[str, int, int]:
        resp = self._client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return resp.content[0].text, resp.usage.input_tokens, resp.usage.output_tokens


class OpenAIBackend:
    def __init__(self) -> None:
        import openai
        self._client = openai.OpenAI(api_key=get_settings().openai_api_key)

    def call(
        self, system_prompt: str, user_prompt: str, model: str, temperature: float = 0.0
    ) -> tuple[str, int, int]:
        kwargs: dict = dict(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        if model.startswith(("o1", "o3", "o4")):
            kwargs["reasoning_effort"] = "high"
        else:
            kwargs["temperature"] = temperature
        resp = self._client.chat.completions.create(**kwargs)
        usage = resp.usage
        return (
            resp.choices[0].message.content,
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )


class GeminiBackend:
    def __init__(self) -> None:
        from google import genai
        self._client = genai.Client(api_key=get_settings().google_api_key)

    def call(
        self, system_prompt: str, user_prompt: str, model: str, temperature: float = 0.0
    ) -> tuple[str, int, int]:
        from google.genai import types

        resp = self._client.models.generate_content(
            model=model,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=temperature,
                thinking_config=types.ThinkingConfig(thinking_budget=8192),
            ),
        )
        usage = resp.usage_metadata
        return (
            resp.text,
            usage.prompt_token_count if usage else 0,
            usage.candidates_token_count if usage else 0,
        )


def get_backend(model: str) -> JudgeBackend:
    """Return the appropriate backend for a model ID."""
    if model.startswith("claude"):
        return AnthropicBackend()
    if model.startswith(("gpt-", "o1-", "o3-", "o4-", "gpt-5")):
        return OpenAIBackend()
    if model.startswith("gemini"):
        return GeminiBackend()
    raise ValueError(f"Unknown model prefix for backend routing: {model}")
