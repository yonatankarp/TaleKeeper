# Black-Box Test Coverage Improvement — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Raise backend test coverage from ~53% to ~80% by adding two-layer black-box tests (unit + integration) that are library-agnostic.

**Architecture:** Reorganize tests into `tests/unit/` (service functions, all deps mocked) and `tests/integration/` (HTTP path, real DB, external I/O mocked). Existing tests move into the appropriate layer. New tests fill coverage gaps in recording, diarization, transcripts, roster, images, exports, and speakers.

**Tech Stack:** pytest, pytest-asyncio, httpx AsyncClient, unittest.mock (patch/AsyncMock), aiosqlite (real temp DB for integration)

---

### Task 1: Restructure test directories

**Files:**
- Create: `tests/unit/__init__.py` (empty)
- Create: `tests/unit/services/__init__.py` (empty)
- Create: `tests/integration/__init__.py` (empty)
- Create: `tests/integration/db/__init__.py` (empty)
- Create: `tests/integration/routers/__init__.py` (empty)
- Move: `tests/services/*` → `tests/unit/services/`
- Move: `tests/db/*` → `tests/integration/db/`
- Move: `tests/routers/*` → `tests/integration/routers/`
- Modify: `pyproject.toml` — update testpaths

**Step 1: Create new directory structure**

```bash
mkdir -p tests/unit/services tests/integration/db tests/integration/routers
touch tests/unit/__init__.py tests/unit/services/__init__.py
touch tests/integration/__init__.py tests/integration/db/__init__.py tests/integration/routers/__init__.py
```

**Step 2: Move existing test files**

```bash
mv tests/services/test_*.py tests/unit/services/
mv tests/services/__init__.py tests/unit/services/__init__.py  # overwrite the empty one
mv tests/db/test_schema.py tests/integration/db/
mv tests/routers/test_*.py tests/integration/routers/
```

**Step 3: Clean up old empty directories**

```bash
rmdir tests/services tests/db tests/routers 2>/dev/null || true
```

**Step 4: Update pyproject.toml testpaths**

In `pyproject.toml`, change:
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```
(testpaths stays as `["tests"]` since both unit/ and integration/ are subdirectories.)

**Step 5: Fix import in test_image_generation.py**

In `tests/unit/services/test_image_generation.py`, the import `from conftest import ...` must still resolve. Since `tests/conftest.py` is at the root and pytest adds `tests/` to sys.path, this should work. Verify.

**Step 6: Run all tests to verify nothing broke**

Run: `pytest -v`
Expected: All 118 tests pass.

**Step 7: Commit**

```bash
git add tests/ pyproject.toml
git commit -m "refactor: reorganize tests into unit/ and integration/ layers"
```

---

### Task 2: Add SSE test helper to conftest

SSE streaming endpoints return `StreamingResponse` with `text/event-stream` content. We need a helper to parse SSE events from httpx responses.

**Files:**
- Modify: `tests/conftest.py`

**Step 1: Add the SSE parsing helper**

Add to `tests/conftest.py`:

```python
import json as _json

def parse_sse_events(text: str) -> list[dict]:
    """Parse SSE text into a list of {event, data} dicts."""
    events = []
    current_event = None
    current_data = []
    for line in text.split("\n"):
        if line.startswith("event:"):
            current_event = line[len("event:"):].strip()
        elif line.startswith("data:"):
            current_data.append(line[len("data:"):].strip())
        elif line.strip() == "" and current_event is not None:
            data_str = "\n".join(current_data)
            try:
                data = _json.loads(data_str)
            except _json.JSONDecodeError:
                data = data_str
            events.append({"event": current_event, "data": data})
            current_event = None
            current_data = []
        elif line.startswith(":"):
            pass  # SSE comment/padding, ignore
    return events
```

**Step 2: Run tests to verify nothing broke**

Run: `pytest -v`
Expected: All 118 tests pass.

**Step 3: Commit**

```bash
git add tests/conftest.py
git commit -m "feat(tests): add SSE event parser helper to conftest"
```

---

### Task 3: Integration test — process-audio SSE happy path

**Files:**
- Modify: `tests/integration/routers/test_recording.py`

**Step 1: Write the test**

Add to `tests/integration/routers/test_recording.py`:

```python
from unittest.mock import patch, MagicMock
from pathlib import Path
from conftest import parse_sse_events


@patch("talekeeper.routers.recording.run_final_diarization", new_callable=AsyncMock)
@patch("talekeeper.routers.recording.audio_to_wav")
@patch("talekeeper.routers.recording.transcribe_chunked")
async def test_process_audio_happy_path(mock_transcribe, mock_wav, mock_diarize, client, tmp_path):
    """process-audio streams progress, segments, phase, done events."""
    from talekeeper.services.transcription import TranscriptSegment, ChunkProgress
    from talekeeper.db import get_db

    # Create campaign + session with audio
    resp = await client.post("/api/campaigns", json={"name": "C"})
    campaign_id = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{campaign_id}/sessions", json={"name": "S", "date": "2025-01-01"})
    session_id = resp.json()["id"]

    # Write a fake audio file and set audio_path
    audio_file = tmp_path / "audio.webm"
    audio_file.write_bytes(b"fake-audio")
    async with get_db() as db:
        await db.execute(
            "UPDATE sessions SET audio_path = ?, status = 'audio_ready' WHERE id = ?",
            (str(audio_file), session_id),
        )

    # Mock transcribe_chunked to yield progress + segments
    mock_transcribe.return_value = iter([
        ChunkProgress(chunk=1, total_chunks=2),
        TranscriptSegment(text="Hello world", start_time=0.0, end_time=1.5),
        ChunkProgress(chunk=2, total_chunks=2),
        TranscriptSegment(text="Goodbye", start_time=1.5, end_time=3.0),
    ])

    # Mock audio_to_wav to return a tmp wav file
    wav_file = tmp_path / "audio.wav"
    wav_file.write_bytes(b"fake-wav")
    mock_wav.return_value = wav_file

    resp = await client.post(f"/api/sessions/{session_id}/process-audio")
    assert resp.status_code == 200

    events = parse_sse_events(resp.text)

    # Should have: progress, segment, progress, segment, phase(diarization), done
    event_types = [e["event"] for e in events]
    assert "progress" in event_types
    assert "segment" in event_types
    assert "phase" in event_types
    assert "done" in event_types

    done_event = next(e for e in events if e["event"] == "done")
    assert done_event["data"]["segments_count"] == 2

    mock_diarize.assert_awaited_once()
```

**Step 2: Run the test**

Run: `pytest tests/integration/routers/test_recording.py::test_process_audio_happy_path -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/routers/test_recording.py
git commit -m "test: add process-audio SSE integration test"
```

---

### Task 4: Integration test — process-audio error cases

**Files:**
- Modify: `tests/integration/routers/test_recording.py`

**Step 1: Write the tests**

```python
async def test_process_audio_session_not_found(client):
    resp = await client.post("/api/sessions/99999/process-audio")
    assert resp.status_code == 404


async def test_process_audio_no_audio(client):
    resp = await client.post("/api/campaigns", json={"name": "C"})
    campaign_id = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{campaign_id}/sessions", json={"name": "S", "date": "2025-01-01"})
    session_id = resp.json()["id"]
    resp = await client.post(f"/api/sessions/{session_id}/process-audio")
    assert resp.status_code == 400
    assert "No audio" in resp.json()["detail"]
```

**Step 2: Run tests**

Run: `pytest tests/integration/routers/test_recording.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/integration/routers/test_recording.py
git commit -m "test: add process-audio error case tests"
```

---

### Task 5: Integration test — download audio

**Files:**
- Modify: `tests/integration/routers/test_recording.py`

**Step 1: Write the tests**

```python
async def test_download_audio(client, tmp_path):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    campaign_id = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{campaign_id}/sessions", json={"name": "S", "date": "2025-01-01"})
    session_id = resp.json()["id"]

    audio_file = tmp_path / "session.mp3"
    audio_file.write_bytes(b"ID3fake-mp3-data")
    async with get_db() as db:
        await db.execute(
            "UPDATE sessions SET audio_path = ? WHERE id = ?",
            (str(audio_file), session_id),
        )

    resp = await client.get(f"/api/sessions/{session_id}/audio")
    assert resp.status_code == 200
    assert b"ID3fake-mp3-data" in resp.content


async def test_download_audio_no_audio(client):
    resp = await client.post("/api/campaigns", json={"name": "C"})
    campaign_id = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{campaign_id}/sessions", json={"name": "S", "date": "2025-01-01"})
    session_id = resp.json()["id"]

    resp = await client.get(f"/api/sessions/{session_id}/audio")
    assert resp.status_code == 404


async def test_download_audio_file_missing(client, tmp_path):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    campaign_id = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{campaign_id}/sessions", json={"name": "S", "date": "2025-01-01"})
    session_id = resp.json()["id"]

    async with get_db() as db:
        await db.execute(
            "UPDATE sessions SET audio_path = ? WHERE id = ?",
            ("/nonexistent/file.mp3", session_id),
        )

    resp = await client.get(f"/api/sessions/{session_id}/audio")
    assert resp.status_code == 404
```

**Step 2: Run and verify**

Run: `pytest tests/integration/routers/test_recording.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/integration/routers/test_recording.py
git commit -m "test: add download-audio integration tests"
```

---

### Task 6: Integration test — upload-audio replaces existing + MIME validation

**Files:**
- Modify: `tests/integration/routers/test_recording.py`

**Step 1: Write the tests**

```python
import io


async def test_upload_audio_invalid_mime(client):
    resp = await client.post("/api/campaigns", json={"name": "C"})
    campaign_id = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{campaign_id}/sessions", json={"name": "S", "date": "2025-01-01"})
    session_id = resp.json()["id"]

    resp = await client.post(
        f"/api/sessions/{session_id}/upload-audio",
        files={"file": ("doc.pdf", io.BytesIO(b"not-audio"), "application/pdf")},
    )
    assert resp.status_code == 400
    assert "audio" in resp.json()["detail"].lower()


async def test_upload_audio_replaces_existing(client, tmp_path):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    campaign_id = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{campaign_id}/sessions", json={"name": "S", "date": "2025-01-01"})
    session_id = resp.json()["id"]

    # Create some transcript data
    async with get_db() as db:
        await db.execute(
            "INSERT INTO speakers (session_id, diarization_label) VALUES (?, ?)",
            (session_id, "SPEAKER_00"),
        )
        await db.execute(
            "INSERT INTO transcript_segments (session_id, text, start_time, end_time) VALUES (?, ?, ?, ?)",
            (session_id, "Old text", 0.0, 1.0),
        )

    # First upload
    resp = await client.post(
        f"/api/sessions/{session_id}/upload-audio",
        files={"file": ("first.mp3", io.BytesIO(b"audio-1"), "audio/mpeg")},
    )
    assert resp.status_code == 200

    # Second upload should replace and clear old segments
    resp = await client.post(
        f"/api/sessions/{session_id}/upload-audio",
        files={"file": ("second.mp3", io.BytesIO(b"audio-2"), "audio/mpeg")},
    )
    assert resp.status_code == 200

    # Old segments and speakers should be gone
    async with get_db() as db:
        segs = await db.execute_fetchall(
            "SELECT * FROM transcript_segments WHERE session_id = ?", (session_id,)
        )
        spks = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE session_id = ?", (session_id,)
        )
    assert len(segs) == 0
    assert len(spks) == 0
```

**Step 2: Run and verify**

Run: `pytest tests/integration/routers/test_recording.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/integration/routers/test_recording.py
git commit -m "test: add upload-audio MIME validation and replacement tests"
```

---

### Task 7: Integration test — retranscribe SSE

**Files:**
- Modify: `tests/integration/routers/test_transcripts.py`

**Step 1: Write the tests**

```python
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path
from conftest import parse_sse_events


@patch("talekeeper.routers.transcripts.run_final_diarization", new_callable=AsyncMock)
@patch("talekeeper.routers.transcripts.webm_to_wav")
@patch("talekeeper.routers.transcripts.transcribe_chunked")
async def test_retranscribe_happy_path(mock_transcribe, mock_wav, mock_diarize, client, tmp_path):
    from talekeeper.services.transcription import TranscriptSegment, ChunkProgress
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    audio_file = tmp_path / "audio.webm"
    audio_file.write_bytes(b"fake-audio")
    async with get_db() as db:
        await db.execute("UPDATE sessions SET audio_path = ?, status = 'completed' WHERE id = ?", (str(audio_file), sid))

    mock_transcribe.return_value = iter([
        ChunkProgress(chunk=1, total_chunks=1),
        TranscriptSegment(text="Retranscribed text", start_time=0.0, end_time=2.0),
    ])
    wav_file = tmp_path / "audio.wav"
    wav_file.write_bytes(b"fake-wav")
    mock_wav.return_value = wav_file

    resp = await client.post(f"/api/sessions/{sid}/retranscribe", json={"model_size": "small"})
    assert resp.status_code == 200

    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert "progress" in event_types
    assert "segment" in event_types
    assert "done" in event_types


async def test_retranscribe_no_audio(client):
    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    resp = await client.post(f"/api/sessions/{sid}/retranscribe", json={"model_size": "small"})
    assert resp.status_code == 400


async def test_retranscribe_session_not_found(client):
    resp = await client.post("/api/sessions/99999/retranscribe", json={"model_size": "small"})
    assert resp.status_code == 404
```

**Step 2: Run and verify**

Run: `pytest tests/integration/routers/test_transcripts.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/integration/routers/test_transcripts.py
git commit -m "test: add retranscribe SSE integration tests"
```

---

### Task 8: Integration test — re-diarize SSE

**Files:**
- Modify: `tests/integration/routers/test_speakers.py`

**Step 1: Write the tests**

```python
from unittest.mock import patch, AsyncMock
from pathlib import Path
from conftest import parse_sse_events


@patch("talekeeper.routers.speakers.run_final_diarization", new_callable=AsyncMock)
@patch("talekeeper.routers.speakers.audio_to_wav")
async def test_re_diarize_happy_path(mock_wav, mock_diarize, client, tmp_path):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    audio_file = tmp_path / "audio.webm"
    audio_file.write_bytes(b"fake-audio")
    async with get_db() as db:
        await db.execute("UPDATE sessions SET audio_path = ?, status = 'completed' WHERE id = ?", (str(audio_file), sid))
        # Add some transcript segments so the done event has a count
        await db.execute(
            "INSERT INTO transcript_segments (session_id, text, start_time, end_time) VALUES (?, ?, ?, ?)",
            (sid, "Hello", 0.0, 1.0),
        )

    wav_file = tmp_path / "audio.wav"
    wav_file.write_bytes(b"fake-wav")
    mock_wav.return_value = wav_file

    resp = await client.post(f"/api/sessions/{sid}/re-diarize", json={"num_speakers": 3})
    assert resp.status_code == 200

    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert "phase" in event_types
    assert "done" in event_types
    mock_diarize.assert_awaited_once()


async def test_re_diarize_session_not_completed(client, tmp_path):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    audio_file = tmp_path / "audio.webm"
    audio_file.write_bytes(b"fake-audio")
    async with get_db() as db:
        await db.execute("UPDATE sessions SET audio_path = ?, status = 'draft' WHERE id = ?", (str(audio_file), sid))

    resp = await client.post(f"/api/sessions/{sid}/re-diarize", json={"num_speakers": 3})
    assert resp.status_code == 409


async def test_re_diarize_no_audio(client):
    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    resp = await client.post(f"/api/sessions/{sid}/re-diarize", json={"num_speakers": 3})
    assert resp.status_code == 400
```

**Step 2: Run and verify**

Run: `pytest tests/integration/routers/test_speakers.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/integration/routers/test_speakers.py
git commit -m "test: add re-diarize SSE integration tests"
```

---

### Task 9: Integration test — generate-image SSE

**Files:**
- Modify: `tests/integration/routers/test_images.py`

**Step 1: Write the tests**

```python
from unittest.mock import patch, AsyncMock
from conftest import parse_sse_events


@patch("talekeeper.routers.images.generate_session_image", new_callable=AsyncMock)
@patch("talekeeper.routers.images.craft_scene_description", new_callable=AsyncMock)
@patch("talekeeper.routers.images.image_client.health_check", new_callable=AsyncMock, return_value={"status": "ok"})
@patch("talekeeper.routers.images.image_client.resolve_config", new_callable=AsyncMock, return_value={"base_url": "http://test", "api_key": None, "model": "sdxl"})
@patch("talekeeper.routers.images.llm_client.health_check", new_callable=AsyncMock, return_value={"status": "ok"})
@patch("talekeeper.routers.images.llm_client.resolve_config", new_callable=AsyncMock, return_value={"base_url": "http://test", "api_key": None, "model": "llama3"})
async def test_generate_image_with_prompt(
    mock_llm_config, mock_llm_health, mock_img_config, mock_img_health,
    mock_craft, mock_gen_img, client
):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    mock_gen_img.return_value = {
        "id": 1, "session_id": sid, "file_path": "/img/1.png",
        "prompt": "A dragon", "scene_description": None,
        "model_used": "sdxl", "generated_at": "2025-01-01",
    }

    resp = await client.post(f"/api/sessions/{sid}/generate-image", json={"prompt": "A dragon"})
    assert resp.status_code == 200

    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert "phase" in event_types
    assert "done" in event_types

    # Should NOT have called craft_scene since prompt was provided
    mock_craft.assert_not_awaited()
    mock_gen_img.assert_awaited_once()


@patch("talekeeper.routers.images.generate_session_image", new_callable=AsyncMock)
@patch("talekeeper.routers.images.craft_scene_description", new_callable=AsyncMock, return_value="A dark tavern")
@patch("talekeeper.routers.images.image_client.health_check", new_callable=AsyncMock, return_value={"status": "ok"})
@patch("talekeeper.routers.images.image_client.resolve_config", new_callable=AsyncMock, return_value={"base_url": "http://test", "api_key": None, "model": "sdxl"})
@patch("talekeeper.routers.images.llm_client.health_check", new_callable=AsyncMock, return_value={"status": "ok"})
@patch("talekeeper.routers.images.llm_client.resolve_config", new_callable=AsyncMock, return_value={"base_url": "http://test", "api_key": None, "model": "llama3"})
async def test_generate_image_crafts_scene_when_no_prompt(
    mock_llm_config, mock_llm_health, mock_img_config, mock_img_health,
    mock_craft, mock_gen_img, client
):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    # Add a summary so _get_session_content returns something
    async with get_db() as db:
        await db.execute(
            "INSERT INTO summaries (session_id, type, content) VALUES (?, ?, ?)",
            (sid, "full", "The party fought a dragon"),
        )

    mock_gen_img.return_value = {
        "id": 1, "session_id": sid, "file_path": "/img/1.png",
        "prompt": "A dark tavern", "scene_description": "A dark tavern",
        "model_used": "sdxl", "generated_at": "2025-01-01",
    }

    resp = await client.post(f"/api/sessions/{sid}/generate-image", json={"prompt": None})
    assert resp.status_code == 200

    events = parse_sse_events(resp.text)
    event_types = [e["event"] for e in events]
    assert "phase" in event_types
    assert "done" in event_types
    mock_craft.assert_awaited_once()


async def test_generate_image_session_not_found(client):
    resp = await client.post("/api/sessions/99999/generate-image", json={"prompt": "test"})
    assert resp.status_code == 404


async def test_get_image_file_not_found(client):
    resp = await client.get("/api/images/99999/file")
    assert resp.status_code == 404


async def test_delete_all_session_images(client):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    # Insert image metadata
    async with get_db() as db:
        await db.execute(
            "INSERT INTO session_images (session_id, file_path, prompt) VALUES (?, ?, ?)",
            (sid, "/tmp/fake.png", "test prompt"),
        )

    resp = await client.delete(f"/api/sessions/{sid}/images")
    assert resp.status_code == 200
    assert resp.json()["deleted"] >= 0
```

**Step 2: Run and verify**

Run: `pytest tests/integration/routers/test_images.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/integration/routers/test_images.py
git commit -m "test: add generate-image SSE and image management integration tests"
```

---

### Task 10: Integration test — roster upload-sheet, import-url, refresh-sheet

**Files:**
- Modify: `tests/integration/routers/test_roster.py`

**Step 1: Write the tests**

```python
import io
from unittest.mock import patch, MagicMock, AsyncMock


async def _create_roster_entry(client):
    """Helper: create campaign + roster entry, return (campaign_id, entry_id)."""
    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/roster", json={
        "player_name": "Alice", "character_name": "Thorn", "description": "",
    })
    return cid, resp.json()["id"]


@patch("talekeeper.routers.roster.llm_client.generate", new_callable=AsyncMock, return_value="A tall elven ranger")
@patch("talekeeper.routers.roster.llm_client.health_check", new_callable=AsyncMock, return_value={"status": "ok"})
@patch("talekeeper.routers.roster.llm_client.resolve_config", new_callable=AsyncMock, return_value={"base_url": "http://test", "api_key": None, "model": "llama3"})
@patch("talekeeper.routers.roster.fitz")
async def test_upload_sheet_pdf(mock_fitz, mock_config, mock_health, mock_generate, client):
    _, entry_id = await _create_roster_entry(client)

    mock_doc = MagicMock()
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Character Name: Thorn\nRace: Elf\nClass: Ranger"
    mock_doc.__iter__ = lambda self: iter([mock_page])
    mock_doc.__enter__ = lambda self: self
    mock_doc.__exit__ = MagicMock(return_value=False)
    mock_fitz.open.return_value = mock_doc

    resp = await client.post(
        f"/api/roster/{entry_id}/upload-sheet",
        files={"file": ("sheet.pdf", io.BytesIO(b"fake-pdf"), "application/pdf")},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "A tall elven ranger"


async def test_upload_sheet_non_pdf(client):
    _, entry_id = await _create_roster_entry(client)

    resp = await client.post(
        f"/api/roster/{entry_id}/upload-sheet",
        files={"file": ("sheet.txt", io.BytesIO(b"text"), "text/plain")},
    )
    assert resp.status_code == 400


@patch("talekeeper.routers.roster.llm_client.generate", new_callable=AsyncMock, return_value="A dwarven cleric")
@patch("talekeeper.routers.roster.llm_client.health_check", new_callable=AsyncMock, return_value={"status": "ok"})
@patch("talekeeper.routers.roster.llm_client.resolve_config", new_callable=AsyncMock, return_value={"base_url": "http://test", "api_key": None, "model": "llama3"})
@patch("talekeeper.routers.roster.httpx.AsyncClient")
async def test_import_url(mock_httpx_cls, mock_config, mock_health, mock_generate, client):
    _, entry_id = await _create_roster_entry(client)

    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "<html><body>Character Name: Brunk, Race: Dwarf, Class: Cleric</body></html>"
    mock_response.raise_for_status = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    mock_httpx_cls.return_value = mock_client

    resp = await client.post(
        f"/api/roster/{entry_id}/import-url",
        json={"url": "https://example.com/character"},
    )
    assert resp.status_code == 200
    assert resp.json()["description"] == "A dwarven cleric"


async def test_refresh_sheet_no_data(client):
    _, entry_id = await _create_roster_entry(client)

    resp = await client.post(f"/api/roster/{entry_id}/refresh-sheet")
    assert resp.status_code == 400
```

**Step 2: Run and verify**

Run: `pytest tests/integration/routers/test_roster.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/integration/routers/test_roster.py
git commit -m "test: add roster upload-sheet, import-url, refresh-sheet integration tests"
```

---

### Task 11: Integration test — exports (PDF, POV-all, email)

**Files:**
- Modify: `tests/integration/routers/test_exports.py`

**Step 1: Write the tests**

```python
from unittest.mock import patch, MagicMock


@patch("talekeeper.routers.exports.weasyprint")
async def test_export_pdf_printable(mock_wp, client):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO summaries (session_id, type, content) VALUES (?, ?, ?)",
            (sid, "full", "The heroes saved the village"),
        )
        summary_id = cursor.lastrowid

    mock_html = MagicMock()
    mock_html.write_pdf.return_value = b"%PDF-printable"
    mock_wp.HTML.return_value = mock_html

    resp = await client.get(f"/api/summaries/{summary_id}/export/pdf?printable=true")
    assert resp.status_code == 200
    assert resp.content == b"%PDF-printable"


@patch("talekeeper.routers.exports.weasyprint")
async def test_export_pov_all_zip(mock_wp, client):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    async with get_db() as db:
        await db.execute(
            "INSERT INTO speakers (session_id, diarization_label, player_name, character_name) VALUES (?, ?, ?, ?)",
            (sid, "SPEAKER_00", "Alice", "Thorn"),
        )
        speaker_rows = await db.execute_fetchall("SELECT id FROM speakers WHERE session_id = ?", (sid,))
        speaker_id = speaker_rows[0]["id"]
        await db.execute(
            "INSERT INTO summaries (session_id, type, speaker_id, content) VALUES (?, ?, ?, ?)",
            (sid, "pov", speaker_id, "Thorn fought bravely"),
        )

    mock_html = MagicMock()
    mock_html.write_pdf.return_value = b"%PDF-pov"
    mock_wp.HTML.return_value = mock_html

    resp = await client.get(f"/api/sessions/{sid}/export/pov-all")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"


async def test_export_pov_all_no_summaries(client):
    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    resp = await client.get(f"/api/sessions/{sid}/export/pov-all")
    assert resp.status_code == 404


@patch("talekeeper.routers.exports.smtplib")
async def test_send_email(mock_smtplib, client):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO summaries (session_id, type, content) VALUES (?, ?, ?)",
            (sid, "full", "The party saved the day"),
        )
        summary_id = cursor.lastrowid

        # Configure SMTP settings
        for key, val in [
            ("smtp_host", "smtp.test.com"),
            ("smtp_port", "587"),
            ("smtp_user", "user@test.com"),
            ("smtp_password", "secret"),
            ("smtp_from", "from@test.com"),
        ]:
            await db.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val)
            )

    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value = mock_server

    resp = await client.post(
        f"/api/summaries/{summary_id}/send-email",
        json={"to": "player@test.com"},
    )
    assert resp.status_code == 200
    mock_server.send_message.assert_called_once()


async def test_send_email_smtp_not_configured(client):
    from talekeeper.db import get_db

    resp = await client.post("/api/campaigns", json={"name": "C"})
    cid = resp.json()["id"]
    resp = await client.post(f"/api/campaigns/{cid}/sessions", json={"name": "S", "date": "2025-01-01"})
    sid = resp.json()["id"]

    async with get_db() as db:
        cursor = await db.execute(
            "INSERT INTO summaries (session_id, type, content) VALUES (?, ?, ?)",
            (sid, "full", "Summary text"),
        )
        summary_id = cursor.lastrowid

    resp = await client.post(
        f"/api/summaries/{summary_id}/send-email",
        json={"to": "player@test.com"},
    )
    assert resp.status_code == 400
```

**Step 2: Run and verify**

Run: `pytest tests/integration/routers/test_exports.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/integration/routers/test_exports.py
git commit -m "test: add PDF export, POV-all ZIP, and email integration tests"
```

---

### Task 12: Unit test — diarization service (expand coverage)

**Files:**
- Modify: `tests/unit/services/test_diarization.py`

**Step 1: Write new tests**

```python
@patch("talekeeper.services.diarization._extract_windowed_embeddings")
@patch("talekeeper.services.diarization.AgglomerativeClustering")
def test_diarize_with_num_speakers(mock_cluster_cls, mock_extract):
    """diarize() uses n_clusters when num_speakers is specified."""
    from talekeeper.services.diarization import diarize

    mock_extract.return_value = (
        np.zeros((4, 192)),
        [(0.0, 1.0), (1.0, 2.0), (2.0, 3.0), (3.0, 4.0)],
    )
    mock_cluster = MagicMock()
    mock_cluster.fit_predict.return_value = np.array([0, 0, 1, 1])
    mock_cluster_cls.return_value = mock_cluster

    segments = diarize("fake.wav", num_speakers=2)
    assert len(segments) == 4
    # Verify clustering was called with n_clusters=2
    mock_cluster_cls.assert_called_once()
    call_kwargs = mock_cluster_cls.call_args
    assert call_kwargs[1].get("n_clusters") == 2 or call_kwargs.kwargs.get("n_clusters") == 2


@patch("talekeeper.services.diarization._extract_windowed_embeddings")
@patch("talekeeper.services.diarization.AgglomerativeClustering")
def test_diarize_without_num_speakers(mock_cluster_cls, mock_extract):
    """diarize() uses distance_threshold when num_speakers is not specified."""
    from talekeeper.services.diarization import diarize

    mock_extract.return_value = (
        np.zeros((3, 192)),
        [(0.0, 1.5), (1.5, 3.0), (3.0, 4.5)],
    )
    mock_cluster = MagicMock()
    mock_cluster.fit_predict.return_value = np.array([0, 1, 0])
    mock_cluster_cls.return_value = mock_cluster

    segments = diarize("fake.wav")
    assert len(segments) == 3
    # Verify distance_threshold was used (not n_clusters)
    call_kwargs = mock_cluster_cls.call_args
    assert "distance_threshold" in str(call_kwargs)
```

**Step 2: Run and verify**

Run: `pytest tests/unit/services/test_diarization.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/unit/services/test_diarization.py
git commit -m "test: add diarize clustering unit tests"
```

---

### Task 13: Unit test — audio service (expand edge cases)

**Files:**
- Modify: `tests/unit/services/test_audio.py`

**Step 1: Write new tests**

```python
@patch("talekeeper.services.audio.AudioSegment.from_file")
def test_split_audio_to_chunks_multiple(mock_from_file, tmp_path):
    """split_audio_to_chunks splits long audio into overlapping chunks."""
    from talekeeper.services.audio import split_audio_to_chunks

    mock_audio = MagicMock()
    mock_audio.__len__ = MagicMock(return_value=180_000)  # 3 minutes
    mock_chunk = MagicMock()
    mock_chunk.export = MagicMock()
    mock_audio.__getitem__ = MagicMock(return_value=mock_chunk)
    mock_from_file.return_value = mock_audio

    src = tmp_path / "long.wav"
    src.write_bytes(b"fake")

    chunks = list(split_audio_to_chunks(src, chunk_duration_ms=60_000, overlap_ms=5_000))
    # 180s audio / 60s chunks with 5s overlap = should produce multiple chunks
    assert len(chunks) > 1
    for idx, wav_path, start_ms, end_ms in chunks:
        assert isinstance(idx, int)
        assert end_ms > start_ms


def test_compute_primary_zone_middle_chunk():
    """compute_primary_zone returns trimmed zone for middle chunks."""
    from talekeeper.services.audio import compute_primary_zone

    start, end = compute_primary_zone(
        chunk_index=1, start_ms=55_000, end_ms=120_000,
        total_chunks=3, overlap_ms=5_000,
    )
    # Middle chunk should have both edges trimmed
    assert start >= 55.0
    assert end <= 120.0
```

**Step 2: Run and verify**

Run: `pytest tests/unit/services/test_audio.py -v`
Expected: All pass.

**Step 3: Commit**

```bash
git add tests/unit/services/test_audio.py
git commit -m "test: add audio chunking and zone calculation unit tests"
```

---

### Task 14: Run full suite and coverage report

**Step 1: Run all tests**

```bash
pytest -v
```
Expected: All tests pass (original 118 + new tests).

**Step 2: Run coverage**

```bash
pytest --cov=talekeeper --cov-report=term-missing
```
Expected: Coverage significantly improved from 53%. Target modules:
- `recording.py`: 21% → ~70%+
- `diarization.py`: 22% → ~40%+
- `transcripts.py`: 34% → ~80%+
- `roster.py`: 50% → ~75%+
- `images.py`: 50% → ~75%+
- `exports.py`: 63% → ~80%+
- `speakers.py`: 67% → ~80%+

**Step 3: Commit**

If everything passes:
```bash
git add -A
git commit -m "test: complete black-box test coverage improvement"
```

---

### Task 15: Fix any failing tests and iterate

This is a catch-all task. After Task 14, review any failures:

- SSE tests may need adjustments to mock patch paths (lazy imports in routers use `from module import func` inside the function body, so patch the import location in the router module, not the service module)
- Some tests may need additional DB seeding
- Coverage targets may need additional tests for uncovered branches

Fix issues, re-run, commit until green.

---

## Running by layer

```bash
pytest tests/unit -v             # unit layer only
pytest tests/integration -v      # integration layer only
pytest -v                        # everything
pytest --cov=talekeeper          # coverage report
```
