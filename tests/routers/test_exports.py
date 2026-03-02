"""Tests for export and sharing API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock

from talekeeper.db import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _seed(db) -> dict:
    """Create campaign -> session -> summary + segments for export. Return IDs."""
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

    cursor = await db.execute(
        "INSERT INTO summaries (session_id, type, content, model_used) "
        "VALUES (?, 'full', 'The heroes fought bravely.', 'test-model')",
        (session_id,),
    )
    summary_id = cursor.lastrowid

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
        "summary_id": summary_id,
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("weasyprint.HTML")
async def test_export_pdf(mock_html_cls, client: AsyncClient) -> None:
    """GET /api/summaries/{id}/export/pdf returns a PDF with correct content-type."""
    mock_html_cls.return_value.write_pdf.return_value = b"fake-pdf-bytes"

    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/summaries/{ids['summary_id']}/export/pdf")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == b"fake-pdf-bytes"
    mock_html_cls.assert_called_once()


@pytest.mark.asyncio
async def test_export_text(client: AsyncClient) -> None:
    """GET /api/summaries/{id}/export/text returns plain text with correct content-type."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/summaries/{ids['summary_id']}/export/text")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text
    assert "Session Chronicle" in body
    assert "The heroes fought bravely." in body


@pytest.mark.asyncio
async def test_export_transcript(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/export/transcript returns formatted transcript text."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/sessions/{ids['session_id']}/export/transcript")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    body = resp.text
    assert "Transcript: Session 1" in body
    assert "We should head north." in body
    assert "Gandalf" in body


@pytest.mark.asyncio
async def test_email_content(client: AsyncClient) -> None:
    """GET /api/summaries/{id}/email-content returns subject, body, and meta."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/summaries/{ids['summary_id']}/email-content")
    assert resp.status_code == 200
    data = resp.json()
    assert "subject" in data
    assert "body" in data
    assert "meta" in data
    assert data["subject"] == "Session Chronicle"
    assert "heroes fought" in data["body"]


# ---------------------------------------------------------------------------
# Batch export (summaries-all) tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@patch("weasyprint.HTML")
async def test_export_summaries_all(mock_html_cls, client: AsyncClient) -> None:
    """GET /api/sessions/{id}/export/summaries-all returns ZIP with all summary PDFs."""
    mock_html_cls.return_value.write_pdf.return_value = b"fake-pdf-bytes"

    async with get_db() as db:
        ids = await _seed(db)
        # Add a POV summary
        await db.execute(
            "INSERT INTO summaries (session_id, type, speaker_id, content, model_used) "
            "VALUES (?, 'pov', ?, 'Gandalf saw the battle.', 'test-model')",
            (ids["session_id"], ids["speaker_id"]),
        )
        await db.commit()

    resp = await client.get(f"/api/sessions/{ids['session_id']}/export/summaries-all")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    import zipfile as zf
    buf = __import__("io").BytesIO(resp.content)
    with zf.ZipFile(buf) as z:
        names = z.namelist()
        assert "session-chronicle.pdf" in names
        assert "gandalf-pov.pdf" in names
        assert len(names) == 2


@pytest.mark.asyncio
@patch("weasyprint.HTML")
async def test_export_summaries_all_printable(mock_html_cls, client: AsyncClient) -> None:
    """GET /api/sessions/{id}/export/summaries-all?printable=true uses printable styling."""
    mock_html_cls.return_value.write_pdf.return_value = b"fake-pdf-bytes"

    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(f"/api/sessions/{ids['session_id']}/export/summaries-all?printable=true")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"

    # Verify the HTML passed to weasyprint contains printable styling
    call_args = mock_html_cls.call_args
    html_string = call_args[1]["string"] if "string" in call_args[1] else call_args[0][0]
    assert "background: #fff;" in html_string


@pytest.mark.asyncio
async def test_export_summaries_all_empty(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/export/summaries-all returns 404 when no summaries exist."""
    async with get_db() as db:
        cursor = await db.execute("INSERT INTO campaigns (name) VALUES ('C')")
        cid = cursor.lastrowid
        cursor = await db.execute(
            "INSERT INTO sessions (campaign_id, name, date) VALUES (?, 'S', '2025-01-01')",
            (cid,),
        )
        sid = cursor.lastrowid
        await db.commit()

    resp = await client.get(f"/api/sessions/{sid}/export/summaries-all")
    assert resp.status_code == 404
