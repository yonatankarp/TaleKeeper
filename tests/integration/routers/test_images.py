"""Tests for image generation and management API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from talekeeper.db import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_session(db) -> dict:
    """Create campaign -> session. Return IDs."""
    cursor = await db.execute(
        "INSERT INTO campaigns (name) VALUES ('Test Campaign')"
    )
    campaign_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'Session 1', '2025-01-01')",
        (campaign_id,),
    )
    session_id = cursor.lastrowid

    await db.commit()
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
    }


async def _seed_with_image(db) -> dict:
    """Create campaign -> session -> image record. Return IDs."""
    ids = await _seed_session(db)
    cursor = await db.execute(
        "INSERT INTO session_images (session_id, file_path, prompt, model_used) "
        "VALUES (?, '/tmp/fake.png', 'a fantasy scene', 'test-model')",
        (ids["session_id"],),
    )
    ids["image_id"] = cursor.lastrowid
    await db.commit()
    return ids


async def _seed_with_transcript(db) -> dict:
    """Create campaign -> session -> speaker -> segments. Return IDs."""
    ids = await _seed_session(db)

    cursor = await db.execute(
        "INSERT INTO speakers (session_id, diarization_label, player_name, character_name) "
        "VALUES (?, 'SPEAKER_00', 'Alice', 'Gandalf')",
        (ids["session_id"],),
    )
    speaker_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
        "VALUES (?, ?, 'The dragon appeared before us.', 0.0, 3.0)",
        (ids["session_id"], speaker_id),
    )
    await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
        "VALUES (?, ?, 'We drew our swords.', 3.0, 6.0)",
        (ids["session_id"], speaker_id),
    )

    ids["speaker_id"] = speaker_id
    await db.commit()
    return ids


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_images(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/images returns all images for the session."""
    async with get_db() as db:
        ids = await _seed_with_image(db)

    resp = await client.get(f"/api/sessions/{ids['session_id']}/images")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["id"] == ids["image_id"]
    assert data[0]["prompt"] == "a fantasy scene"


@pytest.mark.asyncio
async def test_delete_image(client: AsyncClient) -> None:
    """DELETE /api/images/{id} returns status 204."""
    async with get_db() as db:
        ids = await _seed_with_image(db)

    resp = await client.delete(f"/api/images/{ids['image_id']}")
    assert resp.status_code == 204

    # Verify it is gone from the database
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM session_images WHERE id = ?", (ids["image_id"],)
        )
        assert len(rows) == 0


@pytest.mark.asyncio
@patch(
    "talekeeper.services.image_client.resolve_config",
    new_callable=AsyncMock,
    return_value={"base_url": "http://test-image", "api_key": None, "model": "test-img"},
)
@patch(
    "talekeeper.services.image_client.health_check",
    new_callable=AsyncMock,
    return_value={"status": "ok"},
)
async def test_image_health(
    mock_health: AsyncMock,
    mock_config: AsyncMock,
    client: AsyncClient,
) -> None:
    """GET /api/settings/image-health returns the health check result."""
    resp = await client.get("/api/settings/image-health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    mock_config.assert_called_once()
    mock_health.assert_called_once()


@pytest.mark.asyncio
@patch(
    "talekeeper.services.llm_client.resolve_config",
    new_callable=AsyncMock,
    return_value={"base_url": "http://test", "api_key": None, "model": "test"},
)
@patch(
    "talekeeper.services.llm_client.health_check",
    new_callable=AsyncMock,
    return_value={"status": "ok"},
)
@patch(
    "talekeeper.services.llm_client.generate",
    new_callable=AsyncMock,
    return_value="A dragon looms over a burning village at dusk.",
)
async def test_craft_scene(
    mock_generate: AsyncMock,
    mock_health: AsyncMock,
    mock_config: AsyncMock,
    client: AsyncClient,
) -> None:
    """POST /api/sessions/{id}/craft-scene returns a scene description via mocked LLM."""
    async with get_db() as db:
        ids = await _seed_with_transcript(db)

    resp = await client.post(f"/api/sessions/{ids['session_id']}/craft-scene")
    assert resp.status_code == 200
    data = resp.json()
    assert "scene_description" in data
    assert data["scene_description"] == "A dragon looms over a burning village at dusk."
    mock_generate.assert_called_once()
