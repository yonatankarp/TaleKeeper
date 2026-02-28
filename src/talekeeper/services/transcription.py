"""Transcription service using faster-whisper."""

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from faster_whisper import WhisperModel

_model: WhisperModel | None = None
_model_size: str | None = None


@dataclass
class TranscriptSegment:
    text: str
    start_time: float
    end_time: float


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
    )

    for seg in segments:
        yield TranscriptSegment(
            text=seg.text.strip(),
            start_time=seg.start,
            end_time=seg.end,
        )
