"""Speaker diarization service using pyannote-audio."""

from dataclasses import dataclass
from pathlib import Path

_pipeline = None


@dataclass
class SpeakerSegment:
    speaker_label: str
    start_time: float
    end_time: float


def get_pipeline():
    """Load and cache the pyannote-audio diarization pipeline."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    import os
    from pyannote.audio import Pipeline
    import torch

    token = os.environ.get("HF_TOKEN")
    if not token:
        raise RuntimeError("HF_TOKEN environment variable is required for speaker diarization. Get one at https://huggingface.co/settings/tokens")

    _pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        token=token,
    )

    # Use Metal acceleration on Apple Silicon if available
    if torch.backends.mps.is_available():
        _pipeline.to(torch.device("mps"))

    return _pipeline


def diarize(wav_path: Path) -> list[SpeakerSegment]:
    """Run diarization on a WAV file and return speaker segments."""
    pipeline = get_pipeline()
    diarization = pipeline(str(wav_path))

    results = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        results.append(
            SpeakerSegment(
                speaker_label=speaker,
                start_time=turn.start,
                end_time=turn.end,
            )
        )
    return results


def diarize_chunk(wav_path: Path, num_speakers: int | None = None) -> list[SpeakerSegment]:
    """Run diarization on a short audio chunk (e.g., 30s window)."""
    pipeline = get_pipeline()

    params = {}
    if num_speakers is not None:
        params["num_speakers"] = num_speakers

    diarization = pipeline(str(wav_path), **params)

    results = []
    for turn, _, speaker in diarization.itertracks(yield_label=True):
        results.append(
            SpeakerSegment(
                speaker_label=speaker,
                start_time=turn.start,
                end_time=turn.end,
            )
        )
    return results


def align_speakers_with_transcript(
    speaker_segments: list[SpeakerSegment],
    transcript_segments: list[dict],
) -> list[dict]:
    """Align speaker labels with transcript segments.

    For each transcript segment, find the speaker segment that
    overlaps the most and assign that speaker.
    If a transcript segment crosses a speaker boundary, split it.
    """
    aligned = []

    for t_seg in transcript_segments:
        t_start = t_seg["start_time"]
        t_end = t_seg["end_time"]

        # Find overlapping speaker segments
        overlapping = []
        for s_seg in speaker_segments:
            overlap_start = max(t_start, s_seg.start_time)
            overlap_end = min(t_end, s_seg.end_time)
            if overlap_start < overlap_end:
                overlapping.append((s_seg, overlap_end - overlap_start))

        if not overlapping:
            aligned.append(t_seg)
            continue

        if len(overlapping) == 1:
            t_seg["speaker_label"] = overlapping[0][0].speaker_label
            aligned.append(t_seg)
        else:
            # Multiple speakers overlap — assign to the one with the most overlap
            overlapping.sort(key=lambda x: x[1], reverse=True)
            t_seg["speaker_label"] = overlapping[0][0].speaker_label
            aligned.append(t_seg)

    return aligned


async def run_final_diarization(session_id: int, wav_path: Path) -> None:
    """Run final diarization pass and update all speaker labels in DB."""
    from talekeeper.db import get_db

    segments = diarize(wav_path)

    # Get all unique speaker labels
    unique_labels = sorted(set(s.speaker_label for s in segments))

    async with get_db() as db:
        # Create/update speaker records
        speaker_id_map = {}
        for idx, label in enumerate(unique_labels, start=1):
            friendly_label = f"Player {idx}"
            # Check if speaker already exists
            rows = await db.execute_fetchall(
                "SELECT id FROM speakers WHERE session_id = ? AND diarization_label = ?",
                (session_id, friendly_label),
            )
            if rows:
                speaker_id_map[label] = rows[0]["id"]
            else:
                cursor = await db.execute(
                    "INSERT INTO speakers (session_id, diarization_label) VALUES (?, ?)",
                    (session_id, friendly_label),
                )
                speaker_id_map[label] = cursor.lastrowid

        # Get transcript segments
        t_rows = await db.execute_fetchall(
            "SELECT id, start_time, end_time FROM transcript_segments WHERE session_id = ? ORDER BY start_time",
            (session_id,),
        )

        transcript_segs = [dict(r) for r in t_rows]
        aligned = align_speakers_with_transcript(segments, transcript_segs)

        # Update speaker assignments
        for seg in aligned:
            label = seg.get("speaker_label")
            if label and label in speaker_id_map:
                await db.execute(
                    "UPDATE transcript_segments SET speaker_id = ? WHERE id = ?",
                    (speaker_id_map[label], seg["id"]),
                )
