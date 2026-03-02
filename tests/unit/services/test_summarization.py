"""Tests for the summarization service."""

import pytest
from unittest.mock import patch, AsyncMock

from talekeeper.services.summarization import (
    generate_full_summary,
    generate_pov_summary,
    format_transcript,
    _chunk_transcript,
    CHARS_PER_TOKEN,
    MAX_CONTEXT_TOKENS,
    CHUNK_OVERLAP_TOKENS,
)


@patch(
    "talekeeper.services.summarization.llm_client.generate",
    new_callable=AsyncMock,
    return_value="The party entered the dungeon.",
)
async def test_generate_full_summary(mock_gen):
    """generate_full_summary calls LLM and returns the narrative summary."""
    result = await generate_full_summary(
        "Player 1: We enter the dungeon.", "http://test", None, "model"
    )

    assert result == "The party entered the dungeon."
    mock_gen.assert_awaited_once()


@patch(
    "talekeeper.services.summarization.llm_client.generate",
    new_callable=AsyncMock,
    return_value="I watched as we descended into the dark cavern.",
)
async def test_generate_pov_summary(mock_gen):
    """generate_pov_summary returns a character-perspective summary."""
    result = await generate_pov_summary(
        "Player 1: We descend into the cavern.",
        "Eldrin",
        "http://test",
        None,
        "model",
    )

    assert result == "I watched as we descended into the dark cavern."
    mock_gen.assert_awaited_once()


def test_format_transcript():
    """format_transcript formats segments with speaker labels and timestamps."""
    segments = [
        {
            "character_name": "Eldrin",
            "player_name": "Alice",
            "diarization_label": "SPEAKER_00",
            "start_time": 0.0,
            "text": "Hello everyone",
        },
        {
            "character_name": None,
            "player_name": "Bob",
            "diarization_label": "SPEAKER_01",
            "start_time": 65.0,
            "text": "Greetings",
        },
        {
            "character_name": None,
            "player_name": None,
            "diarization_label": None,
            "start_time": 130.0,
            "text": "Unknown speaker line",
        },
    ]

    result = format_transcript(segments)
    lines = result.split("\n")

    assert len(lines) == 3
    # Character name takes priority
    assert "[00:00:00] Eldrin: Hello everyone" == lines[0]
    # Falls back to player name
    assert "[00:01:05] Bob: Greetings" == lines[1]
    # No speaker label at all
    assert "[00:02:10] Unknown speaker line" == lines[2]


def test_chunk_transcript():
    """_chunk_transcript splits long text into overlapping chunks."""
    chunk_size = MAX_CONTEXT_TOKENS * CHARS_PER_TOKEN
    overlap_size = CHUNK_OVERLAP_TOKENS * CHARS_PER_TOKEN

    # Short text fits in a single chunk
    short_text = "Hello world"
    assert _chunk_transcript(short_text) == [short_text]

    # Long text is split into overlapping chunks
    long_text = "A" * (chunk_size + 1000)
    chunks = _chunk_transcript(long_text)

    assert len(chunks) >= 2
    # Each chunk should be at most chunk_size characters
    for chunk in chunks:
        assert len(chunk) <= chunk_size
    # Chunks should overlap
    assert len(chunks[0]) == chunk_size
