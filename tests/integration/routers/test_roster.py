"""Integration tests for roster API endpoints."""

import pytest
from httpx import AsyncClient


async def _create_campaign(client: AsyncClient) -> int:
    """Helper to create a campaign and return its ID."""
    resp = await client.post("/api/campaigns", json={"name": "Test Campaign"})
    assert resp.status_code == 200
    return resp.json()["id"]


@pytest.mark.asyncio
async def test_create_roster_entry(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    resp = await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["player_name"] == "Alice"
    assert data["character_name"] == "Gandalf"
    assert data["campaign_id"] == campaign_id
    assert "id" in data


@pytest.mark.asyncio
async def test_list_roster(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Bob", "character_name": "Aragorn"},
    )

    resp = await client.get(f"/api/campaigns/{campaign_id}/roster")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 2
    player_names = [e["player_name"] for e in data]
    assert "Alice" in player_names
    assert "Bob" in player_names


@pytest.mark.asyncio
async def test_update_roster_entry(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    create_resp = await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    entry_id = create_resp.json()["id"]

    resp = await client.put(
        f"/api/roster/{entry_id}",
        json={"character_name": "Gandalf the White"},
    )
    assert resp.status_code == 200
    assert resp.json()["character_name"] == "Gandalf the White"
    # Player name should remain unchanged
    assert resp.json()["player_name"] == "Alice"


@pytest.mark.asyncio
async def test_delete_roster_entry(client: AsyncClient) -> None:
    campaign_id = await _create_campaign(client)

    create_resp = await client.post(
        f"/api/campaigns/{campaign_id}/roster",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    entry_id = create_resp.json()["id"]

    resp = await client.delete(f"/api/roster/{entry_id}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True


@pytest.mark.asyncio
async def test_delete_roster_entry_not_found(client: AsyncClient) -> None:
    resp = await client.delete("/api/roster/99999")
    assert resp.status_code == 404
