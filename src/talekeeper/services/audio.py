"""Audio conversion utilities."""

import shutil
import tempfile
from pathlib import Path
from typing import Iterator

from pydub import AudioSegment

# Defaults for chunked processing (in milliseconds)
DEFAULT_CHUNK_DURATION_MS = 5 * 60 * 1000  # 5 minutes
DEFAULT_OVERLAP_MS = 30 * 1000  # 30 seconds


def audio_to_wav(audio_path: Path, wav_path: Path | None = None) -> Path:
    """Convert any audio file to WAV for ML model input (auto-detects format).

    Returns the path to the resulting WAV file.
    """
    if wav_path is None:
        wav_path = audio_path.with_suffix(".wav")

    audio = AudioSegment.from_file(str(audio_path))
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(str(wav_path), format="wav")
    return wav_path


def webm_to_wav(webm_path: Path, wav_path: Path | None = None) -> Path:
    """Convert WebM audio to WAV for ML model input.

    Returns the path to the resulting WAV file.
    """
    if wav_path is None:
        wav_path = webm_path.with_suffix(".wav")

    audio = AudioSegment.from_file(str(webm_path), format="webm")
    audio = audio.set_channels(1).set_frame_rate(16000)  # Whisper expects 16kHz mono
    audio.export(str(wav_path), format="wav")
    return wav_path


def webm_bytes_to_wav(data: bytes, wav_path: Path) -> Path:
    """Convert raw WebM bytes to WAV."""
    import io

    audio = AudioSegment.from_file(io.BytesIO(data), format="webm")
    audio = audio.set_channels(1).set_frame_rate(16000)
    audio.export(str(wav_path), format="wav")
    return wav_path


def split_audio_to_chunks(
    audio_path: Path,
    chunk_duration_ms: int = DEFAULT_CHUNK_DURATION_MS,
    overlap_ms: int = DEFAULT_OVERLAP_MS,
) -> Iterator[tuple[int, Path, int, int]]:
    """Split an audio file into overlapping chunks for transcription.

    Yields (chunk_index, wav_path, start_ms, end_ms) tuples.
    Each slice is exported as a temp WAV (16kHz mono) and the temp file
    is cleaned up after the caller is done with it (after yield).
    """
    audio = AudioSegment.from_file(str(audio_path))
    total_ms = len(audio)

    if total_ms <= chunk_duration_ms:
        # Short file — single chunk, no splitting needed
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = Path(tmp.name)
        tmp.close()
        try:
            chunk = audio.set_channels(1).set_frame_rate(16000)
            chunk.export(str(wav_path), format="wav")
            yield (0, wav_path, 0, total_ms)
        finally:
            if wav_path.exists():
                wav_path.unlink()
        return

    chunk_index = 0
    start_ms = 0
    while start_ms < total_ms:
        end_ms = min(start_ms + chunk_duration_ms, total_ms)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        wav_path = Path(tmp.name)
        tmp.close()
        try:
            chunk = audio[start_ms:end_ms].set_channels(1).set_frame_rate(16000)
            chunk.export(str(wav_path), format="wav")
            yield (chunk_index, wav_path, start_ms, end_ms)
        finally:
            if wav_path.exists():
                wav_path.unlink()

        chunk_index += 1
        start_ms += chunk_duration_ms - overlap_ms
        # Avoid creating a tiny trailing chunk
        if start_ms < total_ms and (total_ms - start_ms) < overlap_ms:
            break


def merge_chunk_files(chunk_dir: Path, output_path: Path) -> None:
    """Concatenate numbered chunk_NNN.webm files into a single .webm output.

    Reads files in sorted order, writes them sequentially, then deletes
    the chunk directory.
    """
    chunk_files = sorted(chunk_dir.glob("chunk_*.webm"))
    with open(output_path, "wb") as out:
        for chunk_file in chunk_files:
            out.write(chunk_file.read_bytes())
    shutil.rmtree(chunk_dir)


def compute_primary_zone(
    chunk_index: int,
    chunk_start_ms: int,
    chunk_end_ms: int,
    total_chunks: int,
    overlap_ms: int = DEFAULT_OVERLAP_MS,
) -> tuple[float, float]:
    """Compute the primary zone for midpoint-based deduplication.

    Returns (zone_start_sec, zone_end_sec) — segments whose midpoint falls
    within this range belong to this chunk.
    """
    half_overlap_ms = overlap_ms / 2

    if chunk_index == 0:
        zone_start = chunk_start_ms
    else:
        zone_start = chunk_start_ms + half_overlap_ms

    if chunk_index == total_chunks - 1:
        zone_end = chunk_end_ms
    else:
        zone_end = chunk_end_ms - half_overlap_ms

    return (zone_start / 1000.0, zone_end / 1000.0)
