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
WINDOW_SIZE_SEC = 3.0
HOP_SIZE_SEC = 1.5
COSINE_DISTANCE_THRESHOLD = 1.0
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


def extract_speaker_embedding(
    waveform, time_ranges: list[tuple[float, float]]
) -> np.ndarray | None:
    """Extract a single averaged, L2-normalized embedding from time ranges.

    Given a waveform tensor [1, samples] and list of (start_sec, end_sec) ranges,
    extract windowed ECAPA-TDNN embeddings from those ranges, average them, and
    L2-normalize. Returns a 1-D numpy array, or None if no valid embeddings found.
    """
    import torch

    encoder = _get_encoder()
    window_samples = int(WINDOW_SIZE_SEC * SAMPLE_RATE)
    hop_samples = int(HOP_SIZE_SEC * SAMPLE_RATE)

    all_embeddings = []

    for start_sec, end_sec in time_ranges:
        start_sample = int(start_sec * SAMPLE_RATE)
        end_sample = int(end_sec * SAMPLE_RATE)
        segment = waveform[:, start_sample:end_sample]

        if segment.shape[1] < MIN_WINDOW_SAMPLES:
            # Segment too short for windowing, try encoding directly
            rms = torch.sqrt(torch.mean(segment**2)).item()
            if rms >= SILENCE_RMS_THRESHOLD and segment.shape[1] >= MIN_WINDOW_SAMPLES:
                emb = encoder.encode_batch(segment)
                all_embeddings.append(emb.squeeze().cpu().numpy())
            continue

        # Slide windows over this segment
        offset = 0
        while offset < segment.shape[1]:
            end = min(offset + window_samples, segment.shape[1])
            chunk = segment[:, offset:end]

            if chunk.shape[1] < MIN_WINDOW_SAMPLES:
                break

            rms = torch.sqrt(torch.mean(chunk**2)).item()
            if rms >= SILENCE_RMS_THRESHOLD:
                emb = encoder.encode_batch(chunk)
                all_embeddings.append(emb.squeeze().cpu().numpy())

            offset += hop_samples

    if not all_embeddings:
        return None

    # Average and L2-normalize
    avg_embedding = np.mean(all_embeddings, axis=0)
    norm = np.linalg.norm(avg_embedding)
    if norm > 0:
        avg_embedding = avg_embedding / norm

    return avg_embedding


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


SIGNATURE_SIMILARITY_THRESHOLD = 0.25


def diarize_with_signatures(
    wav_path: Path,
    signatures: list[tuple[int, np.ndarray]],
) -> list[SpeakerSegment]:
    """Diarize by matching audio windows against known voice signatures.

    Args:
        wav_path: Path to WAV file.
        signatures: List of (roster_entry_id, embedding) pairs.

    Returns:
        List of SpeakerSegments with labels like "roster_<id>" or "Unknown Speaker".
    """
    waveform = _load_waveform(wav_path)
    embeddings, timestamps = _extract_windowed_embeddings(waveform)

    if len(timestamps) == 0:
        return []

    # Build signature matrix for vectorized comparison
    sig_ids = [s[0] for s in signatures]
    sig_matrix = np.stack([s[1] for s in signatures])  # [num_sigs, dim]

    # Normalize embeddings for cosine similarity (signatures are already L2-normalized)
    emb_norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    emb_norms[emb_norms == 0] = 1
    normed_embeddings = embeddings / emb_norms

    # Cosine similarity: [num_windows, num_sigs]
    similarities = normed_embeddings @ sig_matrix.T

    raw_segments = []
    for i, (start, end) in enumerate(timestamps):
        best_idx = np.argmax(similarities[i])
        best_sim = similarities[i, best_idx]

        if best_sim >= SIGNATURE_SIMILARITY_THRESHOLD:
            label = f"roster_{sig_ids[best_idx]}"
        else:
            label = "Unknown Speaker"

        raw_segments.append(SpeakerSegment(
            speaker_label=label,
            start_time=start,
            end_time=end,
        ))

    return _merge_segments(raw_segments)


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


def diarize(wav_path: Path, num_speakers: int | None = None) -> list[SpeakerSegment]:
    """Run diarization on a WAV file and return speaker segments."""
    return _run_pipeline(wav_path, num_speakers)


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


async def generate_voice_signatures(session_id: int) -> list[dict]:
    """Generate voice signatures from a manually-labeled session.

    For each speaker linked to a roster entry, extract an averaged embedding
    from their transcript segments and store it in the voice_signatures table.
    Returns a list of dicts with roster_entry_id, player_name, character_name, num_samples.
    """
    import json
    from talekeeper.db import get_db
    from talekeeper.services.audio import audio_to_wav

    async with get_db() as db:
        # Get session info
        session = await db.execute_fetchall(
            "SELECT id, campaign_id, audio_path FROM sessions WHERE id = ?",
            (session_id,),
        )
        if not session:
            raise ValueError(f"Session {session_id} not found")
        session = dict(session[0])
        campaign_id = session["campaign_id"]
        audio_path = session["audio_path"]

        if not audio_path:
            raise ValueError(f"Session {session_id} has no audio")

        # Get speakers linked to roster entries (match on player_name + character_name)
        speakers_with_roster = await db.execute_fetchall(
            """
            SELECT s.id as speaker_id, s.player_name, s.character_name,
                   r.id as roster_entry_id
            FROM speakers s
            JOIN roster_entries r ON r.campaign_id = ? AND r.player_name = s.player_name
                AND r.character_name = s.character_name AND r.is_active = 1
            WHERE s.session_id = ? AND s.player_name IS NOT NULL AND s.character_name IS NOT NULL
            """,
            (campaign_id, session_id),
        )

        if not speakers_with_roster:
            return []

        # Convert audio to WAV
        audio_file = Path(audio_path)
        wav_path = audio_to_wav(audio_file)

        try:
            waveform = _load_waveform(wav_path)

            results = []
            for row in speakers_with_roster:
                speaker = dict(row)
                # Get transcript segments for this speaker
                segments = await db.execute_fetchall(
                    "SELECT start_time, end_time FROM transcript_segments WHERE session_id = ? AND speaker_id = ? ORDER BY start_time",
                    (session_id, speaker["speaker_id"]),
                )

                time_ranges = [(s["start_time"], s["end_time"]) for s in segments]
                if not time_ranges:
                    continue

                embedding = extract_speaker_embedding(waveform, time_ranges)
                if embedding is None:
                    continue

                embedding_json = json.dumps(embedding.tolist())
                num_samples = len(time_ranges)

                # Replace existing signature for this roster entry
                await db.execute(
                    "DELETE FROM voice_signatures WHERE roster_entry_id = ?",
                    (speaker["roster_entry_id"],),
                )
                await db.execute(
                    """INSERT INTO voice_signatures
                       (campaign_id, roster_entry_id, embedding, source_session_id, num_samples)
                       VALUES (?, ?, ?, ?, ?)""",
                    (campaign_id, speaker["roster_entry_id"], embedding_json, session_id, num_samples),
                )

                results.append({
                    "roster_entry_id": speaker["roster_entry_id"],
                    "player_name": speaker["player_name"],
                    "character_name": speaker["character_name"],
                    "num_samples": num_samples,
                })

            return results
        finally:
            if wav_path.exists() and wav_path != audio_file:
                wav_path.unlink()


async def run_final_diarization(
    session_id: int, wav_path: Path, num_speakers_override: int | None = None
) -> None:
    """Run final diarization pass and update all speaker labels in DB.

    When voice signatures exist for the session's campaign, uses signature-based
    matching. Otherwise falls back to unsupervised clustering.

    If num_speakers_override is provided, it is used instead of the campaign's
    num_speakers setting.
    """
    import json
    from talekeeper.db import get_db

    async with get_db() as db:
        # Get campaign_id for this session
        session_rows = await db.execute_fetchall(
            "SELECT campaign_id FROM sessions WHERE id = ?", (session_id,)
        )
        campaign_id = session_rows[0]["campaign_id"] if session_rows else None

        # Use override if provided, otherwise fetch from campaign
        num_speakers = num_speakers_override
        if num_speakers is None and campaign_id:
            campaign_rows = await db.execute_fetchall(
                "SELECT num_speakers FROM campaigns WHERE id = ?", (campaign_id,)
            )
            if campaign_rows:
                num_speakers = campaign_rows[0]["num_speakers"]

        # Check for voice signatures
        signatures = []
        if campaign_id:
            sig_rows = await db.execute_fetchall(
                """SELECT vs.roster_entry_id, vs.embedding, r.player_name, r.character_name
                   FROM voice_signatures vs
                   JOIN roster_entries r ON r.id = vs.roster_entry_id
                   WHERE vs.campaign_id = ?""",
                (campaign_id,),
            )
            for row in sig_rows:
                emb = np.array(json.loads(row["embedding"]))
                signatures.append((
                    row["roster_entry_id"],
                    emb,
                    row["player_name"],
                    row["character_name"],
                ))

    if signatures:
        # Signature-based diarization
        sig_pairs = [(s[0], s[1]) for s in signatures]
        segments = diarize_with_signatures(wav_path, sig_pairs)

        # Build roster info lookup
        roster_info = {s[0]: (s[2], s[3]) for s in signatures}

        async with get_db() as db:
            speaker_id_map = {}
            for seg in segments:
                label = seg.speaker_label
                if label in speaker_id_map:
                    continue

                if label.startswith("roster_"):
                    roster_id = int(label.split("_", 1)[1])
                    player_name, character_name = roster_info[roster_id]
                    friendly_label = f"{character_name} ({player_name})"
                    cursor = await db.execute(
                        """INSERT INTO speakers (session_id, diarization_label, player_name, character_name)
                           VALUES (?, ?, ?, ?)""",
                        (session_id, friendly_label, player_name, character_name),
                    )
                else:
                    # Unknown Speaker
                    cursor = await db.execute(
                        "INSERT INTO speakers (session_id, diarization_label) VALUES (?, ?)",
                        (session_id, label),
                    )
                speaker_id_map[label] = cursor.lastrowid

            # Align and update transcript segments
            t_rows = await db.execute_fetchall(
                "SELECT id, start_time, end_time FROM transcript_segments WHERE session_id = ? ORDER BY start_time",
                (session_id,),
            )
            transcript_segs = [dict(r) for r in t_rows]
            aligned = align_speakers_with_transcript(segments, transcript_segs)

            for seg in aligned:
                label = seg.get("speaker_label")
                if label and label in speaker_id_map:
                    await db.execute(
                        "UPDATE transcript_segments SET speaker_id = ? WHERE id = ?",
                        (speaker_id_map[label], seg["id"]),
                    )
    else:
        # Fallback: unsupervised clustering
        segments = diarize(wav_path, num_speakers)
        unique_labels = sorted(set(s.speaker_label for s in segments))

        async with get_db() as db:
            speaker_id_map = {}
            for idx, label in enumerate(unique_labels, start=1):
                friendly_label = f"Player {idx}"
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

            t_rows = await db.execute_fetchall(
                "SELECT id, start_time, end_time FROM transcript_segments WHERE session_id = ? ORDER BY start_time",
                (session_id,),
            )
            transcript_segs = [dict(r) for r in t_rows]
            aligned = align_speakers_with_transcript(segments, transcript_segs)

            for seg in aligned:
                label = seg.get("speaker_label")
                if label and label in speaker_id_map:
                    await db.execute(
                        "UPDATE transcript_segments SET speaker_id = ? WHERE id = ?",
                        (speaker_id_map[label], seg["id"]),
                    )
