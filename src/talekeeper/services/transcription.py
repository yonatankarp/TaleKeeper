"""Transcription service using faster-whisper."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Union

from faster_whisper import WhisperModel

_model: WhisperModel | None = None
_model_size: str | None = None

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


def get_model(model_size: str = "medium") -> WhisperModel:
    """Load and cache the Whisper model."""
    global _model, _model_size

    if _model is not None and _model_size == model_size:
        return _model

    _model = WhisperModel(model_size, device="auto", compute_type="auto")
    _model_size = model_size
    return _model


def unload_model() -> None:
    """Unload the cached model to free memory."""
    global _model, _model_size
    _model = None
    _model_size = None


def transcribe(wav_path: Path, model_size: str = "medium", language: str = "en") -> list[TranscriptSegment]:
    """Transcribe a WAV file and return segments with timestamps."""
    model = get_model(model_size)
    segments, _ = model.transcribe(
        str(wav_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"threshold": 0.3},
    )

    results = []
    for seg in segments:
        results.append(
            TranscriptSegment(
                text=seg.text.strip(),
                start_time=seg.start,
                end_time=seg.end,
            )
        )
    return results


def transcribe_stream(wav_path: Path, model_size: str = "medium", language: str = "en") -> Iterator[TranscriptSegment]:
    """Stream transcription segments as they are produced."""
    model = get_model(model_size)
    segments, _ = model.transcribe(
        str(wav_path),
        language=language,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"threshold": 0.3},
    )

    for seg in segments:
        yield TranscriptSegment(
            text=seg.text.strip(),
            start_time=seg.start,
            end_time=seg.end,
        )


def transcribe_chunked(
    audio_path: Path,
    model_size: str = "medium",
    language: str = "en",
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

        for seg in transcribe_stream(wav_path, model_size=model_size, language=language):
            abs_start = seg.start_time + offset_sec
            abs_end = seg.end_time + offset_sec
            midpoint = (abs_start + abs_end) / 2.0

            if zone_start <= midpoint < zone_end:
                yield TranscriptSegment(
                    text=seg.text,
                    start_time=abs_start,
                    end_time=abs_end,
                )
