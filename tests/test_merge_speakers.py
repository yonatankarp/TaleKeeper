"""Tests for the POST /api/sessions/{session_id}/merge-speakers endpoint."""

import pytest
from httpx import AsyncClient

from talekeeper.db import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed_campaign_and_session(db) -> tuple[int, int]:
    """Insert a campaign + session and return (campaign_id, session_id)."""
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
    return campaign_id, session_id


async def _add_speaker(db, session_id: int, label: str, player_name=None, character_name=None) -> int:
    cursor = await db.execute(
        "INSERT INTO speakers (session_id, diarization_label, player_name, character_name) VALUES (?, ?, ?, ?)",
        (session_id, label, player_name, character_name),
    )
    await db.commit()
    return cursor.lastrowid


async def _add_segment(db, session_id: int, speaker_id: int, text: str) -> int:
    cursor = await db.execute(
        "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) VALUES (?, ?, ?, 0.0, 1.0)",
        (session_id, speaker_id, text),
    )
    await db.commit()
    return cursor.lastrowid


async def _add_roster_and_signature(db, campaign_id: int, player_name: str, character_name: str) -> tuple[int, int]:
    """Insert a roster entry + voice signature. Return (roster_entry_id, signature_id)."""
    cursor = await db.execute(
        "INSERT INTO roster_entries (campaign_id, player_name, character_name) VALUES (?, ?, ?)",
        (campaign_id, player_name, character_name),
    )
    roster_id = cursor.lastrowid
    cursor = await db.execute(
        "INSERT INTO voice_signatures (campaign_id, roster_entry_id, embedding, num_samples) VALUES (?, ?, '[]', 5)",
        (campaign_id, roster_id),
    )
    sig_id = cursor.lastrowid
    await db.commit()
    return roster_id, sig_id


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_successful_merge(client: AsyncClient):
    """Merge reassigns segments and deletes the source speaker."""
    async with get_db() as db:
        _, session_id = await _seed_campaign_and_session(db)
        source_id = await _add_speaker(db, session_id, "SPEAKER_01", "Alice", "Gandalf")
        target_id = await _add_speaker(db, session_id, "SPEAKER_02", "Bob", "Frodo")
        for i in range(3):
            await _add_segment(db, session_id, source_id, f"source seg {i}")
        for i in range(2):
            await _add_segment(db, session_id, target_id, f"target seg {i}")

    resp = await client.post(
        f"/api/sessions/{session_id}/merge-speakers",
        json={"source_speaker_id": source_id, "target_speaker_id": target_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == target_id
    assert data["segment_count"] == 5

    # Source speaker should be deleted
    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM speakers WHERE id = ?", (source_id,))
        assert len(rows) == 0

    # All segments should belong to target
    async with get_db() as db:
        rows = await db.execute_fetchall(
            "SELECT * FROM transcript_segments WHERE session_id = ?", (session_id,)
        )
        for row in rows:
            assert row["speaker_id"] == target_id


@pytest.mark.asyncio
async def test_merge_preserves_target_identity(client: AsyncClient):
    """Target speaker keeps its player_name, character_name, diarization_label."""
    async with get_db() as db:
        _, session_id = await _seed_campaign_and_session(db)
        source_id = await _add_speaker(db, session_id, "SPEAKER_01", "Alice", "Gandalf")
        target_id = await _add_speaker(db, session_id, "SPEAKER_02", "Bob", "Frodo")

    resp = await client.post(
        f"/api/sessions/{session_id}/merge-speakers",
        json={"source_speaker_id": source_id, "target_speaker_id": target_id},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["player_name"] == "Bob"
    assert data["character_name"] == "Frodo"
    assert data["diarization_label"] == "SPEAKER_02"


@pytest.mark.asyncio
async def test_merge_with_zero_segment_source(client: AsyncClient):
    """Merge succeeds even when the source has no segments."""
    async with get_db() as db:
        _, session_id = await _seed_campaign_and_session(db)
        source_id = await _add_speaker(db, session_id, "SPEAKER_01")
        target_id = await _add_speaker(db, session_id, "SPEAKER_02")
        await _add_segment(db, session_id, target_id, "existing")

    resp = await client.post(
        f"/api/sessions/{session_id}/merge-speakers",
        json={"source_speaker_id": source_id, "target_speaker_id": target_id},
    )
    assert resp.status_code == 200
    assert resp.json()["segment_count"] == 1

    async with get_db() as db:
        rows = await db.execute_fetchall("SELECT * FROM speakers WHERE id = ?", (source_id,))
        assert len(rows) == 0


@pytest.mark.asyncio
async def test_self_merge_rejected(client: AsyncClient):
    """Merging a speaker with itself returns 400."""
    async with get_db() as db:
        _, session_id = await _seed_campaign_and_session(db)
        speaker_id = await _add_speaker(db, session_id, "SPEAKER_01")

    resp = await client.post(
        f"/api/sessions/{session_id}/merge-speakers",
        json={"source_speaker_id": speaker_id, "target_speaker_id": speaker_id},
    )
    assert resp.status_code == 400
    assert "different" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_cross_session_rejected(client: AsyncClient):
    """Speakers from different sessions cannot be merged."""
    async with get_db() as db:
        campaign_id, session_id1 = await _seed_campaign_and_session(db)
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'Session 2', '2025-01-02')",
            (campaign_id,),
        )
        session_id2 = cursor.lastrowid
        await db.commit()
        s1 = await _add_speaker(db, session_id1, "SPEAKER_01")
        s2 = await _add_speaker(db, session_id2, "SPEAKER_02")

    # Call on session_id1 but target belongs to session_id2
    resp = await client.post(
        f"/api/sessions/{session_id1}/merge-speakers",
        json={"source_speaker_id": s1, "target_speaker_id": s2},
    )
    assert resp.status_code == 400
    assert "session" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_nonexistent_source_speaker(client: AsyncClient):
    """Merge with a nonexistent source speaker returns 404."""
    async with get_db() as db:
        _, session_id = await _seed_campaign_and_session(db)
        target_id = await _add_speaker(db, session_id, "SPEAKER_01")

    resp = await client.post(
        f"/api/sessions/{session_id}/merge-speakers",
        json={"source_speaker_id": 99999, "target_speaker_id": target_id},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_nonexistent_target_speaker(client: AsyncClient):
    """Merge with a nonexistent target speaker returns 404."""
    async with get_db() as db:
        _, session_id = await _seed_campaign_and_session(db)
        source_id = await _add_speaker(db, session_id, "SPEAKER_01")

    resp = await client.post(
        f"/api/sessions/{session_id}/merge-speakers",
        json={"source_speaker_id": source_id, "target_speaker_id": 99999},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_session_mismatch(client: AsyncClient):
    """Speakers belong to session 2 but endpoint is called on session 1."""
    async with get_db() as db:
        campaign_id, session_id1 = await _seed_campaign_and_session(db)
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'Session 2', '2025-01-02')",
            (campaign_id,),
        )
        session_id2 = cursor.lastrowid
        await db.commit()
        s1 = await _add_speaker(db, session_id2, "SPEAKER_01")
        s2 = await _add_speaker(db, session_id2, "SPEAKER_02")

    resp = await client.post(
        f"/api/sessions/{session_id1}/merge-speakers",
        json={"source_speaker_id": s1, "target_speaker_id": s2},
    )
    assert resp.status_code == 400
    assert "session" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_voice_signature_cleanup_on_merge(client: AsyncClient):
    """Source speaker's voice signature is deleted during merge."""
    async with get_db() as db:
        campaign_id, session_id = await _seed_campaign_and_session(db)
        source_id = await _add_speaker(db, session_id, "SPEAKER_01", "Alice", "Gandalf")
        target_id = await _add_speaker(db, session_id, "SPEAKER_02", "Bob", "Frodo")
        _, sig_id = await _add_roster_and_signature(db, campaign_id, "Alice", "Gandalf")
        # Also add a signature for the target to verify it's preserved
        _, target_sig_id = await _add_roster_and_signature(db, campaign_id, "Bob", "Frodo")

    resp = await client.post(
        f"/api/sessions/{session_id}/merge-speakers",
        json={"source_speaker_id": source_id, "target_speaker_id": target_id},
    )
    assert resp.status_code == 200

    async with get_db() as db:
        # Source signature deleted
        rows = await db.execute_fetchall("SELECT * FROM voice_signatures WHERE id = ?", (sig_id,))
        assert len(rows) == 0
        # Target signature preserved
        rows = await db.execute_fetchall("SELECT * FROM voice_signatures WHERE id = ?", (target_sig_id,))
        assert len(rows) == 1


@pytest.mark.asyncio
async def test_no_voice_signature_noop(client: AsyncClient):
    """Merge completes normally when neither speaker has a voice signature."""
    async with get_db() as db:
        _, session_id = await _seed_campaign_and_session(db)
        source_id = await _add_speaker(db, session_id, "SPEAKER_01")
        target_id = await _add_speaker(db, session_id, "SPEAKER_02")
        await _add_segment(db, session_id, source_id, "hello")

    resp = await client.post(
        f"/api/sessions/{session_id}/merge-speakers",
        json={"source_speaker_id": source_id, "target_speaker_id": target_id},
    )
    assert resp.status_code == 200
    assert resp.json()["segment_count"] == 1
