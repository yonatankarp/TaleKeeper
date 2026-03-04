"""Integration tests for campaign API endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_campaign(client: AsyncClient) -> None:
    resp = await client.post("/api/campaigns", json={"name": "Test Campaign"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Test Campaign"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_campaigns(client: AsyncClient) -> None:
    await client.post("/api/campaigns", json={"name": "Campaign A"})
    await client.post("/api/campaigns", json={"name": "Campaign B"})

    resp = await client.get("/api/campaigns")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 2
    names = [c["name"] for c in data]
    assert "Campaign A" in names
    assert "Campaign B" in names


@pytest.mark.asyncio
async def test_get_campaign(client: AsyncClient) -> None:
    create_resp = await client.post("/api/campaigns", json={"name": "My Campaign"})
    campaign_id = create_resp.json()["id"]

    resp = await client.get(f"/api/campaigns/{campaign_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "My Campaign"
    assert resp.json()["id"] == campaign_id


@pytest.mark.asyncio
async def test_get_campaign_not_found(client: AsyncClient) -> None:
    resp = await client.get("/api/campaigns/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_update_campaign(client: AsyncClient) -> None:
    create_resp = await client.post("/api/campaigns", json={"name": "Original"})
    campaign_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/campaigns/{campaign_id}", json={"name": "Updated"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "Updated"


@pytest.mark.asyncio
async def test_delete_campaign(client: AsyncClient) -> None:
    create_resp = await client.post("/api/campaigns", json={"name": "To Delete"})
    campaign_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/campaigns/{campaign_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Subsequent GET should return 404
    get_resp = await client.get(f"/api/campaigns/{campaign_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_campaign_returns_similarity_threshold(client: AsyncClient) -> None:
    """GET /api/campaigns/{id} includes similarity_threshold with default value."""
    create_resp = await client.post("/api/campaigns", json={"name": "Threshold Test"})
    campaign_id = create_resp.json()["id"]

    resp = await client.get(f"/api/campaigns/{campaign_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "similarity_threshold" in data
    assert data["similarity_threshold"] == 0.75


@pytest.mark.asyncio
async def test_update_campaign_similarity_threshold(client: AsyncClient) -> None:
    """PUT /api/campaigns/{id} can update similarity_threshold."""
    create_resp = await client.post("/api/campaigns", json={"name": "Threshold Update"})
    campaign_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/campaigns/{campaign_id}", json={"similarity_threshold": 0.85}
    )
    assert resp.status_code == 200
    assert resp.json()["similarity_threshold"] == 0.85

    # Verify it persists
    get_resp = await client.get(f"/api/campaigns/{campaign_id}")
    assert get_resp.json()["similarity_threshold"] == 0.85


@pytest.mark.asyncio
async def test_update_campaign_similarity_threshold_validation(client: AsyncClient) -> None:
    """PUT /api/campaigns/{id} rejects out-of-range similarity_threshold."""
    create_resp = await client.post("/api/campaigns", json={"name": "Threshold Validate"})
    campaign_id = create_resp.json()["id"]

    # Value above 1.0 should be rejected
    resp = await client.put(
        f"/api/campaigns/{campaign_id}", json={"similarity_threshold": 1.5}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_campaign_dashboard(client: AsyncClient) -> None:
    create_resp = await client.post("/api/campaigns", json={"name": "Dashboard Test"})
    campaign_id = create_resp.json()["id"]

    resp = await client.get(f"/api/campaigns/{campaign_id}/dashboard")
    assert resp.status_code == 200
    data = resp.json()
    assert "session_count" in data
    assert "total_recorded_time" in data
    assert "most_recent_session_date" in data
    assert data["session_count"] == 0
