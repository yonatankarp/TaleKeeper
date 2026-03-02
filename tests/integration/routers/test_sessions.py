"""Integration tests for session API endpoints."""

import pytest
from httpx import AsyncClient


async def _create_campaign(client: AsyncClient) -> int:
    """Helper to create a campaign and return its ID."""
    resp = await client.post("/api/campaigns", json={"name": "Test Campaign"})
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_session(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    resp = await client.post(
        f"/api/campaigns/{campaign_id}/sessions",
        json={"name": "Session 1", "date": "2025-01-01"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Session 1"
    assert data["date"] == "2025-01-01"
    assert data["campaign_id"] == campaign_id
    assert "id" in data


@pytest.mark.asyncio
async def test_list_sessions(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    await client.post(
        f"/api/campaigns/{campaign_id}/sessions",
        json={"name": "Session 1", "date": "2025-01-01"},
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/sessions",
        json={"name": "Session 2", "date": "2025-01-15"},
    )

    resp = await client.get(f"/api/campaigns/{campaign_id}/sessions")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2


@pytest.mark.asyncio
async def test_get_session(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    create_resp = await client.post(
        f"/api/campaigns/{campaign_id}/sessions",
        json={"name": "My Session", "date": "2025-03-01"},
    )
    session_id = create_resp.json()["id"]

    resp = await client.get(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Session"
    assert resp.json()["id"] == session_id


@pytest.mark.asyncio
async def test_get_session_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/sessions/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_session(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    create_resp = await client.post(
        f"/api/campaigns/{campaign_id}/sessions",
        json={"name": "Original", "date": "2025-01-01"},
    )
    session_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/sessions/{session_id}", json={"name": "Renamed"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Renamed"


@pytest.mark.asyncio
async def test_delete_session(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    create_resp = await client.post(
        f"/api/campaigns/{campaign_id}/sessions",
        json={"name": "To Delete", "date": "2025-01-01"},
    )
    session_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Subsequent GET should return 404
    get_resp = await client.get(f"/api/sessions/{session_id}")
    assert get_resp.status_code == 404
