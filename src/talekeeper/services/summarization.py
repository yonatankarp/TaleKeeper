"""Summary generation service using Ollama."""

from talekeeper.services import ollama

FULL_SUMMARY_SYSTEM = """You are a skilled narrator summarizing a tabletop RPG session.
Write a compelling narrative summary capturing key plot events, NPC interactions,
combat encounters, player decisions, and notable character moments.
Use third person, past tense. Be specific about names and events."""

FULL_SUMMARY_PROMPT = """Summarize the following D&D session transcript into a narrative recap.

TRANSCRIPT:
{transcript}

Write a detailed but readable session summary."""

POV_SUMMARY_SYSTEM = """You are writing a personal journal entry from the perspective of a
specific character in a tabletop RPG session. Focus on what this character experienced,
learned, decided, and how they interacted with other characters and the world.
Write in first person as the character."""

POV_SUMMARY_PROMPT = """Write a session recap from the perspective of {character_name},
played by {player_name}. Focus on their personal experience of the session.

TRANSCRIPT:
{transcript}

Write a first-person recap as {character_name}."""

# Rough token estimation: ~4 chars per token
CHARS_PER_TOKEN = 4
MAX_CONTEXT_TOKENS = 6000  # Conservative default for 8B models
CHUNK_OVERLAP_TOKENS = 500


def _estimate_tokens(text: str) -> int:
    return len(text) // CHARS_PER_TOKEN


def _chunk_transcript(transcript: str, max_tokens: int = MAX_CONTEXT_TOKENS) -> list[str]:
    """Split transcript into overlapping chunks that fit the context window."""
    chunk_size = max_tokens * CHARS_PER_TOKEN
    overlap_size = CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN

    if len(transcript) <= chunk_size:
        return [transcript]

    chunks = []
    start = 0
    while start < len(transcript):
        end = start + chunk_size
        chunk = transcript[start:end]
        chunks.append(chunk)
        start = end - overlap_size

    return chunks


def format_transcript(segments: list[dict]) -> str:
    """Format transcript segments into a readable text block."""
    lines = []
    for seg in segments:
        speaker = ""
        if seg.get("character_name") and seg.get("player_name"):
            speaker = f"{seg['character_name']} ({seg['player_name']})"
        elif seg.get("diarization_label"):
            speaker = seg["diarization_label"]

        time_str = _format_time(seg["start_time"])
        if speaker:
            lines.append(f"[{time_str}] {speaker}: {seg['text']}")
        else:
            lines.append(f"[{time_str}] {seg['text']}")
    return "\n".join(lines)


def _format_time(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


async def generate_full_summary(transcript_text: str, model: str = "llama3.1:8b") -> str:
    """Generate a full session narrative summary."""
    chunks = _chunk_transcript(transcript_text)

    if len(chunks) == 1:
        prompt = FULL_SUMMARY_PROMPT.format(transcript=transcript_text)
        return await ollama.generate(model, prompt, system=FULL_SUMMARY_SYSTEM)

    # Chunked summarization
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        prompt = f"Summarize this section ({i + 1}/{len(chunks)}) of a D&D session transcript:\n\n{chunk}"
        summary = await ollama.generate(model, prompt, system=FULL_SUMMARY_SYSTEM)
        chunk_summaries.append(summary)

    # Meta-summary
    combined = "\n\n---\n\n".join(chunk_summaries)
    meta_prompt = f"Combine these section summaries into one coherent session recap:\n\n{combined}"
    return await ollama.generate(model, meta_prompt, system=FULL_SUMMARY_SYSTEM)


async def generate_pov_summary(
    transcript_text: str,
    character_name: str,
    player_name: str,
    model: str = "llama3.1:8b",
) -> str:
    """Generate a POV summary from a specific character's perspective."""
    chunks = _chunk_transcript(transcript_text)

    if len(chunks) == 1:
        prompt = POV_SUMMARY_PROMPT.format(
            transcript=transcript_text,
            character_name=character_name,
            player_name=player_name,
        )
        return await ollama.generate(model, prompt, system=POV_SUMMARY_SYSTEM)

    # Chunked POV summarization
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        prompt = (
            f"Summarize this section ({i + 1}/{len(chunks)}) from {character_name}'s perspective:\n\n{chunk}"
        )
        summary = await ollama.generate(model, prompt, system=POV_SUMMARY_SYSTEM)
        chunk_summaries.append(summary)

    combined = "\n\n---\n\n".join(chunk_summaries)
    meta_prompt = (
        f"Combine these section recaps into one coherent first-person session "
        f"journal entry for {character_name}:\n\n{combined}"
    )
    return await ollama.generate(model, meta_prompt, system=POV_SUMMARY_SYSTEM)
