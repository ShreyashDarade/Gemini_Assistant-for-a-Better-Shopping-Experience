from unittest.mock import AsyncMock, MagicMock

import pytest
from google.genai import errors

from app.services.gemini_client import GeminiClient, _strip_code_fence


def test_strip_code_fence():
    assert _strip_code_fence('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert _strip_code_fence('{"a": 1}') == '{"a": 1}'


def _client(generate):
    c = GeminiClient()
    c._client = MagicMock()
    c._client.aio.models.generate_content = generate
    return c


async def test_generate_json_parses():
    resp = MagicMock(text='{"intent": "x"}')
    c = _client(AsyncMock(return_value=resp))
    assert await c.generate_json("p") == {"intent": "x"}


async def test_retries_transient_then_succeeds(monkeypatch):
    monkeypatch.setattr("tenacity.nap.time.sleep", lambda *_: None)
    monkeypatch.setattr("asyncio.sleep", AsyncMock())
    err = errors.ServerError(503, {"error": {"message": "busy"}})
    gen = AsyncMock(side_effect=[err, MagicMock(text="ok")])
    assert await _client(gen).generate("p") == "ok"
    assert gen.await_count == 2


async def test_does_not_retry_client_errors():
    err = errors.ClientError(400, {"error": {"message": "bad"}})
    gen = AsyncMock(side_effect=err)
    with pytest.raises(errors.ClientError):
        await _client(gen).generate("p")
    assert gen.await_count == 1
