"""Tests for the Gemini PDF transcript import service."""

import pytest
from unittest.mock import patch

from conftest import create_campaign, create_session

from talekeeper.services.transcript_import import (
    _parse_timestamp,
    parse_gemini_transcript,
    import_transcript_from_pdf,
    ParsedTurn,
)


# ---- 3.1 Timestamp parsing ----

def test_parse_timestamp_m_ss():
    assert _parse_timestamp("1:30") == 90.0


def test_parse_timestamp_h_mm_ss():
    assert _parse_timestamp("1:02:03") == 3723.0


def test_parse_timestamp_zero():
    assert _parse_timestamp("0:00") == 0.0


def test_parse_timestamp_invalid():
    assert _parse_timestamp("bad") == 0.0


def test_parse_timestamp_empty():
    assert _parse_timestamp("") == 0.0


# ---- 3.2 Parser tests ----

SIMPLE_TRANSCRIPT = """\
Alice  0:00
Hello everyone.
Bob  0:15
Hi there.
Alice  0:30
Let us begin.
"""


def test_parse_three_turns():
    turns = parse_gemini_transcript(SIMPLE_TRANSCRIPT)
    assert len(turns) == 3
    assert turns[0].speaker == "Alice"
    assert turns[0].start_time == 0.0
    assert turns[0].text == "Hello everyone."
    assert turns[1].speaker == "Bob"
    assert turns[1].start_time == 15.0
    assert turns[2].speaker == "Alice"
    assert turns[2].start_time == 30.0


def test_parse_end_times():
    turns = parse_gemini_transcript(SIMPLE_TRANSCRIPT)
    assert turns[0].end_time == 15.0
    assert turns[1].end_time == 30.0
    # last turn gets +30s
    assert turns[2].end_time == turns[2].start_time + 30.0


def test_parse_preamble_stripped():
    text = "Meeting notes\nSome metadata\nTranscript\n" + SIMPLE_TRANSCRIPT
    from talekeeper.services.transcript_import import _find_transcript_section
    section = _find_transcript_section(text)
    turns = parse_gemini_transcript(section)
    # preamble lines before "Transcript" heading should not appear as speakers
    assert all(t.speaker in ("Alice", "Bob") for t in turns)


def test_parse_empty_input():
    turns = parse_gemini_transcript("")
    assert turns == []


def test_parse_single_turn_gets_plus30():
    text = "Solo  1:00\nSpeaking alone.\n"
    turns = parse_gemini_transcript(text)
    assert len(turns) == 1
    assert turns[0].end_time == 60.0 + 30.0


def test_parse_multiline_dialogue_joined():
    text = "Alice  0:00\nLine one.\nLine two.\nLine three.\n"
    turns = parse_gemini_transcript(text)
    assert turns[0].text == "Line one. Line two. Line three."


# ---- 3.3 DB integration tests ----

FAKE_PDF_TEXT = """\
Transcript
Alice  0:00
Hello everyone.
Bob  0:15
Hi there.
"""


@pytest.mark.asyncio
async def test_import_clears_existing_data(db):
    campaign_id = await create_campaign(db)
    session_id = await create_session(db, campaign_id)

    # Pre-populate with old data
    await db.execute(
        "INSERT INTO speakers (session_id, diarization_label) VALUES (?, 'OLD')", (session_id,)
    )
    await db.execute(
        "INSERT INTO transcript_segments (session_id, text, start_time, end_time) VALUES (?, 'old', 0, 1)",
        (session_id,),
    )
    await db.commit()

    with patch(
        "talekeeper.services.transcript_import._extract_pdf_text",
        return_value=FAKE_PDF_TEXT,
    ):
        await import_transcript_from_pdf(session_id, b"fake")

    rows = await db.execute_fetchall(
        "SELECT diarization_label FROM speakers WHERE session_id = ?", (session_id,)
    )
    labels = [r["diarization_label"] for r in rows]
    assert "OLD" not in labels
    assert set(labels) == {"Alice", "Bob"}


@pytest.mark.asyncio
async def test_import_sets_status_completed(db):
    campaign_id = await create_campaign(db)
    session_id = await create_session(db, campaign_id, status="draft")

    with patch(
        "talekeeper.services.transcript_import._extract_pdf_text",
        return_value=FAKE_PDF_TEXT,
    ):
        await import_transcript_from_pdf(session_id, b"fake")

    rows = await db.execute_fetchall(
        "SELECT status FROM sessions WHERE id = ?", (session_id,)
    )
    assert rows[0]["status"] == "completed"


@pytest.mark.asyncio
async def test_import_creates_speakers_with_correct_names(db):
    campaign_id = await create_campaign(db)
    session_id = await create_session(db, campaign_id)

    with patch(
        "talekeeper.services.transcript_import._extract_pdf_text",
        return_value=FAKE_PDF_TEXT,
    ):
        result = await import_transcript_from_pdf(session_id, b"fake")

    assert result["speakers_count"] == 2
    rows = await db.execute_fetchall(
        "SELECT diarization_label, player_name FROM speakers WHERE session_id = ?",
        (session_id,),
    )
    for row in rows:
        assert row["diarization_label"] == row["player_name"]
    names = {r["player_name"] for r in rows}
    assert names == {"Alice", "Bob"}


@pytest.mark.asyncio
async def test_import_invalid_session_raises_value_error(db):
    with patch(
        "talekeeper.services.transcript_import._extract_pdf_text",
        return_value=FAKE_PDF_TEXT,
    ):
        with pytest.raises(ValueError, match="not found"):
            await import_transcript_from_pdf(99999, b"fake")
