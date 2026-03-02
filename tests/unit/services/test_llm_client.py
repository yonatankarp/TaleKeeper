"""Tests for the LLM client service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock

from openai import APIConnectionError

from talekeeper.services.llm_client import health_check, generate, resolve_config


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


@patch("talekeeper.services.llm_client.AsyncOpenAI")
async def test_generate(MockOpenAI):
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
