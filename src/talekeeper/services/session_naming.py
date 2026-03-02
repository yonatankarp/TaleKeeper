"""Session name generation service using LLM."""

import logging
import re

from talekeeper.db import get_db
from talekeeper.services import llm_client
from talekeeper.services.summarization import format_transcript

logger = logging.getLogger(__name__)

_SESSION_NAME_SYSTEM = """You are naming tabletop RPG sessions based on transcript content.
Generate a short, catchy title (2-6 words) that captures the key theme or event of the session.
Output ONLY the title itself. No quotes, no preamble, no explanation.
IMPORTANT: Write the title in the same language as the transcript. If the transcript is in
Hebrew, write in Hebrew. If in English, write in English. Match the language of the source material.
Examples of good titles: "The Dragon's Lair", "Betrayal at Blackwater", "Into the Feywild"."""

_SESSION_NAME_PROMPT = """Based on the following transcript excerpt from a tabletop RPG session,
generate a catchy session title (2-6 words) that captures the key theme or event.

TRANSCRIPT:
{transcript}

Title:"""

_AUTO_NAME_PATTERN = re.compile(r"^Session \d+(?:\s*:.+)?$")

# Sampling limits for long transcripts
_SAMPLE_THRESHOLD = 4000
_SAMPLE_SIZE = 2000


def _is_auto_named(name: str) -> bool:
    """Check if a session name matches the auto-assigned 'Session N' or 'Session N: ...' pattern."""
    return bool(_AUTO_NAME_PATTERN.match(name.strip()))


def _sample_transcript(text: str) -> str:
    """Sample first and last portions of long transcripts."""
    if len(text) <= _SAMPLE_THRESHOLD:
        return text
    return text[:_SAMPLE_SIZE] + "\n\n[...]\n\n" + text[-_SAMPLE_SIZE:]


async def generate_session_name(transcript_text: str) -> str:
    """Generate a catchy session title from transcript text using the LLM.

    Returns a 2-6 word title string.
    """
    config = await llm_client.resolve_config()
    sampled = _sample_transcript(transcript_text)
    prompt = _SESSION_NAME_PROMPT.format(transcript=sampled)

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


async def maybe_generate_and_update_name(session_id: int) -> None:
    """Generate a session name from transcript and update if session is auto-named.

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

            # Fetch transcript segments
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
