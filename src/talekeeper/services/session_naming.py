"""Session name generation service using LLM."""

import logging
import re

from talekeeper.db import get_db
from talekeeper.services import llm_client
from talekeeper.services.summarization import format_transcript

logger = logging.getLogger(__name__)

_SESSION_NAME_SYSTEM = """You are naming tabletop RPG sessions.
Generate a short, catchy title (2-6 words) that captures the MAIN event, turning point, or climax of the session.
Output ONLY the title itself. No quotes, no preamble, no explanation.
IMPORTANT: Write the title in the same language as the input. If the text is in
Hebrew, write in Hebrew. If in English, write in English. Match the language of the source material.
Examples of good titles: "The Dragon's Lair", "Betrayal at Blackwater", "Into the Feywild"."""

_SESSION_NAME_PROMPT_SUMMARY = """Based on this session summary, generate a catchy title (2-6 words)
that captures the central event or turning point.

SUMMARY:
{text}

Title:"""

_SESSION_NAME_PROMPT_TRANSCRIPT = """Below are excerpts from a tabletop RPG session transcript.
The MIDDLE and END sections are the most important — they contain the main action and climax.
The BEGINNING is just context/setup.

Generate a catchy session title (2-6 words) based on the central event or turning point.

TRANSCRIPT:
{text}

Title:"""

_AUTO_NAME_PATTERN = re.compile(r"^Session \d+(?:\s*:.+)?$")

# Sampling limits for long transcripts
_SAMPLE_THRESHOLD = 6000
_SAMPLE_BEGIN = 1000
_SAMPLE_MIDDLE = 2000
_SAMPLE_END = 2500


def _is_auto_named(name: str) -> bool:
    """Check if a session name matches the auto-assigned 'Session N' or 'Session N: ...' pattern."""
    return bool(_AUTO_NAME_PATTERN.match(name.strip()))


def _sample_transcript(text: str) -> str:
    """Sample beginning, middle, and end of long transcripts.

    Weights the middle and end more heavily since that's where the main
    action and climax typically occur.
    """
    if len(text) <= _SAMPLE_THRESHOLD:
        return text
    mid = len(text) // 2
    mid_start = mid - _SAMPLE_MIDDLE // 2
    return (
        f"[BEGINNING]\n{text[:_SAMPLE_BEGIN]}"
        f"\n\n[MIDDLE]\n{text[mid_start:mid_start + _SAMPLE_MIDDLE]}"
        f"\n\n[END]\n{text[-_SAMPLE_END:]}"
    )


async def generate_session_name(text: str, *, from_summary: bool = False) -> str:
    """Generate a catchy session title from a summary or transcript.

    Args:
        text: Summary content or formatted transcript text.
        from_summary: If True, use the shorter summary prompt.

    Returns a 2-6 word title string.
    """
    config = await llm_client.resolve_config()

    if from_summary:
        prompt = _SESSION_NAME_PROMPT_SUMMARY.format(text=text)
    else:
        sampled = _sample_transcript(text)
        prompt = _SESSION_NAME_PROMPT_TRANSCRIPT.format(text=sampled)

    result = await llm_client.generate(
        base_url=config["base_url"],
        api_key=config["api_key"],
        model=config["model"],
        prompt=prompt,
        system=_SESSION_NAME_SYSTEM,
    )

    # Clean up: strip quotes and whitespace
    title = result.strip().strip('"').strip("'").strip()
    return title


async def _get_summary_text(db, session_id: int) -> str | None:
    """Return the full summary content for a session, if one exists."""
    rows = await db.execute_fetchall(
        "SELECT content FROM summaries WHERE session_id = ? AND type = 'full' "
        "ORDER BY generated_at DESC LIMIT 1",
        (session_id,),
    )
    if rows and rows[0]["content"]:
        return rows[0]["content"]
    return None


async def maybe_generate_and_update_name(session_id: int) -> None:
    """Generate a session name and update if session is auto-named.

    Prefers the summary if available, falls back to transcript sampling.
    This is a fire-and-forget helper: all errors are logged, never raised.
    """
    try:
        async with get_db() as db:
            rows = await db.execute_fetchall(
                "SELECT name, session_number FROM sessions WHERE id = ?",
                (session_id,),
            )
            if not rows:
                return

            session = rows[0]
            name = session["name"] or ""
            session_number = session["session_number"]

            if not _is_auto_named(name):
                return

            # Prefer summary over raw transcript
            summary_text = await _get_summary_text(db, session_id)

            if not summary_text:
                # Fall back to transcript
                segments = await db.execute_fetchall(
                    """SELECT ts.text, ts.start_time, ts.end_time,
                              sp.diarization_label, sp.player_name, sp.character_name
                       FROM transcript_segments ts
                       LEFT JOIN speakers sp ON sp.id = ts.speaker_id
                       WHERE ts.session_id = ?
                       ORDER BY ts.start_time""",
                    (session_id,),
                )
                if not segments:
                    return

        if summary_text:
            title = await generate_session_name(summary_text, from_summary=True)
        else:
            transcript_text = format_transcript([dict(s) for s in segments])
            title = await generate_session_name(transcript_text)

        if not title:
            return

        new_name = f"Session {session_number}: {title}"
        async with get_db() as db:
            await db.execute(
                "UPDATE sessions SET name = ?, updated_at = datetime('now') WHERE id = ?",
                (new_name, session_id),
            )

    except Exception:
        logger.exception("Failed to generate session name for session %s", session_id)
