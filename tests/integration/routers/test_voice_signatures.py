"""Tests for voice signature API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from talekeeper.db import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed(db) -> dict:
    """Create campaign -> roster entry -> voice signature. Return IDs."""
    cursor = await db.execute(
        "INSERT INTO campaigns (name) VALUES ('Test Campaign')"
    )
    campaign_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO roster_entries (campaign_id, player_name, character_name) "
        "VALUES (?, 'Alice', 'Gandalf')",
        (campaign_id,),
    )
    roster_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO voice_signatures (campaign_id, roster_entry_id, embedding, num_samples) "
        "VALUES (?, ?, '[]', 5)",
        (campaign_id, roster_id),
    )
    sig_id = cursor.lastrowid

    await db.commit()
    return {
        "campaign_id": campaign_id,
        "roster_id": roster_id,
        "sig_id": sig_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_voice_signatures(client: AsyncClient) -> None:
    """GET /api/campaigns/{id}/voice-signatures returns signatures without embedding data."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/campaigns/{ids['campaign_id']}/voice-signatures")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    sig = data[0]
    assert sig["id"] == ids["sig_id"]
    assert sig["player_name"] == "Alice"
    assert sig["character_name"] == "Gandalf"
    # The endpoint joins roster_entries and omits raw embedding
    assert "embedding" not in sig


@pytest.mark.asyncio
async def test_delete_voice_signature(client: AsyncClient) -> None:
    """DELETE /api/voice-signatures/{id} returns deleted true."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.delete(f"/api/voice-signatures/{ids['sig_id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True

    # Verify it is actually gone
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM voice_signatures WHERE id = ?", (ids["sig_id"],)
        )
        assert len(rows) == 0
