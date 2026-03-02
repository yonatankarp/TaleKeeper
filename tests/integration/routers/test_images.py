"""Tests for image generation and management API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from talekeeper.db import get_db
from conftest import parse_sse_events


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


async def _seed_with_summary(db) -> dict:
    """Create campaign -> session -> full summary. Return IDs."""
    ids = await _seed_session(db)
    await db.execute(
        "INSERT INTO summaries (session_id, type, content) "
        "VALUES (?, 'full', 'The party fought a fearsome dragon in the mountain pass.')",
        (ids["session_id"],),
    )
    await db.commit()
    return ids


async def _seed_multiple_images(db, count: int = 3) -> dict:
    """Create campaign -> session -> multiple image records. Return IDs."""
    ids = await _seed_session(db)
    image_ids = []
    for i in range(count):
        cursor = await db.execute(
            "INSERT INTO session_images (session_id, file_path, prompt, model_used) "
            "VALUES (?, ?, ?, 'test-model')",
            (ids["session_id"], f"/tmp/fake_{i}.png", f"scene {i}"),
        )
        image_ids.append(cursor.lastrowid)
    await db.commit()
    ids["image_ids"] = image_ids
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


# ---------------------------------------------------------------------------
# Generate-image SSE tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch(
    "talekeeper.routers.images.image_client.resolve_config",
    new_callable=AsyncMock,
    return_value={"base_url": "http://img", "api_key": None, "model": "img-model"},
)
@patch(
    "talekeeper.routers.images.image_client.health_check",
    new_callable=AsyncMock,
    return_value={"status": "ok"},
)
@patch(
    "talekeeper.routers.images.generate_session_image",
    new_callable=AsyncMock,
    return_value={"id": 1, "file_path": "/tmp/gen.png", "prompt": "A brave knight"},
)
@patch(
    "talekeeper.routers.images.craft_scene_description",
    new_callable=AsyncMock,
)
async def test_generate_image_with_prompt(
    mock_craft: AsyncMock,
    mock_gen_image: AsyncMock,
    mock_img_health: AsyncMock,
    mock_img_config: AsyncMock,
    client: AsyncClient,
) -> None:
    """POST /api/sessions/{id}/generate-image with explicit prompt skips crafting."""
    async with get_db() as db:
        ids = await _seed_session(db)

    resp = await client.post(
        f"/api/sessions/{ids['session_id']}/generate-image",
        json={"prompt": "A brave knight"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]

    assert "phase" in event_types
    assert "done" in event_types

    # Should have generating_image phase but NOT crafting_scene
    phase_events = [e["data"]["phase"] for e in events if e["event"] == "phase"]
    assert "generating_image" in phase_events
    assert "crafting_scene" not in phase_events

    # craft_scene_description must NOT have been called
    mock_craft.assert_not_called()
    mock_gen_image.assert_called_once()

    # Verify the done event carries image metadata
    done_events = [e for e in events if e["event"] == "done"]
    assert len(done_events) == 1
    assert done_events[0]["data"]["image"]["id"] == 1


@pytest.mark.asyncio
@patch(
    "talekeeper.routers.images.image_client.resolve_config",
    new_callable=AsyncMock,
    return_value={"base_url": "http://img", "api_key": None, "model": "img-model"},
)
@patch(
    "talekeeper.routers.images.image_client.health_check",
    new_callable=AsyncMock,
    return_value={"status": "ok"},
)
@patch(
    "talekeeper.routers.images.llm_client.resolve_config",
    new_callable=AsyncMock,
    return_value={"base_url": "http://llm", "api_key": None, "model": "llm-model"},
)
@patch(
    "talekeeper.routers.images.llm_client.health_check",
    new_callable=AsyncMock,
    return_value={"status": "ok"},
)
@patch(
    "talekeeper.routers.images.craft_scene_description",
    new_callable=AsyncMock,
    return_value="A dragon swoops over a burning village.",
)
@patch(
    "talekeeper.routers.images.generate_session_image",
    new_callable=AsyncMock,
    return_value={"id": 2, "file_path": "/tmp/gen2.png", "prompt": "A dragon swoops over a burning village."},
)
async def test_generate_image_crafts_scene(
    mock_gen_image: AsyncMock,
    mock_craft: AsyncMock,
    mock_llm_health: AsyncMock,
    mock_llm_config: AsyncMock,
    mock_img_health: AsyncMock,
    mock_img_config: AsyncMock,
    client: AsyncClient,
) -> None:
    """POST /api/sessions/{id}/generate-image without prompt crafts scene first."""
    async with get_db() as db:
        ids = await _seed_with_summary(db)

    resp = await client.post(
        f"/api/sessions/{ids['session_id']}/generate-image",
        json={},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]

    assert "phase" in event_types
    assert "done" in event_types

    # Should have both crafting_scene and generating_image phases, in order
    phase_events = [e["data"]["phase"] for e in events if e["event"] == "phase"]
    assert phase_events == ["crafting_scene", "generating_image"]

    mock_craft.assert_called_once()
    mock_gen_image.assert_called_once()


@pytest.mark.asyncio
async def test_generate_image_session_not_found(client: AsyncClient) -> None:
    """POST /api/sessions/{id}/generate-image returns 404 for non-existent session."""
    resp = await client.post(
        "/api/sessions/99999/generate-image",
        json={"prompt": "anything"},
    )
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_image_file_not_found(client: AsyncClient) -> None:
    """GET /api/images/{id}/file returns 404 for non-existent image ID."""
    resp = await client.get("/api/images/99999/file")
    assert resp.status_code == 404
    assert "not found" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_all_session_images(client: AsyncClient) -> None:
    """DELETE /api/sessions/{id}/images removes all image metadata for the session."""
    async with get_db() as db:
        ids = await _seed_multiple_images(db, count=3)

    # Confirm 3 images exist
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM session_images WHERE session_id = ?",
            (ids["session_id"],),
        )
        assert len(rows) == 3

    resp = await client.delete(f"/api/sessions/{ids['session_id']}/images")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] == 3

    # Verify all images are gone
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM session_images WHERE session_id = ?",
            (ids["session_id"],),
        )
        assert len(rows) == 0
