"""Gemini PDF transcript import service."""

import re
from dataclasses import dataclass, field

import fitz  # PyMuPDF

from talekeeper.db import get_db

SPEAKER_RE = re.compile(r"^(.+?)\s{2,}(\d+:\d{2}(?::\d{2})?)\s*$")


@dataclass
class ParsedTurn:
    speaker: str
    start_time: float
    text: str
    end_time: float = field(default=0.0)


def _parse_timestamp(ts: str) -> float:
    """Parse M:SS or H:MM:SS timestamp string to seconds. Returns 0.0 on failure."""
    try:
        parts = ts.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    except (ValueError, IndexError):
        pass
    return 0.0


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes. Raises ValueError if empty."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    pages = [page.get_text() for page in doc]
    text = "\n".join(pages)
    if not text.strip():
        raise ValueError("Could not extract text from PDF")
    return text


def _find_transcript_section(full_text: str) -> str:
    """Find the transcript section starting at the 'Transcript' heading."""
    match = re.search(r"^Transcript\s*$", full_text, re.IGNORECASE | re.MULTILINE)
    if match:
        return full_text[match.end():]
    return full_text


def parse_gemini_transcript(text: str) -> list[ParsedTurn]:
    """Parse Gemini transcript text into a list of ParsedTurn objects."""
    turns: list[ParsedTurn] = []
    current_speaker: str | None = None
    current_start: float = 0.0
    current_lines: list[str] = []

    for line in text.splitlines():
        m = SPEAKER_RE.match(line)
        if m:
            # Save previous turn
            if current_speaker is not None and current_lines:
                turns.append(ParsedTurn(
                    speaker=current_speaker,
                    start_time=current_start,
                    text=" ".join(current_lines),
                ))
            current_speaker = m.group(1).strip()
            current_start = _parse_timestamp(m.group(2))
            current_lines = []
        elif current_speaker is not None:
            stripped = line.strip()
            if stripped:
                current_lines.append(stripped)

    # Save last turn
    if current_speaker is not None and current_lines:
        turns.append(ParsedTurn(
            speaker=current_speaker,
            start_time=current_start,
            text=" ".join(current_lines),
        ))

    # Assign end times
    for i, turn in enumerate(turns):
        if i + 1 < len(turns):
            turn.end_time = turns[i + 1].start_time
        else:
            turn.end_time = turn.start_time + 30.0

    return turns


async def import_transcript_from_pdf(session_id: int, pdf_bytes: bytes) -> dict:
    """Import a Gemini PDF transcript into the database for the given session."""
    text = _extract_pdf_text(pdf_bytes)
    section = _find_transcript_section(text)
    turns = parse_gemini_transcript(section)

    if not turns:
        raise ValueError("No transcript turns found in PDF")

    async with get_db() as db:
        # Verify session exists
        rows = await db.execute_fetchall(
            "SELECT id FROM sessions WHERE id = ?", (session_id,)
        )
        if not rows:
            raise ValueError(f"Session {session_id} not found")

        # Clear existing data
        await db.execute(
            "DELETE FROM transcript_segments WHERE session_id = ?", (session_id,)
        )
        await db.execute(
            "DELETE FROM speakers WHERE session_id = ?", (session_id,)
        )

        # Insert unique speakers
        speaker_ids: dict[str, int] = {}
        for turn in turns:
            if turn.speaker not in speaker_ids:
                cursor = await db.execute(
                    "INSERT INTO speakers (session_id, diarization_label, player_name) VALUES (?, ?, ?)",
                    (session_id, turn.speaker, turn.speaker),
                )
                speaker_ids[turn.speaker] = cursor.lastrowid  # type: ignore[assignment]

        # Insert transcript segments
        for turn in turns:
            await db.execute(
                "INSERT INTO transcript_segments (session_id, speaker_id, text, start_time, end_time) VALUES (?, ?, ?, ?, ?)",
                (session_id, speaker_ids[turn.speaker], turn.text, turn.start_time, turn.end_time),
            )

        # Mark session as completed
        await db.execute(
            "UPDATE sessions SET status = 'completed', updated_at = datetime('now') WHERE id = ?",
            (session_id,),
        )

    return {"segments_count": len(turns), "speakers_count": len(speaker_ids)}
