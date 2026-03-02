"""Tests for summary generation and management API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from talekeeper.db import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_with_summary(db) -> dict:
    """Create campaign -> session -> summary. Return IDs."""
    cursor = await db.execute(
        "INSERT INTO campaigns (name) VALUES ('Test Campaign')"
    )
    campaign_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'Session 1', '2025-01-01')",
        (campaign_id,),
    )
    session_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO summaries (session_id, type, content, model_used) "
        "VALUES (?, 'full', 'The heroes fought bravely.', 'test-model')",
        (session_id,),
    )
    summary_id = cursor.lastrowid

    await db.commit()
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "summary_id": summary_id,
    }


async def _seed_with_transcript(db) -> dict:
    """Create campaign -> session -> speaker -> segments (no summary). Return IDs."""
    cursor = await db.execute(
        "INSERT INTO campaigns (name) VALUES ('Test Campaign')"
    )
    campaign_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'Session 1', '2025-01-01')",
        (campaign_id,),
    )
    session_id = cursor.lastrowid

    cursor = await db.execute(
        "INSERT INTO speakers (session_id, diarization_label, player_name, character_name) "
        "VALUES (?, 'SPEAKER_00', 'Alice', 'Gandalf')",
        (session_id,),
    )
    speaker_id = cursor.lastrowid

    await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
        "VALUES (?, ?, 'We should head north.', 0.0, 3.0)",
        (session_id, speaker_id),
    )
    await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) "
        "VALUES (?, ?, 'I agree, let us go.', 3.0, 6.0)",
        (session_id, speaker_id),
    )

    await db.commit()
    return {
        "campaign_id": campaign_id,
        "session_id": session_id,
        "speaker_id": speaker_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_summaries(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/summaries returns all summaries for the session."""
    async with get_db() as db:
        ids = await _seed_with_summary(db)

    resp = await client.get(f"/api/sessions/{ids['session_id']}/summaries")
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["type"] == "full"
    assert "heroes fought" in data[0]["content"]


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
    return_value="A summary of the session.",
)
async def test_generate_summary(
    mock_generate: AsyncMock,
    mock_health: AsyncMock,
    mock_config: AsyncMock,
    client: AsyncClient,
) -> None:
    """POST /api/sessions/{id}/generate-summary creates a new full summary using mocked LLM."""
    async with get_db() as db:
        ids = await _seed_with_transcript(db)

    resp = await client.post(
        f"/api/sessions/{ids['session_id']}/generate-summary",
        json={"type": "full"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["type"] == "full"
    assert data["content"] == "A summary of the session."
    assert data["session_id"] == ids["session_id"]
    mock_generate.assert_called_once()


@pytest.mark.asyncio
async def test_update_summary(client: AsyncClient) -> None:
    """PUT /api/summaries/{id} updates the summary content."""
    async with get_db() as db:
        ids = await _seed_with_summary(db)

    resp = await client.put(
        f"/api/summaries/{ids['summary_id']}",
        json={"content": "New content"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["content"] == "New content"
    assert data["id"] == ids["summary_id"]


@pytest.mark.asyncio
async def test_delete_summary(client: AsyncClient) -> None:
    """DELETE /api/summaries/{id} returns deleted true."""
    async with get_db() as db:
        ids = await _seed_with_summary(db)

    resp = await client.delete(f"/api/summaries/{ids['summary_id']}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["deleted"] is True

    # Verify it is actually gone
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM summaries WHERE id = ?", (ids["summary_id"],)
        )
        assert len(rows) == 0


@pytest.mark.asyncio
@patch(
    "talekeeper.services.llm_client.resolve_config",
    new_callable=AsyncMock,
    return_value={"base_url": "http://test", "api_key": None, "model": "test"},
)
@patch(
    "talekeeper.services.llm_client.health_check",
    new_callable=AsyncMock,
    return_value={"status": "ok", "message": "All good"},
)
async def test_llm_status(
    mock_health: AsyncMock,
    mock_config: AsyncMock,
    client: AsyncClient,
) -> None:
    """GET /api/llm/status returns the health check result."""
    resp = await client.get("/api/llm/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    mock_config.assert_called_once()
    mock_health.assert_called_once()
