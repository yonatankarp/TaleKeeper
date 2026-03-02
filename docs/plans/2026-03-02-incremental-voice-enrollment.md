# Incremental Voice Enrollment Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Automatically enroll voice signatures when users assign speakers to roster entries during transcript review.

**Architecture:** When `PUT /api/speakers/{id}` updates player_name + character_name to match a roster entry, a FastAPI BackgroundTask extracts embeddings from the speaker's transcript segments (sampled up to ~120s, longest-first) and creates or weighted-merges a voice signature.

**Tech Stack:** SpeechBrain ECAPA-TDNN (existing), FastAPI BackgroundTasks, aiosqlite, numpy

---

### Task 1: Add `enroll_speaker_voice` service function — failing test

**Files:**
- Create: `tests/unit/services/test_enroll_voice.py`

**Step 1: Write the failing test — new signature creation**

```python
"""Tests for incremental voice enrollment."""

import json
from unittest.mock import patch, AsyncMock, MagicMock

import numpy as np
import pytest

from talekeeper.services.diarization import enroll_speaker_voice


@pytest.mark.asyncio
@patch("talekeeper.services.diarization._load_waveform")
@patch("talekeeper.services.diarization.extract_speaker_embedding")
@patch("talekeeper.services.audio.audio_to_wav")
async def test_enroll_creates_new_signature(
    mock_audio_to_wav: MagicMock,
    mock_extract: MagicMock,
    mock_load_waveform: MagicMock,
    db,
) -> None:
    """enroll_speaker_voice creates a new voice signature when none exists."""
    from conftest import create_campaign, create_session, create_speaker, create_segment

    campaign_id = await create_campaign(db)
    session_id = await create_session(db, campaign_id, status="completed")
    speaker_id = await create_speaker(
        db, session_id, player_name="Alice", character_name="Gandalf",
    )
    # Create roster entry
    cursor = await db.execute(
        "INSERT INTO roster_entries (campaign_id, player_name, character_name) "
        "VALUES (?, 'Alice', 'Gandalf')",
        (campaign_id,),
    )
    await db.commit()

    # Create segments with varying durations (longest-first sampling test)
    await create_segment(db, session_id, speaker_id, start_time=0.0, end_time=10.0)
    await create_segment(db, session_id, speaker_id, start_time=10.0, end_time=15.0)

    # Mock audio pipeline
    fake_wav = MagicMock()
    fake_wav.exists.return_value = True
    fake_wav.__eq__ = lambda self, other: False  # ensure cleanup runs
    mock_audio_to_wav.return_value = fake_wav

    fake_embedding = np.random.randn(192).astype(np.float32)
    fake_embedding = fake_embedding / np.linalg.norm(fake_embedding)
    mock_extract.return_value = fake_embedding
    mock_load_waveform.return_value = MagicMock()

    await enroll_speaker_voice(session_id, speaker_id)

    # Verify signature was created
    rows = await db.execute_fetchall(
        "SELECT * FROM voice_signatures WHERE campaign_id = ?", (campaign_id,)
    )
    assert len(rows) == 1
    sig = dict(rows[0])
    assert sig["num_samples"] > 0
    assert sig["source_session_id"] == session_id

    # Verify embedding is valid JSON array
    emb = np.array(json.loads(sig["embedding"]))
    assert emb.shape == (192,)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/unit/services/test_enroll_voice.py -v`
Expected: FAIL with `ImportError` (enroll_speaker_voice does not exist yet)

---

### Task 2: Add `enroll_speaker_voice` service function — implementation

**Files:**
- Modify: `src/talekeeper/services/diarization.py` (append new function)

**Step 1: Implement `enroll_speaker_voice`**

Add at the end of `diarization.py`:

```python
# Maximum audio duration (seconds) to sample per enrollment
_ENROLL_MAX_AUDIO_SEC = 120.0


async def enroll_speaker_voice(session_id: int, speaker_id: int) -> None:
    """Extract voice embedding from a speaker's segments and create/update signature.

    Samples up to ~120s of audio (longest segments first) for efficiency.
    Creates a new voice signature if none exists, or weighted-merges with the
    existing one.
    """
    import json
    import logging
    from talekeeper.db import get_db
    from talekeeper.services.audio import audio_to_wav

    log = logging.getLogger(__name__)

    async with get_db() as db:
        # Get speaker + session info
        rows = await db.execute_fetchall(
            """SELECT s.player_name, s.character_name, s.session_id,
                      sess.campaign_id, sess.audio_path
               FROM speakers s
               JOIN sessions sess ON sess.id = s.session_id
               WHERE s.id = ?""",
            (speaker_id,),
        )
        if not rows:
            log.warning("enroll_speaker_voice: speaker %d not found", speaker_id)
            return
        info = dict(rows[0])

        if not info["player_name"] or not info["character_name"]:
            return
        if not info["audio_path"]:
            log.warning("enroll_speaker_voice: session %d has no audio", session_id)
            return

        # Find matching roster entry
        roster_rows = await db.execute_fetchall(
            """SELECT id FROM roster_entries
               WHERE campaign_id = ? AND player_name = ? AND character_name = ?
               AND is_active = 1""",
            (info["campaign_id"], info["player_name"], info["character_name"]),
        )
        if not roster_rows:
            return
        roster_entry_id = roster_rows[0]["id"]

        # Get transcript segments for this speaker, sorted by duration descending
        seg_rows = await db.execute_fetchall(
            """SELECT start_time, end_time FROM transcript_segments
               WHERE session_id = ? AND speaker_id = ?
               ORDER BY (end_time - start_time) DESC""",
            (session_id, speaker_id),
        )

        # Sample up to _ENROLL_MAX_AUDIO_SEC
        time_ranges: list[tuple[float, float]] = []
        total_duration = 0.0
        for seg in seg_rows:
            dur = seg["end_time"] - seg["start_time"]
            if total_duration + dur > _ENROLL_MAX_AUDIO_SEC:
                remaining = _ENROLL_MAX_AUDIO_SEC - total_duration
                if remaining > 0.5:  # only include if at least 0.5s
                    time_ranges.append((seg["start_time"], seg["start_time"] + remaining))
                break
            time_ranges.append((seg["start_time"], seg["end_time"]))
            total_duration += dur

        if not time_ranges:
            return

        # Load existing signature for weighted merge
        existing_rows = await db.execute_fetchall(
            "SELECT id, embedding, num_samples FROM voice_signatures WHERE roster_entry_id = ?",
            (roster_entry_id,),
        )

    # Extract embedding (CPU-intensive, outside DB context)
    audio_file = Path(info["audio_path"])
    wav_path = audio_to_wav(audio_file)
    try:
        waveform = _load_waveform(wav_path)
        new_embedding = extract_speaker_embedding(waveform, time_ranges)
    finally:
        if wav_path.exists() and wav_path != audio_file:
            wav_path.unlink()

    if new_embedding is None:
        return

    new_count = len(time_ranges)

    if existing_rows:
        # Weighted merge with existing signature
        existing = dict(existing_rows[0])
        old_emb = np.array(json.loads(existing["embedding"]))
        old_count = existing["num_samples"]

        combined = old_emb * old_count + new_embedding * new_count
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm

        total_count = old_count + new_count
        embedding_json = json.dumps(combined.tolist())

        async with get_db() as db:
            await db.execute(
                """UPDATE voice_signatures
                   SET embedding = ?, num_samples = ?, source_session_id = ?
                   WHERE id = ?""",
                (embedding_json, total_count, session_id, existing["id"]),
            )
        log.info(
            "Updated voice signature for roster_entry %d (%d total samples)",
            roster_entry_id, total_count,
        )
    else:
        # Create new signature
        embedding_json = json.dumps(new_embedding.tolist())

        async with get_db() as db:
            await db.execute(
                """INSERT INTO voice_signatures
                   (campaign_id, roster_entry_id, embedding, source_session_id, num_samples)
                   VALUES (?, ?, ?, ?, ?)""",
                (info["campaign_id"], roster_entry_id, embedding_json, session_id, new_count),
            )
        log.info(
            "Created voice signature for roster_entry %d (%d samples)",
            roster_entry_id, new_count,
        )
```

**Step 2: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/services/test_enroll_voice.py::test_enroll_creates_new_signature -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/talekeeper/services/diarization.py tests/unit/services/test_enroll_voice.py
git commit -m "feat: add enroll_speaker_voice service function"
```

---

### Task 3: Test weighted merge with existing signature

**Files:**
- Modify: `tests/unit/services/test_enroll_voice.py`

**Step 1: Write the failing test**

```python
@pytest.mark.asyncio
@patch("talekeeper.services.diarization._load_waveform")
@patch("talekeeper.services.diarization.extract_speaker_embedding")
@patch("talekeeper.services.audio.audio_to_wav")
async def test_enroll_merges_with_existing_signature(
    mock_audio_to_wav: MagicMock,
    mock_extract: MagicMock,
    mock_load_waveform: MagicMock,
    db,
) -> None:
    """enroll_speaker_voice weighted-merges when a signature already exists."""
    from conftest import create_campaign, create_session, create_speaker, create_segment

    campaign_id = await create_campaign(db)
    session_id = await create_session(db, campaign_id, status="completed")
    speaker_id = await create_speaker(
        db, session_id, player_name="Alice", character_name="Gandalf",
    )
    cursor = await db.execute(
        "INSERT INTO roster_entries (campaign_id, player_name, character_name) "
        "VALUES (?, 'Alice', 'Gandalf')",
        (campaign_id,),
    )
    roster_id = cursor.lastrowid

    # Create existing signature with known embedding
    old_emb = np.zeros(192, dtype=np.float32)
    old_emb[0] = 1.0  # unit vector along first axis
    await db.execute(
        "INSERT INTO voice_signatures (campaign_id, roster_entry_id, embedding, source_session_id, num_samples) "
        "VALUES (?, ?, ?, ?, 10)",
        (campaign_id, roster_id, json.dumps(old_emb.tolist()), session_id),
    )
    await db.commit()

    await create_segment(db, session_id, speaker_id, start_time=0.0, end_time=5.0)

    # Mock audio pipeline
    fake_wav = MagicMock()
    fake_wav.exists.return_value = True
    fake_wav.__eq__ = lambda self, other: False
    mock_audio_to_wav.return_value = fake_wav

    new_emb = np.zeros(192, dtype=np.float32)
    new_emb[1] = 1.0  # unit vector along second axis
    mock_extract.return_value = new_emb
    mock_load_waveform.return_value = MagicMock()

    await enroll_speaker_voice(session_id, speaker_id)

    rows = await db.execute_fetchall(
        "SELECT * FROM voice_signatures WHERE roster_entry_id = ?", (roster_id,)
    )
    assert len(rows) == 1  # updated, not duplicated
    sig = dict(rows[0])
    assert sig["num_samples"] == 11  # 10 old + 1 new

    # Verify weighted merge direction: should be more like old_emb (10x weight)
    merged = np.array(json.loads(sig["embedding"]))
    assert merged[0] > merged[1]  # old direction dominates
```

**Step 2: Run test to verify it passes**

Run: `.venv/bin/python -m pytest tests/unit/services/test_enroll_voice.py -v`
Expected: PASS (both tests)

**Step 3: Commit**

```bash
git add tests/unit/services/test_enroll_voice.py
git commit -m "test: add weighted merge test for voice enrollment"
```

---

### Task 4: Test audio sampling cap (120s limit)

**Files:**
- Modify: `tests/unit/services/test_enroll_voice.py`

**Step 1: Write the test**

```python
@pytest.mark.asyncio
@patch("talekeeper.services.diarization._load_waveform")
@patch("talekeeper.services.diarization.extract_speaker_embedding")
@patch("talekeeper.services.audio.audio_to_wav")
async def test_enroll_samples_up_to_120s(
    mock_audio_to_wav: MagicMock,
    mock_extract: MagicMock,
    mock_load_waveform: MagicMock,
    db,
) -> None:
    """enroll_speaker_voice caps audio sampling at ~120 seconds."""
    from conftest import create_campaign, create_session, create_speaker, create_segment

    campaign_id = await create_campaign(db)
    session_id = await create_session(db, campaign_id, status="completed")
    speaker_id = await create_speaker(
        db, session_id, player_name="Alice", character_name="Gandalf",
    )
    cursor = await db.execute(
        "INSERT INTO roster_entries (campaign_id, player_name, character_name) "
        "VALUES (?, 'Alice', 'Gandalf')",
        (campaign_id,),
    )
    await db.commit()

    # Create segments totalling 300s — should be capped
    await create_segment(db, session_id, speaker_id, start_time=0.0, end_time=100.0)
    await create_segment(db, session_id, speaker_id, start_time=100.0, end_time=200.0)
    await create_segment(db, session_id, speaker_id, start_time=200.0, end_time=300.0)

    fake_wav = MagicMock()
    fake_wav.exists.return_value = True
    fake_wav.__eq__ = lambda self, other: False
    mock_audio_to_wav.return_value = fake_wav

    fake_embedding = np.random.randn(192).astype(np.float32)
    fake_embedding = fake_embedding / np.linalg.norm(fake_embedding)
    mock_extract.return_value = fake_embedding
    mock_load_waveform.return_value = MagicMock()

    await enroll_speaker_voice(session_id, speaker_id)

    # Verify extract_speaker_embedding was called with capped time_ranges
    call_args = mock_extract.call_args
    time_ranges = call_args[0][1]  # second positional arg
    total = sum(end - start for start, end in time_ranges)
    assert total <= 120.0 + 0.01  # allow tiny float rounding
    assert total >= 119.0  # should use most of the cap
```

**Step 2: Run all enrollment tests**

Run: `.venv/bin/python -m pytest tests/unit/services/test_enroll_voice.py -v`
Expected: PASS (all 3 tests)

**Step 3: Commit**

```bash
git add tests/unit/services/test_enroll_voice.py
git commit -m "test: verify 120s audio sampling cap for voice enrollment"
```

---

### Task 5: Test no-op cases (no roster match, no audio, no segments)

**Files:**
- Modify: `tests/unit/services/test_enroll_voice.py`

**Step 1: Write tests for edge cases**

```python
@pytest.mark.asyncio
async def test_enroll_noop_no_roster_match(db) -> None:
    """enroll_speaker_voice does nothing when speaker doesn't match a roster entry."""
    from conftest import create_campaign, create_session, create_speaker

    campaign_id = await create_campaign(db)
    session_id = await create_session(db, campaign_id, status="completed")
    speaker_id = await create_speaker(
        db, session_id, player_name="Alice", character_name="Gandalf",
    )
    # No roster entry created

    await enroll_speaker_voice(session_id, speaker_id)

    rows = await db.execute_fetchall("SELECT * FROM voice_signatures")
    assert len(rows) == 0


@pytest.mark.asyncio
async def test_enroll_noop_no_audio(db) -> None:
    """enroll_speaker_voice does nothing when session has no audio."""
    from conftest import create_campaign, create_session, create_speaker

    campaign_id = await create_campaign(db)
    # Default session has no audio_path
    session_id = await create_session(db, campaign_id, status="completed")
    speaker_id = await create_speaker(
        db, session_id, player_name="Alice", character_name="Gandalf",
    )
    cursor = await db.execute(
        "INSERT INTO roster_entries (campaign_id, player_name, character_name) "
        "VALUES (?, 'Alice', 'Gandalf')",
        (campaign_id,),
    )
    await db.commit()

    await enroll_speaker_voice(session_id, speaker_id)

    rows = await db.execute_fetchall("SELECT * FROM voice_signatures")
    assert len(rows) == 0
```

**Step 2: Run all enrollment tests**

Run: `.venv/bin/python -m pytest tests/unit/services/test_enroll_voice.py -v`
Expected: PASS (all 5 tests)

**Step 3: Commit**

```bash
git add tests/unit/services/test_enroll_voice.py
git commit -m "test: verify enrollment no-ops for missing roster/audio"
```

---

### Task 6: Wire background enrollment into speaker update endpoint — failing test

**Files:**
- Modify: `tests/integration/routers/test_speakers.py`

**Step 1: Write the failing test**

Add to the end of `test_speakers.py`:

```python
@pytest.mark.asyncio
@patch(
    "talekeeper.routers.speakers.enroll_speaker_voice",
    new_callable=AsyncMock,
)
async def test_update_speaker_triggers_enrollment(
    mock_enroll: AsyncMock,
    client: AsyncClient,
) -> None:
    """PUT /api/speakers/{id} triggers background voice enrollment when roster matches."""
    async with get_db() as db:
        ids = await _seed(db)
        # Set audio_path on session so enrollment can proceed
        await db.execute(
            "UPDATE sessions SET audio_path = '/tmp/fake.webm', status = 'completed' WHERE id = ?",
            (ids["session_id"],),
        )
        await db.commit()

    # Update speaker to match roster entry (Alice/Gandalf)
    resp = await client.put(
        f"/api/speakers/{ids['speaker_b']}",
        json={"player_name": "Alice", "character_name": "Gandalf"},
    )
    assert resp.status_code == 200

    # Verify enrollment was scheduled
    mock_enroll.assert_called_once_with(ids["session_id"], ids["speaker_b"])
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/integration/routers/test_speakers.py::test_update_speaker_triggers_enrollment -v`
Expected: FAIL (enroll_speaker_voice not imported/called in speakers.py yet)

---

### Task 7: Wire background enrollment into speaker update endpoint — implementation

**Files:**
- Modify: `src/talekeeper/routers/speakers.py`

**Step 1: Modify the `update_speaker` endpoint**

In `speakers.py`, modify the `update_speaker` function to:
1. Accept `BackgroundTasks` parameter
2. After updating, check if player_name + character_name match a roster entry
3. If match found, schedule `enroll_speaker_voice` as background task

Change the import section — add:
```python
from fastapi import APIRouter, BackgroundTasks, HTTPException
```

Replace the existing `update_speaker` function with:
```python
@router.put("/api/speakers/{speaker_id}")
async def update_speaker(
    speaker_id: int, body: SpeakerUpdate, background_tasks: BackgroundTasks
) -> dict:
    async with get_db() as db:
        existing = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE id = ?", (speaker_id,)
        )
        if not existing:
            raise HTTPException(status_code=404, detail="Speaker not found")

        speaker = dict(existing[0])
        fields = []
        values = []
        if body.player_name is not None:
            fields.append("player_name = ?")
            values.append(body.player_name)
        if body.character_name is not None:
            fields.append("character_name = ?")
            values.append(body.character_name)

        if fields:
            values.append(speaker_id)
            await db.execute(
                f"UPDATE speakers SET {', '.join(fields)} WHERE id = ?",
                values,
            )

        rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE id = ?", (speaker_id,)
        )
        updated = dict(rows[0])

        # Check if updated speaker matches a roster entry for voice enrollment
        player_name = updated.get("player_name")
        character_name = updated.get("character_name")
        if player_name and character_name:
            session_rows = await db.execute_fetchall(
                "SELECT campaign_id FROM sessions WHERE id = ?",
                (updated["session_id"],),
            )
            if session_rows:
                campaign_id = session_rows[0]["campaign_id"]
                roster_rows = await db.execute_fetchall(
                    """SELECT id FROM roster_entries
                       WHERE campaign_id = ? AND player_name = ? AND character_name = ?
                       AND is_active = 1""",
                    (campaign_id, player_name, character_name),
                )
                if roster_rows:
                    background_tasks.add_task(
                        enroll_speaker_voice,
                        updated["session_id"],
                        speaker_id,
                    )

    return updated
```

Add the import near the top of the file (after existing imports):
```python
from talekeeper.services.diarization import enroll_speaker_voice
```

**Step 2: Run the integration test**

Run: `.venv/bin/python -m pytest tests/integration/routers/test_speakers.py::test_update_speaker_triggers_enrollment -v`
Expected: PASS

**Step 3: Run all speaker tests to verify no regressions**

Run: `.venv/bin/python -m pytest tests/integration/routers/test_speakers.py -v`
Expected: All PASS

**Step 4: Commit**

```bash
git add src/talekeeper/routers/speakers.py tests/integration/routers/test_speakers.py
git commit -m "feat: trigger voice enrollment on speaker assignment to roster entry"
```

---

### Task 8: Test that non-roster updates don't trigger enrollment

**Files:**
- Modify: `tests/integration/routers/test_speakers.py`

**Step 1: Write the test**

```python
@pytest.mark.asyncio
@patch(
    "talekeeper.routers.speakers.enroll_speaker_voice",
    new_callable=AsyncMock,
)
async def test_update_speaker_no_enrollment_without_roster_match(
    mock_enroll: AsyncMock,
    client: AsyncClient,
) -> None:
    """PUT /api/speakers/{id} does NOT trigger enrollment when no roster match."""
    async with get_db() as db:
        ids = await _seed(db)

    # Update with names that don't match any roster entry
    resp = await client.put(
        f"/api/speakers/{ids['speaker_b']}",
        json={"player_name": "Charlie", "character_name": "Sauron"},
    )
    assert resp.status_code == 200

    mock_enroll.assert_not_called()
```

**Step 2: Run test**

Run: `.venv/bin/python -m pytest tests/integration/routers/test_speakers.py -v`
Expected: All PASS

**Step 3: Commit**

```bash
git add tests/integration/routers/test_speakers.py
git commit -m "test: verify no enrollment for non-roster speaker updates"
```

---

### Task 9: Run full test suite

**Step 1: Run all tests**

Run: `.venv/bin/python -m pytest -v`
Expected: All PASS, no regressions

**Step 2: Commit if any fixes needed**

---

### Task 10: Final commit and summary

**Step 1: Verify git status is clean**

Run: `git status`

**Step 2: Verify the feature end-to-end by reviewing the code path**

1. User assigns speaker → `PUT /api/speakers/{id}` with player_name + character_name
2. Router checks roster match → schedules `enroll_speaker_voice` as BackgroundTask
3. Service loads audio, samples up to 120s of segments (longest first)
4. Extracts ECAPA-TDNN embedding → creates or weighted-merges signature
5. Next diarization run picks up the signature via `run_final_diarization`
