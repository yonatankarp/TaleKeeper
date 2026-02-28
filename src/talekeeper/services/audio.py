"""Audio conversion utilities."""

from pathlib import Path
from pydub import AudioSegment


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
