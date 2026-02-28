"""Speaker diarization service using SpeechBrain embeddings + clustering."""

# Shims for SpeechBrain 1.0.x compatibility with newer dependencies.
# 1) torchaudio >=2.9 removed list_audio_backends()
# 2) huggingface_hub >=1.0 removed the use_auth_token parameter
try:
    import torchaudio as _torchaudio

    if not hasattr(_torchaudio, "list_audio_backends"):
        _torchaudio.list_audio_backends = lambda: ["ffmpeg"]
except ImportError:
    pass

import huggingface_hub as _hfh
from requests import HTTPError as _HTTPError

_orig_hf_hub_download = _hfh.hf_hub_download


def _patched_hf_hub_download(*args, **kwargs):
    # SpeechBrain 1.0.x passes use_auth_token; huggingface_hub >=1.0 removed it.
    kwargs.pop("use_auth_token", None)
    # SpeechBrain 1.0.x also passes removed local_dir_use_symlinks/force_filename.
    kwargs.pop("local_dir_use_symlinks", None)
    kwargs.pop("force_filename", None)
    try:
        return _orig_hf_hub_download(*args, **kwargs)
    except _hfh.errors.EntryNotFoundError as e:
        # SpeechBrain expects HTTPError for 404s, not EntryNotFoundError.
        raise _HTTPError(f"404 Client Error: {e}") from e


_hfh.hf_hub_download = _patched_hf_hub_download

from dataclasses import dataclass
from pathlib import Path

import numpy as np

# Tunable constants
WINDOW_SIZE_SEC = 1.5
HOP_SIZE_SEC = 0.75
COSINE_DISTANCE_THRESHOLD = 0.7
SAMPLE_RATE = 16_000
MIN_WINDOW_SAMPLES = int(0.4 * SAMPLE_RATE)
SILENCE_RMS_THRESHOLD = 0.01

_encoder = None


@dataclass
class SpeakerSegment:
    speaker_label: str
    start_time: float
    end_time: float


def _get_encoder():
    """Load and cache the SpeechBrain ECAPA-TDNN encoder."""
    global _encoder
    if _encoder is not None:
        return _encoder

    import torch
    from speechbrain.inference.speaker import EncoderClassifier

    # Select best available device
    device = "cpu"
    try:
        if torch.backends.mps.is_available():
            device = "mps"
        elif torch.cuda.is_available():
            device = "cuda"
    except Exception:
        pass

    _encoder = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir="data/models/spkrec-ecapa-voxceleb",
        run_opts={"device": device},
    )

    return _encoder


def _load_waveform(wav_path: Path):
    """Load audio, ensure mono, resample to 16kHz. Returns tensor [1, samples]."""
    import torch
    from scipy.io import wavfile
    from scipy.signal import resample_poly
    from math import gcd

    sr, data = wavfile.read(str(wav_path))

    # Convert to float32 in [-1, 1]
    if data.dtype == np.int16:
        data = data.astype(np.float32) / 32768.0
    elif data.dtype == np.int32:
        data = data.astype(np.float32) / 2147483648.0
    elif data.dtype != np.float32:
        data = data.astype(np.float32)

    # Convert to mono
    if data.ndim > 1:
        data = data.mean(axis=1)

    # Resample to 16kHz if needed
    if sr != SAMPLE_RATE:
        g = gcd(SAMPLE_RATE, sr)
        data = resample_poly(data, SAMPLE_RATE // g, sr // g).astype(np.float32)

    return torch.from_numpy(data).unsqueeze(0)


def _extract_windowed_embeddings(waveform):
    """Slide windows over waveform and extract speaker embeddings.

    Returns (embeddings: np.ndarray[N, dim], timestamps: list[(start_sec, end_sec)]).
    """
    import torch

    encoder = _get_encoder()
    total_samples = waveform.shape[1]
    window_samples = int(WINDOW_SIZE_SEC * SAMPLE_RATE)
    hop_samples = int(HOP_SIZE_SEC * SAMPLE_RATE)

    embeddings = []
    timestamps = []
    offset = 0

    while offset < total_samples:
        end = min(offset + window_samples, total_samples)
        chunk = waveform[:, offset:end]

        # Skip windows shorter than minimum
        if chunk.shape[1] < MIN_WINDOW_SAMPLES:
            break

        # Skip silence
        rms = torch.sqrt(torch.mean(chunk ** 2)).item()
        if rms < SILENCE_RMS_THRESHOLD:
            offset += hop_samples
            continue

        emb = encoder.encode_batch(chunk)
        embeddings.append(emb.squeeze().cpu().numpy())
        timestamps.append((offset / SAMPLE_RATE, end / SAMPLE_RATE))

        offset += hop_samples

    if not embeddings:
        return np.empty((0, 0)), []

    return np.stack(embeddings), timestamps


def _cluster_embeddings(embeddings: np.ndarray, num_speakers: int | None = None) -> np.ndarray:
    """Cluster embeddings into speaker groups. Returns label array."""
    from sklearn.cluster import AgglomerativeClustering

    n = len(embeddings)
    if n <= 1:
        return np.zeros(n, dtype=int)

    if num_speakers is not None:
        num_speakers = min(num_speakers, n)
        clustering = AgglomerativeClustering(
            n_clusters=num_speakers,
            metric="cosine",
            linkage="average",
        )
    else:
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=COSINE_DISTANCE_THRESHOLD,
            metric="cosine",
            linkage="average",
        )

    return clustering.fit_predict(embeddings)


def _merge_segments(raw_segments: list[SpeakerSegment]) -> list[SpeakerSegment]:
    """Merge adjacent segments with the same speaker label."""
    if not raw_segments:
        return []

    merged = [raw_segments[0]]
    for seg in raw_segments[1:]:
        prev = merged[-1]
        if seg.speaker_label == prev.speaker_label:
            merged[-1] = SpeakerSegment(
                speaker_label=prev.speaker_label,
                start_time=prev.start_time,
                end_time=max(prev.end_time, seg.end_time),
            )
        else:
            merged.append(seg)

    return merged


def _run_pipeline(wav_path: Path, num_speakers: int | None = None) -> list[SpeakerSegment]:
    """Full diarization pipeline: load -> window -> embed -> cluster -> merge."""
    waveform = _load_waveform(wav_path)

    embeddings, timestamps = _extract_windowed_embeddings(waveform)
    if len(timestamps) == 0:
        return []

    labels = _cluster_embeddings(embeddings, num_speakers)

    raw_segments = [
        SpeakerSegment(
            speaker_label=f"SPEAKER_{label:02d}",
            start_time=start,
            end_time=end,
        )
        for (start, end), label in zip(timestamps, labels)
    ]

    return _merge_segments(raw_segments)


def diarize(wav_path: Path) -> list[SpeakerSegment]:
    """Run diarization on a WAV file and return speaker segments."""
    return _run_pipeline(wav_path)


def diarize_chunk(wav_path: Path, num_speakers: int | None = None) -> list[SpeakerSegment]:
    """Run diarization on a short audio chunk (e.g., 30s window)."""
    return _run_pipeline(wav_path, num_speakers)


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
