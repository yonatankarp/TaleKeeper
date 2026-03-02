"""Tests for the image generation client service."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
import base64

from talekeeper.services.image_client import health_check, generate_image


@patch("talekeeper.services.image_client._make_client")
async def test_health_check_success(mock_make):
    """health_check returns ok status when the image provider is reachable."""
    mock_client = AsyncMock()
    mock_make.return_value = mock_client
    mock_client.models.list = AsyncMock()

    result = await health_check("http://test", None, "test-model")

    assert result == {"status": "ok"}
    mock_client.models.list.assert_awaited_once()


@patch("talekeeper.services.image_client._make_client")
async def test_generate_image(mock_make):
    """generate_image returns decoded PNG bytes from the provider response."""
    mock_client = AsyncMock()
    mock_make.return_value = mock_client

    # Simulate base64-encoded PNG data
    raw_bytes = b"PNG-FAKE-DATA"
    b64_data = base64.b64encode(raw_bytes).decode()

    mock_image_data = MagicMock()
    mock_image_data.b64_json = b64_data

    mock_response = MagicMock()
    mock_response.data = [mock_image_data]
    mock_client.images.generate = AsyncMock(return_value=mock_response)

    result = await generate_image("http://test", None, "test-model", "a dragon")

    assert result == raw_bytes
    mock_client.images.generate.assert_awaited_once()
