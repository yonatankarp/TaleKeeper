"""Tests for export and sharing API endpoints."""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock

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


@pytest.mark.asyncio
@patch("weasyprint.HTML")
async def test_export_pdf_printable(mock_html_cls, client: AsyncClient) -> None:
    """GET /api/summaries/{id}/export/pdf?printable=true returns a printable PDF."""
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-printable"

    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.get(
        f"/api/summaries/{ids['summary_id']}/export/pdf?printable=true"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content == b"%PDF-printable"
    mock_html_cls.assert_called_once()


@pytest.mark.asyncio
@patch("weasyprint.HTML")
async def test_export_pov_all_zip(mock_html_cls, client: AsyncClient) -> None:
    """GET /api/sessions/{id}/export/pov-all returns a ZIP with POV PDFs."""
    mock_html_cls.return_value.write_pdf.return_value = b"%PDF-pov"

    async with get_db() as db:
        ids = await _seed(db)
        # Add a POV summary tied to the speaker
        await db.execute(
            "INSERT INTO summaries (session_id, speaker_id, type, content, model_used) "
            "VALUES (?, ?, 'pov', 'Gandalf saw the battle unfold.', 'test-model')",
            (ids["session_id"], ids["speaker_id"]),
        )
        await db.commit()

    resp = await client.get(
        f"/api/sessions/{ids['session_id']}/export/pov-all"
    )
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/zip"
    # Verify the ZIP contains at least one file
    import zipfile, io
    zf = zipfile.ZipFile(io.BytesIO(resp.content))
    names = zf.namelist()
    assert len(names) >= 1
    assert any(name.endswith("-pov.pdf") for name in names)


@pytest.mark.asyncio
async def test_export_pov_all_no_summaries(client: AsyncClient) -> None:
    """GET /api/sessions/{id}/export/pov-all returns 404 when no POV summaries exist."""
    async with get_db() as db:
        # _seed creates a 'full' summary, not 'pov'
        ids = await _seed(db)

    resp = await client.get(
        f"/api/sessions/{ids['session_id']}/export/pov-all"
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
@patch("talekeeper.routers.exports.smtplib")
async def test_send_email(mock_smtplib, client: AsyncClient) -> None:
    """POST /api/summaries/{id}/send-email sends an email via SMTP."""
    mock_server = MagicMock()
    mock_smtplib.SMTP.return_value.__enter__ = MagicMock(return_value=mock_server)
    mock_smtplib.SMTP.return_value.__exit__ = MagicMock(return_value=False)

    async with get_db() as db:
        ids = await _seed(db)
        # Insert SMTP settings
        for key, value in [
            ("smtp_host", "smtp.test.com"),
            ("smtp_port", "587"),
            ("smtp_username", "user@test.com"),
            ("smtp_password", "secret"),
            ("smtp_sender", "noreply@test.com"),
        ]:
            await db.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)", (key, value)
            )
        await db.commit()

    resp = await client.post(
        f"/api/summaries/{ids['summary_id']}/send-email",
        json={"to": "player@test.com"},
    )
    assert resp.status_code == 200
    assert resp.json()["sent"] is True
    mock_server.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_smtp_not_configured(client: AsyncClient) -> None:
    """POST /api/summaries/{id}/send-email returns 400 when SMTP is not configured."""
    async with get_db() as db:
        ids = await _seed(db)

    resp = await client.post(
        f"/api/summaries/{ids['summary_id']}/send-email",
        json={"to": "player@test.com"},
    )
    assert resp.status_code == 400
