"""Tests for the LLM client service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

import httpx
from openai import APIConnectionError

from talekeeper.services import llm_client
from talekeeper.services.llm_client import (
    health_check, generate, resolve_config, _is_ollama, unload_model, _ollama_cache,
)


@patch("talekeeper.services.llm_client._make_client")
async def test_health_check_success(mock_make):
    """health_check returns ok status when the LLM provider is reachable."""
    mock_client = AsyncMock()
    mock_make.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock()

    result = await health_check("http://test", None, "test-model")

    assert result == {"status": "ok"}
    mock_client.chat.completions.create.assert_awaited_once()


@patch("talekeeper.services.llm_client._make_client")
async def test_health_check_failure(mock_make):
    """health_check returns error status when the provider is unreachable."""
    mock_client = AsyncMock()
    mock_make.return_value = mock_client
    mock_client.chat.completions.create = AsyncMock(
        side_effect=APIConnectionError(request=MagicMock())
    )

    result = await health_check("http://test", None, "test-model")

    assert result["status"] == "error"
    assert "Cannot reach" in result["message"]


@patch("talekeeper.services.llm_client._is_ollama", new_callable=AsyncMock, return_value=False)
@patch("talekeeper.services.llm_client.AsyncOpenAI")
async def test_generate(MockOpenAI, mock_is_ollama):
    """generate returns the text content from the LLM response."""
    mock_client = AsyncMock()
    MockOpenAI.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="Generated text"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    result = await generate("http://test", None, "model", "prompt")

    assert result == "Generated text"
    mock_client.chat.completions.create.assert_awaited_once()


async def test_resolve_config(db):
    """resolve_config reads LLM settings from the database."""
    await db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("llm_base_url", "http://custom:1234/v1"),
    )
    await db.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?)",
        ("llm_model", "custom-model"),
    )
    await db.commit()

    config = await resolve_config()

    assert config["base_url"] == "http://custom:1234/v1"
    assert config["model"] == "custom-model"


# ---- Ollama detection tests (3.4) ----


@pytest.fixture(autouse=True)
def _clear_ollama_cache():
    """Clear the Ollama detection cache between tests."""
    _ollama_cache.clear()
    yield
    _ollama_cache.clear()


async def test_is_ollama_detects_ollama_endpoint():
    """_is_ollama returns True when /api/tags responds with a models list."""
    mock_response = httpx.Response(
        200,
        json={"models": [{"name": "llama3.1:8b"}]},
        request=httpx.Request("GET", "http://localhost:11434/api/tags"),
    )
    with patch("talekeeper.services.llm_client.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _is_ollama("http://localhost:11434/v1")

        assert result is True
        mock_client.get.assert_awaited_once_with("http://localhost:11434/api/tags")


async def test_is_ollama_returns_false_for_non_ollama():
    """_is_ollama returns False when /api/tags returns non-Ollama response."""
    mock_response = httpx.Response(
        404,
        text="Not Found",
        request=httpx.Request("GET", "http://openai.example.com/api/tags"),
    )
    with patch("talekeeper.services.llm_client.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(return_value=mock_response)

        result = await _is_ollama("http://openai.example.com/v1")

        assert result is False


async def test_is_ollama_returns_false_on_connection_error():
    """_is_ollama returns False when the endpoint is unreachable."""
    with patch("talekeeper.services.llm_client.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.get = AsyncMock(side_effect=httpx.ConnectError("refused"))

        result = await _is_ollama("http://unreachable:11434/v1")

        assert result is False


async def test_is_ollama_caches_result():
    """_is_ollama caches detection result per base_url."""
    _ollama_cache["http://cached:11434/v1"] = True
    result = await _is_ollama("http://cached:11434/v1")
    assert result is True


# ---- generate() Ollama extra_body tests (3.5) ----


@patch("talekeeper.services.llm_client._is_ollama", new_callable=AsyncMock, return_value=True)
@patch("talekeeper.services.llm_client.AsyncOpenAI")
async def test_generate_injects_num_ctx_for_ollama(MockOpenAI, mock_is_ollama):
    """generate() injects extra_body with num_ctx when Ollama is detected."""
    mock_client = AsyncMock()
    MockOpenAI.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    await generate("http://localhost:11434/v1", None, "llama3.1:8b", "prompt")

    call_kwargs = mock_client.chat.completions.create.call_args
    assert call_kwargs.kwargs["extra_body"] == {"options": {"num_ctx": 32768}}


@patch("talekeeper.services.llm_client._is_ollama", new_callable=AsyncMock, return_value=False)
@patch("talekeeper.services.llm_client.AsyncOpenAI")
async def test_generate_no_extra_body_for_non_ollama(MockOpenAI, mock_is_ollama):
    """generate() does not inject extra_body for non-Ollama providers."""
    mock_client = AsyncMock()
    MockOpenAI.return_value = mock_client

    mock_response = MagicMock()
    mock_response.choices = [MagicMock(message=MagicMock(content="response"))]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_response)

    await generate("http://openai.example.com/v1", "key", "gpt-4", "prompt")

    call_kwargs = mock_client.chat.completions.create.call_args
    assert "extra_body" not in call_kwargs.kwargs


# ---- unload_model tests ----


@patch("talekeeper.services.llm_client._is_ollama", new_callable=AsyncMock, return_value=True)
async def test_unload_model_sends_keep_alive_zero(mock_is_ollama):
    """unload_model sends keep_alive=0 to Ollama."""
    mock_response = httpx.Response(
        200,
        json={},
        request=httpx.Request("POST", "http://localhost:11434/api/generate"),
    )
    with patch("talekeeper.services.llm_client.httpx.AsyncClient") as MockClient:
        mock_client = AsyncMock()
        MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
        mock_client.post = AsyncMock(return_value=mock_response)

        await unload_model("http://localhost:11434/v1", None, "llama3.1:8b")

        mock_client.post.assert_awaited_once_with(
            "http://localhost:11434/api/generate",
            json={"model": "llama3.1:8b", "keep_alive": "0"},
        )


@patch("talekeeper.services.llm_client._is_ollama", new_callable=AsyncMock, return_value=False)
async def test_unload_model_noop_for_non_ollama(mock_is_ollama):
    """unload_model is a no-op for non-Ollama providers."""
    with patch("talekeeper.services.llm_client.httpx.AsyncClient") as MockClient:
        await unload_model("http://openai.example.com/v1", "key", "gpt-4")
        MockClient.assert_not_called()
