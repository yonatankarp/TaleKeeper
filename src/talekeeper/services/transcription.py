"""Transcription service using lightning-whisper-mlx with VAD pre-pass."""

import logging
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Union

import numpy as np

logger = logging.getLogger(__name__)

_model = None
_model_name: str | None = None

DEFAULT_MODEL = "large-v3"

SUPPORTED_LANGUAGES: set[str] = {
    "af", "am", "ar", "as", "az", "ba", "be", "bg", "bn", "bo", "br", "bs",
    "ca", "cs", "cy", "da", "de", "el", "en", "es", "et", "eu", "fa", "fi",
    "fo", "fr", "gl", "gu", "ha", "haw", "he", "hi", "hr", "ht", "hu", "hy",
    "id", "is", "it", "ja", "jw", "ka", "kk", "km", "kn", "ko", "la", "lb",
    "ln", "lo", "lt", "lv", "mg", "mi", "mk", "ml", "mn", "mr", "ms", "mt",
    "my", "ne", "nl", "nn", "no", "oc", "pa", "pl", "ps", "pt", "ro", "ru",
    "sa", "sd", "si", "sk", "sl", "sn", "so", "sq", "sr", "su", "sv", "sw",
    "ta", "te", "tg", "th", "tk", "tl", "tr", "tt", "uk", "ur", "uz", "vi",
    "yi", "yo", "zh",
}


@dataclass
class TranscriptSegment:
    text: str
    start_time: float
    end_time: float


@dataclass
class ChunkProgress:
    chunk: int  # 1-based
    total_chunks: int


def _detect_batch_size() -> int:
    """Auto-detect batch size from Apple Silicon performance core count."""
    try:
        result = subprocess.run(
            ["sysctl", "-n", "hw.perflevel0.logicalcpu"],
            capture_output=True, text=True, timeout=5,
        )
        cores = int(result.stdout.strip())
        if cores <= 6:
            return 8
        elif cores <= 10:
            return 12
        else:
            return 16
    except Exception:
        return 12  # safe default


async def _resolve_batch_size() -> int:
    """Resolve batch size: settings override > auto-detection."""
    from talekeeper.db import get_db
    try:
        async with get_db() as db:
            rows = await db.execute_fetchall(
                "SELECT value FROM settings WHERE key = 'whisper_batch_size'"
            )
            if rows and rows[0]["value"]:
                return int(rows[0]["value"])
    except Exception:
        pass
    return _detect_batch_size()


def get_model(model_name: str = DEFAULT_MODEL, batch_size: int = 12):
    """Load and cache the lightning-whisper-mlx model."""
    global _model, _model_name
    from lightning_whisper_mlx import LightningWhisperMLX

    if _model is not None and _model_name == model_name:
        return _model

    logger.info("Loading lightning-whisper-mlx model: %s (batch_size=%d)", model_name, batch_size)
    _model = LightningWhisperMLX(model=model_name, batch_size=batch_size)
    _model_name = model_name
    return _model


def unload_model() -> None:
    """Unload the cached model to free memory."""
    global _model, _model_name
    _model = None
    _model_name = None
    try:
        import mlx.core
        mlx.core.metal.clear_cache()
    except Exception:
        pass


def _run_vad(wav_path: Path) -> list[dict]:
    """Run Silero VAD on a WAV file, return list of {'start': float, 'end': float} in seconds."""
    import torch
    from silero_vad import load_silero_vad, read_audio, get_speech_timestamps

    model = load_silero_vad()
    wav = read_audio(str(wav_path), sampling_rate=16000)
    speech_timestamps = get_speech_timestamps(
        wav, model, sampling_rate=16000, return_seconds=True,
    )
    return speech_timestamps


def _build_speech_buffer(
    wav_path: Path, vad_ranges: list[dict]
) -> tuple[np.ndarray, list[tuple[float, float]]]:
    """Concatenate speech-only regions into a contiguous buffer.

    Returns:
        audio_buffer: numpy array of speech-only audio at 16kHz
        offset_map: list of (buffer_start_sec, original_start_sec) tuples for timestamp remapping
    """
    from scipy.io import wavfile

    sr, audio_data = wavfile.read(str(wav_path))
    # Convert to float32 in [-1, 1] range
    if audio_data.dtype == np.int16:
        audio_data = audio_data.astype(np.float32) / 32768.0
    elif audio_data.dtype == np.int32:
        audio_data = audio_data.astype(np.float32) / 2147483648.0
    else:
        audio_data = audio_data.astype(np.float32)

    if sr != 16000:
        from scipy.signal import resample
        audio_data = resample(audio_data, int(len(audio_data) * 16000 / sr))
        sr = 16000

    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    chunks = []
    offset_map: list[tuple[float, float]] = []
    buffer_pos = 0.0

    for r in vad_ranges:
        start_sample = int(r["start"] * sr)
        end_sample = int(r["end"] * sr)
        chunk = audio_data[start_sample:end_sample]
        chunks.append(chunk)
        offset_map.append((buffer_pos, r["start"]))
        buffer_pos += len(chunk) / sr

    if not chunks:
        return np.array([], dtype=np.float32), []

    return np.concatenate(chunks), offset_map


def _remap_timestamp(buffer_time: float, offset_map: list[tuple[float, float]]) -> float:
    """Map a timestamp from the speech buffer back to the original audio timeline."""
    if not offset_map:
        return buffer_time

    # Find which region this timestamp falls in
    for i in range(len(offset_map) - 1, -1, -1):
        buf_start, orig_start = offset_map[i]
        if buffer_time >= buf_start:
            return orig_start + (buffer_time - buf_start)

    return buffer_time


def transcribe(
    wav_path: Path,
    model_name: str = DEFAULT_MODEL,
    language: str = "en",
    batch_size: int = 12,
) -> list[TranscriptSegment]:
    """Transcribe a WAV file: VAD pre-pass -> speech buffer -> lightning-whisper-mlx -> timestamp remapping."""
    # Step 1: VAD pre-pass
    vad_ranges = _run_vad(wav_path)
    if not vad_ranges:
        logger.info("No speech detected in %s", wav_path)
        return []

    # Step 2: Build speech-only buffer
    speech_buffer, offset_map = _build_speech_buffer(wav_path, vad_ranges)
    if len(speech_buffer) == 0:
        return []

    # Step 3: Write speech buffer to temp file for lightning-whisper-mlx
    import tempfile
    from scipy.io import wavfile as wavfile_write

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    # Convert float32 [-1,1] to int16 for WAV file
    int16_buffer = (speech_buffer * 32767).astype(np.int16)
    wavfile_write.write(str(tmp_path), 16000, int16_buffer)

    try:
        # Step 4: Transcribe with lightning-whisper-mlx
        model = get_model(model_name, batch_size)
        result = model.transcribe(str(tmp_path), language=language)

        # Step 5: Remap timestamps
        # lightning-whisper-mlx returns segments as [start_frames, end_frames, text]
        # where frames are mel spectrogram positions; convert to seconds via
        # HOP_LENGTH (160) / SAMPLE_RATE (16000) = 0.01s per frame.
        FRAMES_TO_SEC = 160 / 16000  # HOP_LENGTH / SAMPLE_RATE
        segments = []
        for seg in result.get("segments", []):
            buf_start = seg[0] * FRAMES_TO_SEC
            buf_end = seg[1] * FRAMES_TO_SEC
            text = seg[2]
            orig_start = _remap_timestamp(buf_start, offset_map)
            orig_end = _remap_timestamp(buf_end, offset_map)
            text = text.strip()
            if text:
                segments.append(TranscriptSegment(
                    text=text,
                    start_time=orig_start,
                    end_time=orig_end,
                ))
        return segments
    finally:
        tmp_path.unlink(missing_ok=True)


def transcribe_chunked(
    audio_path: Path,
    model_name: str = DEFAULT_MODEL,
    language: str = "en",
    batch_size: int = 12,
) -> Iterator[Union[TranscriptSegment, ChunkProgress]]:
    """Split a stored audio file into chunks and transcribe each.

    Yields ChunkProgress between chunks and TranscriptSegment objects
    with absolute timestamps (adjusted for chunk offsets). Overlapping
    segments are deduplicated using the primary-zone strategy.
    """
    from pydub import AudioSegment
    from talekeeper.services.audio import (
        split_audio_to_chunks,
        compute_primary_zone,
        DEFAULT_CHUNK_DURATION_MS,
        DEFAULT_OVERLAP_MS,
    )

    # Compute total chunks from audio duration to avoid an extra pass
    audio = AudioSegment.from_file(str(audio_path))
    total_ms = len(audio)
    del audio  # free memory before transcription

    if total_ms <= DEFAULT_CHUNK_DURATION_MS:
        total_chunks = 1
    else:
        # Simulate the split loop to match split_audio_to_chunks exactly
        total_chunks = 0
        start = 0
        step = DEFAULT_CHUNK_DURATION_MS - DEFAULT_OVERLAP_MS
        while start < total_ms:
            total_chunks += 1
            start += step
            if start < total_ms and (total_ms - start) < DEFAULT_OVERLAP_MS:
                break

    for chunk_index, wav_path, start_ms, end_ms in split_audio_to_chunks(audio_path):
        yield ChunkProgress(chunk=chunk_index + 1, total_chunks=total_chunks)

        offset_sec = start_ms / 1000.0
        zone_start, zone_end = compute_primary_zone(
            chunk_index, start_ms, end_ms, total_chunks
        )

        for seg in transcribe(wav_path, model_name=model_name, language=language, batch_size=batch_size):
            abs_start = seg.start_time + offset_sec
            abs_end = seg.end_time + offset_sec
            midpoint = (abs_start + abs_end) / 2.0

            if zone_start <= midpoint < zone_end:
                yield TranscriptSegment(
                    text=seg.text,
                    start_time=abs_start,
                    end_time=abs_end,
                )
