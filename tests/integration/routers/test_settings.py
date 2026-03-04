"""Integration tests for settings API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_empty_settings(client: AsyncClient) -> None:
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)


@pytest.mark.asyncio
async def test_update_and_get_settings(client: AsyncClient) -> None:
    update_resp = await client.put(
        "/api/settings",
        json={"settings": {"llm_base_url": "http://localhost:11434/v1"}},
    )
    assert update_resp.status_code == 200
    assert update_resp.json()["updated"] is True

    get_resp = await client.get("/api/settings")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["llm_base_url"] == "http://localhost:11434/v1"


@pytest.mark.asyncio
async def test_password_masking(client: AsyncClient) -> None:
    await client.put(
        "/api/settings",
        json={"settings": {"smtp_password": "supersecret"}},
    )

    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert data["smtp_password"] == "********"


@pytest.mark.asyncio
async def test_hf_token_masking(client: AsyncClient) -> None:
    await client.put(
        "/api/settings",
        json={"settings": {"hf_token": "hf_abc123"}},
    )

    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    assert resp.json()["hf_token"] == "********"


@pytest.mark.asyncio
async def test_reset_clears_non_sensitive_settings(client: AsyncClient) -> None:
    await client.put(
        "/api/settings",
        json={"settings": {
            "whisper_model": "large-v3",
            "llm_base_url": "http://example.com",
            "hf_token": "hf_abc123",
            "smtp_password": "secret",
        }},
    )

    resp = await client.post("/api/settings/reset")
    assert resp.status_code == 200
    assert resp.json()["reset"] is True

    get_resp = await client.get("/api/settings")
    data = get_resp.json()
    # Non-sensitive settings should be cleared
    assert "whisper_model" not in data
    assert "llm_base_url" not in data
    # Sensitive keys should be preserved
    assert data["hf_token"] == "********"
    assert data["smtp_password"] == "********"


@pytest.mark.asyncio
async def test_reset_with_no_settings(client: AsyncClient) -> None:
    resp = await client.post("/api/settings/reset")
    assert resp.status_code == 200
    assert resp.json()["reset"] is True
