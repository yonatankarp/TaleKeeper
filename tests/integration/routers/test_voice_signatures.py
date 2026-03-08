"""Tests for voice signature API endpoints."""

import io
import numpy as np
import pytest
from httpx import AsyncClient
from unittest.mock import patch

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


async def _seed_roster_only(db) -> dict:
    """Create campaign -> roster entry (no signature). Return IDs."""
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
    await db.commit()
    return {"campaign_id": campaign_id, "roster_id": roster_id}


_FAKE_EMBEDDING = np.ones(256, dtype=np.float32)
_FAKE_AUDIO = b"RIFF$\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80>\x00\x00\x00}\x00\x00\x02\x00\x10\x00data\x00\x00\x00\x00"


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


@pytest.mark.asyncio
async def test_upload_voice_sample_creates_signature(client: AsyncClient) -> None:
    """POST /api/roster/{id}/upload-voice-sample creates a voice signature."""
    async with get_db() as db:
        ids = await _seed_roster_only(db)

    with patch(
        "talekeeper.routers.voice_signatures.extract_speaker_embedding",
        return_value=_FAKE_EMBEDDING,
    ):
        resp = await client.post(
            f"/api/roster/{ids['roster_id']}/upload-voice-sample",
            files={"file": ("sample.wav", io.BytesIO(_FAKE_AUDIO), "audio/wav")},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["roster_entry_id"] == ids["roster_id"]
    assert data["campaign_id"] == ids["campaign_id"]

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM voice_signatures WHERE roster_entry_id = ?",
            (ids["roster_id"],),
        )
    assert len(rows) == 1
    assert rows[0]["source_session_id"] is None


@pytest.mark.asyncio
async def test_upload_voice_sample_replaces_existing(client: AsyncClient) -> None:
    """Uploading a new sample replaces an existing voice signature."""
    async with get_db() as db:
        ids = await _seed(db)

    with patch(
        "talekeeper.routers.voice_signatures.extract_speaker_embedding",
        return_value=_FAKE_EMBEDDING,
    ):
        resp = await client.post(
            f"/api/roster/{ids['roster_id']}/upload-voice-sample",
            files={"file": ("sample.wav", io.BytesIO(_FAKE_AUDIO), "audio/wav")},
        )

    assert resp.status_code == 200

    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM voice_signatures WHERE roster_entry_id = ?",
            (ids["roster_id"],),
        )
    assert len(rows) == 1
    # The old sig_id should be gone; a new one created
    assert rows[0]["id"] != ids["sig_id"]


@pytest.mark.asyncio
async def test_upload_voice_sample_no_speech_returns_400(client: AsyncClient) -> None:
    """Returns 400 when no speech is detected in the uploaded audio."""
    async with get_db() as db:
        ids = await _seed_roster_only(db)

    with patch(
        "talekeeper.routers.voice_signatures.extract_speaker_embedding",
        return_value=None,
    ):
        resp = await client.post(
            f"/api/roster/{ids['roster_id']}/upload-voice-sample",
            files={"file": ("silence.wav", io.BytesIO(_FAKE_AUDIO), "audio/wav")},
        )

    assert resp.status_code == 400
    assert "No speech detected" in resp.json()["detail"]


@pytest.mark.asyncio
async def test_upload_voice_sample_roster_not_found(client: AsyncClient) -> None:
    """Returns 404 for a nonexistent roster entry."""
    resp = await client.post(
        "/api/roster/99999/upload-voice-sample",
        files={"file": ("sample.wav", io.BytesIO(_FAKE_AUDIO), "audio/wav")},
    )
    assert resp.status_code == 404
