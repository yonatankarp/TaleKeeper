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
