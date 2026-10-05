"""
Gemini client built on the official ``google-genai`` SDK.

Uses the SDK's native asyncio surface (``client.aio``), real system instructions,
native JSON mode, bounded concurrency, and tenacity-based retries with jittered
exponential backoff on transient errors only.
"""

import asyncio
import json
import logging
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from tenacity import (
    AsyncRetrying,
    retry_if_exception,
    stop_after_attempt,
    wait_random_exponential,
)

from app.config import get_settings

logger = logging.getLogger(__name__)

_TRANSIENT_STATUS = {408, 429, 500, 502, 503, 504}


def _is_transient(exc: BaseException) -> bool:
    if isinstance(exc, genai_errors.APIError):
        return exc.code in _TRANSIENT_STATUS
    return isinstance(exc, TimeoutError | ConnectionError)


def _strip_code_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.removesuffix("```")
    return text.strip()


class GeminiClient:
    """Async Gemini wrapper with concurrency limiting and retries."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client = genai.Client(
            api_key=self.settings.gemini_api_key.get_secret_value(),
            http_options=types.HttpOptions(timeout=self.settings.ai_timeout_seconds * 1000),
        )
        self._semaphore = asyncio.Semaphore(self.settings.ai_max_concurrency)
        logger.info("Gemini client initialized (model=%s)", self.settings.ai_model)

    def _config(
        self,
        system_instruction: str | None,
        temperature: float | None,
        max_tokens: int | None,
        json_mode: bool,
        schema: Any = None,
    ) -> types.GenerateContentConfig:
        return types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=self.settings.ai_temperature if temperature is None else temperature,
            max_output_tokens=max_tokens or self.settings.ai_max_tokens,
            response_mime_type="application/json" if json_mode else None,
            response_schema=schema if json_mode else None,
        )

    async def _call(self, contents: Any, config: types.GenerateContentConfig) -> str:
        async with self._semaphore:
            async for attempt in AsyncRetrying(
                retry=retry_if_exception(_is_transient),
                stop=stop_after_attempt(self.settings.ai_max_retries),
                wait=wait_random_exponential(multiplier=0.5, max=8),
                reraise=True,
            ):
                with attempt:
                    response = await self._client.aio.models.generate_content(
                        model=self.settings.ai_model, contents=contents, config=config
                    )
                    return (response.text or "").strip()
        raise RuntimeError("unreachable")  # pragma: no cover

    async def generate(
        self,
        prompt: str,
        system_instruction: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        response_format: str = "text",
    ) -> str:
        """Generate a text (or JSON string when ``response_format="json"``) response."""
        json_mode = response_format == "json"
        config = self._config(system_instruction, temperature, max_tokens, json_mode)
        text = await self._call(prompt, config)
        return _strip_code_fence(text) if json_mode else text

    async def generate_json(
        self,
        prompt: str,
        system_instruction: str | None = None,
        schema: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Generate and parse a JSON object response."""
        if schema:
            prompt = f"{prompt}\n\nExpected JSON schema: {json.dumps(schema)}"
        text = await self.generate(
            prompt, system_instruction=system_instruction, response_format="json"
        )
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            logger.error("Invalid JSON from model: %.500s", text)
            raise ValueError(f"Invalid JSON response from AI: {exc}") from exc

    async def generate_with_context(
        self, messages: list[dict[str, str]], system_instruction: str | None = None
    ) -> str:
        """Generate a reply from structured chat history (last 10 turns)."""
        contents = [
            types.Content(
                role="model" if m.get("role") == "assistant" else "user",
                parts=[types.Part.from_text(text=m.get("content", ""))],
            )
            for m in messages[-10:]
        ]
        config = self._config(system_instruction, None, None, False)
        return await self._call(contents, config)

    async def health_check(self) -> bool:
        try:
            return "OK" in (await self.generate("Respond with exactly: OK", max_tokens=16)).upper()
        except Exception:
            logger.exception("Gemini health check failed")
            return False

    async def aclose(self) -> None:
        await self._client.aio.aclose()


_client: GeminiClient | None = None


async def get_gemini_client() -> GeminiClient:
    """Return the process-wide client (created lazily; no await between check and set)."""
    global _client
    if _client is None:
        _client = GeminiClient()
    return _client


async def close_gemini_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
