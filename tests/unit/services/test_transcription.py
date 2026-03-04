"""Tests for the transcription service (lightning-whisper-mlx + VAD)."""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from pathlib import Path

import numpy as np

import talekeeper.services.transcription as mod
from talekeeper.services.transcription import (
    transcribe,
    transcribe_chunked,
    TranscriptSegment,
    ChunkProgress,
    _run_vad,
    _build_speech_buffer,
    _remap_timestamp,
    _detect_batch_size,
)


# ---- VAD pre-pass tests (4.10) ----


@patch("silero_vad.get_speech_timestamps")
@patch("silero_vad.read_audio")
@patch("silero_vad.load_silero_vad")
def test_run_vad_extracts_speech_regions(mock_load, mock_read, mock_timestamps):
    """_run_vad returns speech timestamp ranges from Silero VAD."""
    mock_model = MagicMock()
    mock_load.return_value = mock_model
    mock_wav = MagicMock()
    mock_read.return_value = mock_wav
    mock_timestamps.return_value = [
        {"start": 1.0, "end": 5.0},
        {"start": 10.0, "end": 20.0},
    ]

    result = _run_vad(Path("test.wav"))

    assert len(result) == 2
    assert result[0] == {"start": 1.0, "end": 5.0}
    assert result[1] == {"start": 10.0, "end": 20.0}
    mock_read.assert_called_once_with(str(Path("test.wav")), sampling_rate=16000)
    mock_timestamps.assert_called_once()


@patch("silero_vad.get_speech_timestamps")
@patch("silero_vad.read_audio")
@patch("silero_vad.load_silero_vad")
def test_run_vad_empty_for_no_speech(mock_load, mock_read, mock_timestamps):
    """_run_vad returns empty list when no speech detected."""
    mock_load.return_value = MagicMock()
    mock_read.return_value = MagicMock()
    mock_timestamps.return_value = []

    result = _run_vad(Path("silence.wav"))

    assert result == []


# ---- Timestamp remapping tests ----


def test_remap_timestamp_single_region():
    """_remap_timestamp maps buffer time back to original timeline."""
    # Region: original 10.0–15.0 mapped to buffer 0.0–5.0
    offset_map = [(0.0, 10.0)]
    assert _remap_timestamp(2.5, offset_map) == 12.5


def test_remap_timestamp_multiple_regions():
    """_remap_timestamp handles multiple non-contiguous regions."""
    # Region 1: original 5.0–10.0 → buffer 0.0–5.0
    # Region 2: original 20.0–25.0 → buffer 5.0–10.0
    offset_map = [(0.0, 5.0), (5.0, 20.0)]
    assert _remap_timestamp(3.0, offset_map) == 8.0   # falls in region 1
    assert _remap_timestamp(7.0, offset_map) == 22.0  # falls in region 2


def test_remap_timestamp_empty_offset_map():
    """_remap_timestamp returns buffer_time unchanged when no offset map."""
    assert _remap_timestamp(5.0, []) == 5.0


# ---- transcribe() tests (4.11) ----


@patch("scipy.io.wavfile.write")
@patch("talekeeper.services.transcription.get_model")
@patch("talekeeper.services.transcription._build_speech_buffer")
@patch("talekeeper.services.transcription._run_vad")
def test_transcribe_vad_to_transcribe_to_remap(mock_vad, mock_build, mock_get_model, mock_wav_write, tmp_path):
    """transcribe runs VAD → speech buffer → lightning-whisper-mlx → timestamp remapping."""
    # VAD returns two speech regions
    mock_vad.return_value = [
        {"start": 5.0, "end": 10.0},
        {"start": 20.0, "end": 25.0},
    ]

    # Build speech buffer returns concatenated audio with offset map
    speech_audio = np.zeros(160000, dtype=np.float32)  # 10 seconds at 16kHz
    offset_map = [(0.0, 5.0), (5.0, 20.0)]
    mock_build.return_value = (speech_audio, offset_map)

    # Mock model transcribe to return segments in mel frames
    # lightning-whisper-mlx returns [start_frames, end_frames, text]
    # where seconds = frames * HOP_LENGTH / SAMPLE_RATE = frames * 0.01
    mock_model = MagicMock()
    mock_model.transcribe.return_value = {
        "text": "Hello World",
        "segments": [
            [50, 200, " Hello "],  # 0.5s-2.0s in buffer → original 5.5-7.0
            [600, 800, " World "],  # 6.0s-8.0s in buffer → original 21.0-23.0
        ],
        "language": "en",
    }
    mock_get_model.return_value = mock_model

    result = transcribe(tmp_path / "test.wav")

    assert len(result) == 2
    assert result[0].text == "Hello"
    assert abs(result[0].start_time - 5.5) < 0.01
    assert abs(result[0].end_time - 7.0) < 0.01
    assert result[1].text == "World"
    assert abs(result[1].start_time - 21.0) < 0.01
    assert abs(result[1].end_time - 23.0) < 0.01


@patch("talekeeper.services.transcription._run_vad")
def test_transcribe_no_speech_returns_empty(mock_vad, tmp_path):
    """transcribe returns empty list when VAD detects no speech."""
    mock_vad.return_value = []

    result = transcribe(tmp_path / "silence.wav")

    assert result == []


# ---- get_model caching tests ----


def test_get_model_caching():
    """get_model caches the model and returns the same instance on repeat calls."""
    mod._model = None
    mod._model_name = None

    mock_instance = MagicMock()
    fake_lwm = MagicMock()
    fake_lwm.LightningWhisperMLX.return_value = mock_instance

    with patch.dict("sys.modules", {"lightning_whisper_mlx": fake_lwm}):
        m1 = mod.get_model("test-model", batch_size=8)
        m2 = mod.get_model("test-model", batch_size=8)

        assert m1 is m2
        fake_lwm.LightningWhisperMLX.assert_called_once()

    mod._model = None
    mod._model_name = None


# ---- Batch size auto-detection tests (4.12) ----


@patch("talekeeper.services.transcription.subprocess.run")
def test_detect_batch_size_low_cores(mock_run):
    """_detect_batch_size returns 8 for <= 6 performance cores."""
    mock_run.return_value = MagicMock(stdout="6\n")
    assert _detect_batch_size() == 8


@patch("talekeeper.services.transcription.subprocess.run")
def test_detect_batch_size_medium_cores(mock_run):
    """_detect_batch_size returns 12 for 7-10 performance cores."""
    mock_run.return_value = MagicMock(stdout="10\n")
    assert _detect_batch_size() == 12


@patch("talekeeper.services.transcription.subprocess.run")
def test_detect_batch_size_high_cores(mock_run):
    """_detect_batch_size returns 16 for > 10 performance cores."""
    mock_run.return_value = MagicMock(stdout="14\n")
    assert _detect_batch_size() == 16


@patch("talekeeper.services.transcription.subprocess.run")
def test_detect_batch_size_fallback_on_error(mock_run):
    """_detect_batch_size returns 12 as fallback when sysctl fails."""
    mock_run.side_effect = FileNotFoundError("sysctl not found")
    assert _detect_batch_size() == 12


# ---- transcribe_chunked tests ----


def test_transcribe_chunked():
    """transcribe_chunked yields ChunkProgress first, then TranscriptSegments."""
    import pydub
    import talekeeper.services.audio as audio_mod

    mock_audio = MagicMock()
    mock_audio.__len__ = MagicMock(return_value=60_000)

    orig_as = pydub.AudioSegment
    orig_split = audio_mod.split_audio_to_chunks

    try:
        pydub.AudioSegment = MagicMock()
        pydub.AudioSegment.from_file.return_value = mock_audio

        audio_mod.split_audio_to_chunks = MagicMock(
            return_value=iter([(0, Path("chunk.wav"), 0, 60_000)])
        )

        with patch("talekeeper.services.transcription.transcribe") as mock_transcribe:
            mock_transcribe.return_value = [
                TranscriptSegment(text="Hello", start_time=0.0, end_time=1.0),
                TranscriptSegment(text="World", start_time=1.0, end_time=2.0),
            ]

            results = list(transcribe_chunked(Path("test.wav")))

        assert isinstance(results[0], ChunkProgress)
        assert results[0].chunk == 1
        assert results[0].total_chunks == 1

        transcript_results = [r for r in results if isinstance(r, TranscriptSegment)]
        assert len(transcript_results) == 2
        assert transcript_results[0].text == "Hello"
        assert transcript_results[1].text == "World"
    finally:
        pydub.AudioSegment = orig_as
        audio_mod.split_audio_to_chunks = orig_split
