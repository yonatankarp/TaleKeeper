"""Summary generation service using OpenAI-compatible LLM provider."""

from talekeeper.services import llm_client

FULL_SUMMARY_SYSTEM = """You are a summarizer for tabletop RPG session transcripts.
Your job is to summarize ONLY what is actually said in the transcript.
Do NOT invent, fabricate, or hallucinate any content that is not in the transcript.
Do NOT create fictional characters, events, or plot points.
If the transcript contains no meaningful RPG content, say so plainly.
Use third person, past tense. Be specific about names and events mentioned in the transcript."""

FULL_SUMMARY_PROMPT = """Summarize the following session transcript into a narrative recap.
IMPORTANT: Only include information that is actually present in the transcript below.
Do NOT make up any names, events, or details that are not in the transcript.
If the transcript is empty, repetitive, or contains no meaningful content, state that clearly.

TRANSCRIPT:
{transcript}

Write a summary based strictly on the transcript above."""

POV_SUMMARY_SYSTEM = """You are writing a personal journal entry from the perspective of a
specific character in a tabletop RPG session. Focus on what this character experienced,
learned, decided, and how they interacted with other characters and the world.
Write in first person as the character.
IMPORTANT: Only reference events, dialogue, and details that actually appear in the transcript.
Do NOT invent or fabricate any content."""

POV_SUMMARY_PROMPT = """Write a session recap from the perspective of {character_name},
played by {player_name}. Focus on their personal experience of the session.
IMPORTANT: Only include information actually present in the transcript below.
If the transcript has no meaningful content, say so.

TRANSCRIPT:
{transcript}

Write a first-person recap as {character_name}, based strictly on the transcript above."""

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


async def generate_full_summary(
    transcript_text: str,
    base_url: str,
    api_key: str | None,
    model: str,
) -> str:
    """Generate a full session narrative summary."""
    chunks = _chunk_transcript(transcript_text)

    if len(chunks) == 1:
        prompt = FULL_SUMMARY_PROMPT.format(transcript=transcript_text)
        return await llm_client.generate(base_url, api_key, model, prompt, system=FULL_SUMMARY_SYSTEM)

    # Chunked summarization
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        prompt = f"Summarize this section ({i + 1}/{len(chunks)}) of a session transcript. Only include what is actually said:\n\n{chunk}"
        summary = await llm_client.generate(base_url, api_key, model, prompt, system=FULL_SUMMARY_SYSTEM)
        chunk_summaries.append(summary)

    # Meta-summary
    combined = "\n\n---\n\n".join(chunk_summaries)
    meta_prompt = f"Combine these section summaries into one coherent session recap:\n\n{combined}"
    return await llm_client.generate(base_url, api_key, model, meta_prompt, system=FULL_SUMMARY_SYSTEM)


async def generate_pov_summary(
    transcript_text: str,
    character_name: str,
    player_name: str,
    base_url: str,
    api_key: str | None,
    model: str,
) -> str:
    """Generate a POV summary from a specific character's perspective."""
    chunks = _chunk_transcript(transcript_text)

    if len(chunks) == 1:
        prompt = POV_SUMMARY_PROMPT.format(
            transcript=transcript_text,
            character_name=character_name,
            player_name=player_name,
        )
        return await llm_client.generate(base_url, api_key, model, prompt, system=POV_SUMMARY_SYSTEM)

    # Chunked POV summarization
    chunk_summaries = []
    for i, chunk in enumerate(chunks):
        prompt = (
            f"Summarize this section ({i + 1}/{len(chunks)}) from {character_name}'s perspective:\n\n{chunk}"
        )
        summary = await llm_client.generate(base_url, api_key, model, prompt, system=POV_SUMMARY_SYSTEM)
        chunk_summaries.append(summary)

    combined = "\n\n---\n\n".join(chunk_summaries)
    meta_prompt = (
        f"Combine these section recaps into one coherent first-person session "
        f"journal entry for {character_name}:\n\n{combined}"
    )
    return await llm_client.generate(base_url, api_key, model, meta_prompt, system=POV_SUMMARY_SYSTEM)
