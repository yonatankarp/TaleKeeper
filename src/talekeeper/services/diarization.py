"""Speaker diarization service using diarize library (Silero VAD + WeSpeaker + spectral clustering)."""

import gc
import logging
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf
from scipy.optimize import linear_sum_assignment

from talekeeper.db import get_db

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000

# Embedding extraction constants (matching diarize library internals)
MIN_SEGMENT_DURATION = 0.4
EMBEDDING_WINDOW = 1.2
EMBEDDING_STEP = 0.6

# Overlap detection constant
OVERLAP_RATIO_THRESHOLD = 0.85

# Post-clustering merge: clusters whose centroid cosine similarity exceeds this
# threshold are considered the same speaker and merged. Prevents one speaker from
# appearing as two "Player X" labels when their embeddings vary across the session.
CLUSTER_MERGE_THRESHOLD = 0.75

# Speaker change detection constants
MIN_CHANGE_DETECTION_DURATION = 2.0
CHANGE_DETECTION_WINDOW = 0.4
CHANGE_DETECTION_STEP = 0.2
CHANGE_DETECTION_THRESHOLD = 0.4
CHANGE_DETECTION_MIN_SPLIT_GAP = 3


@dataclass
class SpeakerSegment:
    speaker_label: str
    start_time: float
    end_time: float


ProgressCallback = Callable[[str, dict], None]


async def _resolve_hf_token() -> str:
    """Resolve HuggingFace token: settings table > HF_TOKEN env var.

    Raises ValueError if no token is configured.
    """
    from talekeeper.routers.settings import _decrypt

    try:
        async with get_db() as db:
            rows = await db.execute_fetchall(
                "SELECT value FROM settings WHERE key = 'hf_token'"
            )
            if rows and rows[0]["value"]:
                return _decrypt(rows[0]["value"])
    except Exception:
        pass

    token = os.environ.get("HF_TOKEN", "")
    if token:
        return token

    raise ValueError(
        "HuggingFace token required for speaker diarization. "
        "Set it in Settings > Providers or via the HF_TOKEN environment variable. "
        "You must accept the pyannote license at https://huggingface.co/pyannote/speaker-diarization-3.1"
    )


def unload_models() -> None:
    """No-op — diarize library manages its own model lifecycle. Just gc.collect()."""
    gc.collect()


def _compress_dynamic_range(
    audio: np.ndarray,
    sr: int,
    target_rms: float = 0.1,
    window_sec: float = 0.2,
    step_sec: float = 0.1,
) -> np.ndarray:
    """Apply sliding-window dynamic range compression.

    Quiet speakers far from the mic are inaudible to VAD because loud speakers
    dominate the overall level. This compressor normalizes each short window
    independently so quiet sections are boosted without clipping loud ones.

    Args:
        audio: 1-D float waveform.
        sr: Sample rate.
        target_rms: Desired RMS per window (default 0.1).
        window_sec: Window length in seconds.
        step_sec: Hop between windows in seconds.

    Returns:
        Compressed and clipped audio array.
    """
    win_samples = int(window_sec * sr)
    step_samples = int(step_sec * sr)

    output = np.zeros(len(audio), dtype=np.float64)
    weight = np.zeros(len(audio), dtype=np.float64)
    window = np.hanning(win_samples)

    pos = 0
    while pos + win_samples <= len(audio):
        chunk = audio[pos:pos + win_samples]
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        scale = target_rms / rms if rms > 1e-6 else 1.0
        output[pos:pos + win_samples] += chunk * scale * window
        weight[pos:pos + win_samples] += window
        pos += step_samples

    mask = weight > 1e-8
    output[mask] /= weight[mask]
    return np.clip(output, -1.0, 1.0)


def _normalize_audio_file(wav_path: Path) -> Path:
    """Write a dynamically-compressed copy of a WAV file to a temp file.

    Uses sliding-window compression so that quiet speakers (far from the mic)
    are boosted independently of loud speakers before VAD and segmentation.

    Args:
        wav_path: Path to the original WAV file.

    Returns:
        Path to the compressed temp WAV file. Caller must delete it when done.
    """
    audio, sr = sf.read(str(wav_path))
    if audio.ndim > 1:
        audio = audio.mean(axis=1)

    compressed = _compress_dynamic_range(audio, sr)

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, compressed, sr)
    tmp.close()
    logger.debug("Wrote compressed audio to %s", tmp.name)
    return Path(tmp.name)


def _normalize_segment_audio(
    audio: np.ndarray, target_rms: float = 0.1
) -> np.ndarray:
    """Normalize audio segment to target RMS loudness for consistent embeddings.

    Quiet speakers far from the mic produce low-amplitude segments whose
    WeSpeaker embeddings are poor quality. RMS normalization equalizes loudness
    so all speakers produce equally strong embeddings.

    Args:
        audio: 1-D float waveform.
        target_rms: Desired RMS amplitude (default 0.1).

    Returns:
        Normalized and clipped audio array.
    """
    rms = float(np.sqrt(np.mean(audio ** 2)))
    if rms < 1e-6:
        return audio
    scale = target_rms / rms
    return np.clip(audio * scale, -1.0, 1.0)


def _extract_fine_stride_embeddings(
    audio_data: np.ndarray,
    sr: int,
    seg_start: float,
    seg_end: float,
) -> tuple[np.ndarray, list[float]]:
    """Extract WeSpeaker embeddings at fine stride for speaker change detection.

    Args:
        audio_data: Full audio waveform (mono).
        sr: Sample rate.
        seg_start: Segment start time in seconds.
        seg_end: Segment end time in seconds.

    Returns:
        (embeddings, timestamps) where embeddings is (N, 256) ndarray and
        timestamps is a list of window center times.
    """
    import wespeakerruntime

    model = wespeakerruntime.Speaker(lang="en")

    embeddings: list[np.ndarray] = []
    timestamps: list[float] = []

    win_start = seg_start
    while win_start + CHANGE_DETECTION_WINDOW <= seg_end + 1e-6:
        win_end = min(win_start + CHANGE_DETECTION_WINDOW, seg_end)
        if win_end - win_start < MIN_SEGMENT_DURATION:
            break

        start_sample = int(win_start * sr)
        end_sample = int(win_end * sr)
        segment_audio = audio_data[start_sample:end_sample]
        segment_audio = _normalize_segment_audio(segment_audio)

        tmp_path: str | None = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                sf.write(tmp_path, segment_audio, sr)
            emb = model.extract_embedding(tmp_path)
        except Exception:
            logger.debug("Fine-stride embedding failed for window %.2f-%.2f", win_start, win_end)
            win_start += CHANGE_DETECTION_STEP
            continue
        finally:
            if tmp_path is not None:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass

        if emb is not None:
            if emb.ndim == 2:
                emb = emb[0]
            embeddings.append(emb)
            timestamps.append((win_start + win_end) / 2.0)

        win_start += CHANGE_DETECTION_STEP

    if not embeddings:
        return np.empty((0, 256), dtype=np.float32), []

    return np.stack(embeddings), timestamps


def _find_speaker_change_points(
    embeddings: np.ndarray,
    timestamps: list[float],
) -> list[float]:
    """Find speaker change points using cosine distance peaks between consecutive embeddings.

    Args:
        embeddings: (N, 256) ndarray of fine-stride embeddings.
        timestamps: List of window center times corresponding to each embedding.

    Returns:
        List of timestamps where speaker changes are detected.
    """
    from scipy.signal import find_peaks
    from scipy.spatial.distance import cosine

    if len(embeddings) < 2:
        return []

    # Compute cosine distance between consecutive embeddings
    distances = []
    for i in range(len(embeddings) - 1):
        distances.append(cosine(embeddings[i], embeddings[i + 1]))

    distances_arr = np.array(distances)

    peaks, _ = find_peaks(
        distances_arr,
        height=CHANGE_DETECTION_THRESHOLD,
        distance=CHANGE_DETECTION_MIN_SPLIT_GAP,
    )

    # Map peak indices to timestamps (midpoint between consecutive windows)
    change_times = []
    for peak_idx in peaks:
        change_times.append((timestamps[peak_idx] + timestamps[peak_idx + 1]) / 2.0)

    return change_times


def _split_segment_at_changes(
    seg_start: float,
    seg_end: float,
    change_times: list[float],
) -> list[tuple[float, float]]:
    """Split a segment at detected change points, merging short sub-segments.

    Args:
        seg_start: Original segment start time.
        seg_end: Original segment end time.
        change_times: List of split timestamps within the segment.

    Returns:
        List of (start, end) tuples for sub-segments.
    """
    if not change_times:
        return [(seg_start, seg_end)]

    # Build sub-segments
    boundaries = [seg_start] + sorted(change_times) + [seg_end]
    sub_segments = []
    for i in range(len(boundaries) - 1):
        sub_segments.append((boundaries[i], boundaries[i + 1]))

    # Merge sub-segments shorter than MIN_SEGMENT_DURATION with neighbor
    merged = []
    for start, end in sub_segments:
        if end - start < MIN_SEGMENT_DURATION and merged:
            # Merge with previous
            prev_start, _prev_end = merged[-1]
            merged[-1] = (prev_start, end)
        else:
            merged.append((start, end))

    # Check if first segment is too short after merging
    if len(merged) > 1 and merged[0][1] - merged[0][0] < MIN_SEGMENT_DURATION:
        second = merged[1]
        merged = [(merged[0][0], second[1])] + merged[2:]

    return merged


def _detect_speaker_changes(
    audio_path: Path,
    speech_segments: list,
    progress_callback: ProgressCallback | None = None,
) -> list:
    """Detect speaker changes within long VAD segments and split them.

    For segments longer than MIN_CHANGE_DETECTION_DURATION, extracts fine-stride
    embeddings and detects speaker change points. Short segments pass through unchanged.

    Args:
        audio_path: Path to WAV file.
        speech_segments: List of SpeechSegment objects from run_vad().
        progress_callback: Optional callback for progress reporting.

    Returns:
        Refined list of segment-like objects (with .start and .end attributes).
    """
    long_segments = [s for s in speech_segments if s.end - s.start > MIN_CHANGE_DETECTION_DURATION]

    if not long_segments:
        return speech_segments

    if progress_callback:
        progress_callback("change_detection_start", {})

    audio_data, sr = sf.read(str(audio_path))
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    @dataclass
    class SubSegment:
        start: float
        end: float

    refined: list = []
    total_changes = 0

    for seg in speech_segments:
        if seg.end - seg.start <= MIN_CHANGE_DETECTION_DURATION:
            refined.append(seg)
            continue

        embeddings, timestamps = _extract_fine_stride_embeddings(
            audio_data, sr, seg.start, seg.end
        )

        change_times = _find_speaker_change_points(embeddings, timestamps)
        total_changes += len(change_times)

        if not change_times:
            refined.append(seg)
            continue

        sub_segs = _split_segment_at_changes(seg.start, seg.end, change_times)
        for start, end in sub_segs:
            refined.append(SubSegment(start=start, end=end))

    if progress_callback:
        progress_callback("change_detection_done", {
            "num_segments_processed": len(long_segments),
            "num_changes_found": total_changes,
        })

    logger.info(
        "Speaker change detection: processed %d long segments, found %d change points, %d -> %d segments",
        len(long_segments), total_changes, len(speech_segments), len(refined),
    )

    return refined


def _merge_similar_clusters(
    embeddings: np.ndarray,
    labels: np.ndarray,
    threshold: float = CLUSTER_MERGE_THRESHOLD,
) -> np.ndarray:
    """Merge speaker clusters whose centroids are too similar to be different people.

    After spectral clustering, a single speaker can appear as two nearby clusters
    because their voice embeddings drift across a long session. This function
    computes pairwise cosine similarity between L2-normalized cluster centroids and
    merges any pair above `threshold` using union-find, then remaps labels to
    consecutive integers.

    Args:
        embeddings: (N, D) float32 array of speaker embeddings.
        labels: (N,) integer cluster label array.
        threshold: Cosine similarity above which two clusters are merged (default
            CLUSTER_MERGE_THRESHOLD = 0.80).

    Returns:
        New (N,) label array with merged and remapped cluster labels.
    """
    unique = np.unique(labels)
    if len(unique) < 2:
        return labels.copy()

    # Compute L2-normalized centroid per cluster
    centroids: dict[int, np.ndarray] = {}
    for lbl in unique:
        mask = labels == lbl
        c = embeddings[mask].mean(axis=0).astype(np.float64)
        norm = np.linalg.norm(c)
        centroids[lbl] = c / norm if norm > 1e-8 else c

    # Union-find for transitive merges
    parent = {lbl: lbl for lbl in unique}

    def _find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    lbl_list = list(unique)
    merged_count = 0
    for i in range(len(lbl_list)):
        for j in range(i + 1, len(lbl_list)):
            a, b = lbl_list[i], lbl_list[j]
            sim = float(centroids[a] @ centroids[b])
            if sim >= threshold:
                ra, rb = _find(a), _find(b)
                if ra != rb:
                    parent[rb] = ra
                    merged_count += 1

    if merged_count == 0:
        return labels.copy()

    # Apply merge map and remap to consecutive integers
    roots = np.array([_find(int(l)) for l in labels])
    unique_roots = np.unique(roots)
    remap = {old: new for new, old in enumerate(unique_roots)}
    new_labels = np.array([remap[r] for r in roots])
    logger.info(
        "Post-clustering merge: %d clusters -> %d clusters (%d merges, threshold=%.2f)",
        len(unique), len(unique_roots), merged_count, threshold,
    )
    return new_labels


def _flag_overlap_subsegments(
    embeddings: np.ndarray,
    labels: np.ndarray,
    threshold: float = OVERLAP_RATIO_THRESHOLD,
) -> np.ndarray:
    """Return boolean mask: True for embeddings ambiguous between two speaker clusters.

    For each embedding, computes cosine similarity to all cluster centroids.
    If sim_to_second_best / sim_to_best >= threshold, the subsegment is flagged as overlap.

    Args:
        embeddings: (N, D) float32 array of WeSpeaker embeddings.
        labels: (N,) cluster label array.
        threshold: Overlap ratio threshold (default OVERLAP_RATIO_THRESHOLD).

    Returns:
        Boolean mask of shape (N,), True where subsegment is ambiguous (overlap).
    """
    n = len(labels)
    if n == 0:
        return np.zeros(0, dtype=bool)

    unique_labels = np.unique(labels)
    if len(unique_labels) < 2:
        # Single cluster — no ambiguity possible
        return np.zeros(n, dtype=bool)

    # Compute L2-normalized centroid per cluster
    centroids = []
    for lbl in unique_labels:
        mask = labels == lbl
        centroid = np.mean(embeddings[mask], axis=0)
        norm = np.linalg.norm(centroid)
        if norm > 0:
            centroid = centroid / norm
        centroids.append(centroid)
    centroid_matrix = np.stack(centroids)  # (num_clusters, D)

    # Normalize embeddings for cosine similarity
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms = np.where(norms > 0, norms, 1.0)
    normed_embeddings = embeddings / norms

    # Cosine similarity to each centroid: (N, num_clusters)
    sim_matrix = normed_embeddings @ centroid_matrix.T

    # Best and second-best similarity per embedding
    sorted_sims = np.sort(sim_matrix, axis=1)[:, ::-1]  # descending
    best = sorted_sims[:, 0]
    second = sorted_sims[:, 1]

    # Flag as overlap if second/best >= threshold
    safe_best = np.where(best > 0, best, 1.0)
    overlap_mask = (best > 0) & (second / safe_best >= threshold)

    num_flagged = int(np.sum(overlap_mask))
    logger.debug(
        "Overlap detection: flagged %d/%d subsegments as crosstalk (threshold=%.2f)",
        num_flagged, n, threshold,
    )
    return overlap_mask


def _extract_embeddings_with_progress(
    audio_path: Path,
    speech_segments: list,
    progress_callback: ProgressCallback | None = None,
) -> tuple[np.ndarray, list[tuple[float, float, int]]]:
    """Extract 256-dim WeSpeaker embeddings with per-segment progress reporting.

    Args:
        audio_path: Path to audio file (WAV).
        speech_segments: List of SpeechSegment objects from run_vad().
        progress_callback: Optional callback(stage, detail_dict) for progress.

    Returns:
        (embeddings, subsegments) where embeddings is (N, 256) ndarray and
        subsegments is list of (start, end, parent_idx) tuples.
    """
    import wespeakerruntime

    model = wespeakerruntime.Speaker(lang="en")

    audio_data, sr = sf.read(str(audio_path))
    if audio_data.ndim > 1:
        audio_data = audio_data.mean(axis=1)

    embeddings: list[np.ndarray] = []
    subsegments: list[tuple[float, float, int]] = []
    total = len(speech_segments)

    for idx, seg in enumerate(speech_segments):
        seg_duration = seg.end - seg.start

        if seg_duration < MIN_SEGMENT_DURATION:
            if progress_callback:
                progress_callback("embeddings", {"current": idx + 1, "total": total})
            continue

        # Split long segments with a sliding window
        if seg_duration <= EMBEDDING_WINDOW * 1.5:
            windows = [(seg.start, seg.end)]
        else:
            windows: list[tuple[float, float]] = []
            win_start = seg.start
            while win_start + MIN_SEGMENT_DURATION < seg.end:
                win_end = min(win_start + EMBEDDING_WINDOW, seg.end)
                windows.append((win_start, win_end))
                win_start += EMBEDDING_STEP

        for win_start, win_end in windows:
            start_sample = int(win_start * sr)
            end_sample = int(win_end * sr)
            segment_audio = audio_data[start_sample:end_sample]
            segment_audio = _normalize_segment_audio(segment_audio)

            tmp_path: str | None = None
            try:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    tmp_path = tmp.name
                    sf.write(tmp_path, segment_audio, sr)
                emb = model.extract_embedding(tmp_path)
            except Exception:
                logger.debug("Embedding extraction failed for window %.2f-%.2f", win_start, win_end)
                continue
            finally:
                if tmp_path is not None:
                    try:
                        os.unlink(tmp_path)
                    except OSError:
                        pass

            if emb is not None:
                if emb.ndim == 2:
                    emb = emb[0]
                embeddings.append(emb)
                subsegments.append((win_start, win_end, idx))

        if progress_callback:
            progress_callback("embeddings", {"current": idx + 1, "total": total})

    if not embeddings:
        return np.empty((0, 256), dtype=np.float32), []

    X = np.stack(embeddings)
    logger.info("Extracted %d embeddings (dim=%d)", X.shape[0], X.shape[1])
    return X, subsegments


def _build_segments_from_labels(
    speech_segments: list,
    subsegments: list[tuple[float, float, int]],
    labels: np.ndarray,
    overlap_mask: np.ndarray | None = None,
) -> list[SpeakerSegment]:
    """Convert clustering labels into SpeakerSegments, merging adjacent same-speaker segments.

    Args:
        speech_segments: Original VAD speech segments.
        subsegments: List of (start, end, parent_idx) from embedding extraction.
        labels: Cluster labels array from cluster_speakers(), shape (N,).
        overlap_mask: Optional boolean mask (N,); True entries get label "[crosstalk]".

    Returns:
        Merged list of SpeakerSegments.
    """
    if len(subsegments) == 0:
        return []

    # Build raw segments from subsegments + labels
    raw_segments = []
    for i, ((start, end, _parent_idx), label) in enumerate(zip(subsegments, labels)):
        if overlap_mask is not None and overlap_mask[i]:
            speaker_label = "[crosstalk]"
        else:
            speaker_label = f"SPEAKER_{label:02d}"
        raw_segments.append(SpeakerSegment(
            speaker_label=speaker_label,
            start_time=start,
            end_time=end,
        ))

    # Sort by start time
    raw_segments.sort(key=lambda s: s.start_time)

    return _merge_segments(raw_segments)


def diarize(
    wav_path: Path,
    num_speakers: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[SpeakerSegment]:
    """Run diarization pipeline: VAD -> embeddings -> spectral clustering.

    Args:
        wav_path: Path to WAV file.
        num_speakers: Exact number of speakers for clustering.
        progress_callback: Optional callback(stage, detail_dict) for progress.

    Returns:
        List of merged SpeakerSegments.
    """
    from diarize.vad import run_vad
    from diarize.clustering import cluster_speakers

    logger.info("Starting diarization on %s", wav_path.name)

    # Stage 0: Normalize audio loudness so quiet speakers are detected by VAD
    norm_path = _normalize_audio_file(wav_path)
    try:
        # Stage 1: VAD
        if progress_callback:
            progress_callback("vad_start", {})
        speech_segments = run_vad(str(norm_path))
        total_speech = sum(s.end - s.start for s in speech_segments)
        logger.info("VAD found %d speech segments (%.0fs of speech)", len(speech_segments), total_speech)
        if progress_callback:
            progress_callback("vad_done", {
                "num_segments": len(speech_segments),
                "total_speech_seconds": total_speech,
            })

        if not speech_segments:
            return []

        # Stage 2: Speaker change detection
        speech_segments = _detect_speaker_changes(norm_path, speech_segments, progress_callback)

        # Stage 3: Embedding extraction with progress
        # Use original wav_path, not norm_path: WeSpeaker handles loudness variation
        # internally; running AGC before embedding extraction boosts noise alongside
        # speech, worsening SNR for distant speakers rather than helping them.
        embeddings, subsegments = _extract_embeddings_with_progress(
            wav_path, speech_segments, progress_callback
        )

        if embeddings.shape[0] == 0:
            return []

        # Stage 4: Spectral clustering
        if progress_callback:
            progress_callback("clustering_start", {})
        cluster_kwargs = {}
        if num_speakers is not None:
            cluster_kwargs["num_speakers"] = num_speakers
        labels, _details = cluster_speakers(embeddings, **cluster_kwargs)
        labels = _merge_similar_clusters(embeddings, labels)
        num_found_speakers = len(set(labels))
        logger.info("Clustering found %d speakers, %d segments", num_found_speakers, len(labels))
        if progress_callback:
            progress_callback("clustering_done", {
                "num_speakers": num_found_speakers,
                "num_segments": len(labels),
            })

        overlap_mask = _flag_overlap_subsegments(embeddings, labels)
        return _build_segments_from_labels(speech_segments, subsegments, labels, overlap_mask)
    finally:
        try:
            norm_path.unlink()
        except OSError:
            pass


def extract_speaker_embedding(
    wav_path: Path,
    time_ranges: list[tuple[float, float]],
) -> np.ndarray | None:
    """Extract averaged, L2-normalized 256-dim embedding from time ranges using WeSpeaker.

    Args:
        wav_path: Path to WAV file.
        time_ranges: List of (start_sec, end_sec) tuples.

    Returns:
        1-D numpy array (256-dim), or None if no valid embeddings found.
    """
    from diarize.vad import run_vad

    norm_path = _normalize_audio_file(wav_path)
    try:
        # Run VAD to get speech segments
        speech_segments = run_vad(str(norm_path))

        # Speaker change detection
        speech_segments = _detect_speaker_changes(norm_path, speech_segments)

        # Extract all embeddings from original audio (see diarize() for rationale)
        embeddings, subsegments = _extract_embeddings_with_progress(wav_path, speech_segments)

        if embeddings.shape[0] == 0:
            return None

        # Filter to subsegments overlapping with the provided time ranges
        matching_indices = []
        for i, (sub_start, sub_end, _parent_idx) in enumerate(subsegments):
            for range_start, range_end in time_ranges:
                overlap_start = max(sub_start, range_start)
                overlap_end = min(sub_end, range_end)
                if overlap_start < overlap_end:
                    matching_indices.append(i)
                    break

        if not matching_indices:
            return None

        # Average and L2-normalize
        matching_embs = embeddings[matching_indices]
        avg_embedding = np.mean(matching_embs, axis=0)
        norm = np.linalg.norm(avg_embedding)
        if norm > 0:
            avg_embedding = avg_embedding / norm

        return avg_embedding
    finally:
        try:
            norm_path.unlink()
        except OSError:
            pass


def diarize_with_signatures(
    wav_path: Path,
    signatures: list[tuple[int, np.ndarray]],
    similarity_threshold: float = 0.75,
    num_speakers: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> list[SpeakerSegment]:
    """Diarize then match speaker clusters against known voice signatures.

    Two-pass approach:
    1. Run full diarize pipeline (VAD -> embeddings -> clustering)
    2. Compute per-speaker centroids and match against stored signatures

    Args:
        wav_path: Path to WAV file.
        signatures: List of (roster_entry_id, embedding) pairs.
        similarity_threshold: Cosine similarity threshold for matching.
        num_speakers: Exact number of speakers for clustering.
        progress_callback: Optional callback for progress.

    Returns:
        List of SpeakerSegments with labels like "roster_<id>" or "Unknown Speaker".
    """
    from diarize.vad import run_vad
    from diarize.clustering import cluster_speakers

    logger.info("Starting diarization with signatures on %s", wav_path.name)

    # Stage 0: Normalize audio loudness so quiet speakers are detected by VAD
    norm_path = _normalize_audio_file(wav_path)
    try:
        # Stage 1: VAD
        if progress_callback:
            progress_callback("vad_start", {})
        speech_segments = run_vad(str(norm_path))
        total_speech = sum(s.end - s.start for s in speech_segments)
        logger.info("VAD found %d speech segments (%.0fs)", len(speech_segments), total_speech)
        if progress_callback:
            progress_callback("vad_done", {
                "num_segments": len(speech_segments),
                "total_speech_seconds": total_speech,
            })

        if not speech_segments:
            return []

        # Stage 2: Speaker change detection
        speech_segments = _detect_speaker_changes(norm_path, speech_segments, progress_callback)

        # Stage 3: Embedding extraction (original audio — see diarize() for rationale)
        embeddings, subsegments = _extract_embeddings_with_progress(
            wav_path, speech_segments, progress_callback
        )

        if embeddings.shape[0] == 0:
            return []

        # Stage 4: Clustering
        if progress_callback:
            progress_callback("clustering_start", {})
        cluster_kwargs = {}
        if num_speakers is not None:
            cluster_kwargs["num_speakers"] = num_speakers
        labels, _details = cluster_speakers(embeddings, **cluster_kwargs)
        labels = _merge_similar_clusters(embeddings, labels)
        num_found_speakers = len(set(labels))
        logger.info("Clustering found %d speakers", num_found_speakers)
        if progress_callback:
            progress_callback("clustering_done", {
                "num_speakers": num_found_speakers,
                "num_segments": len(labels),
            })

        # Overlap detection: flag ambiguous subsegments before signature matching
        overlap_mask = _flag_overlap_subsegments(embeddings, labels)

        # Stage 5: Match speaker clusters to signatures via Hungarian algorithm
        # Hungarian guarantees a globally optimal 1:1 cluster→signature assignment.
        # Greedy argmax can assign two clusters to the same person while leaving
        # another speaker unmatched — Hungarian prevents that entirely.
        logger.info("Matching speakers to %d voice signatures", len(signatures))

        # Group embeddings by speaker label
        speaker_embeddings: dict[int, list[np.ndarray]] = {}
        for i, label in enumerate(labels):
            label_int = int(label)
            if label_int not in speaker_embeddings:
                speaker_embeddings[label_int] = []
            speaker_embeddings[label_int].append(embeddings[i])

        # Compute L2-normalized centroid per speaker
        speaker_centroids: dict[int, np.ndarray] = {}
        for label_int, embs in speaker_embeddings.items():
            centroid = np.mean(embs, axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            speaker_centroids[label_int] = centroid

        # Build similarity matrix: (num_clusters, num_signatures)
        sig_ids = [s[0] for s in signatures]
        sig_matrix = np.stack([s[1] for s in signatures])
        cluster_labels = list(speaker_centroids.keys())
        centroid_matrix = np.stack([speaker_centroids[l] for l in cluster_labels])
        sim_matrix = centroid_matrix @ sig_matrix.T  # (num_clusters, num_sigs)

        # Hungarian assignment: minimize cost = maximize similarity
        row_ind, col_ind = linear_sum_assignment(1.0 - sim_matrix)

        label_map: dict[int, str] = {l: "Unknown Speaker" for l in cluster_labels}
        for r, c in zip(row_ind, col_ind):
            best_sim = float(sim_matrix[r, c])
            if best_sim >= similarity_threshold:
                label_map[cluster_labels[r]] = f"roster_{sig_ids[c]}"
        logger.info(
            "Hungarian matching: %d/%d clusters matched above threshold %.2f",
            sum(1 for v in label_map.values() if v != "Unknown Speaker"),
            len(cluster_labels),
            similarity_threshold,
        )

        # Build output segments; flagged subsegments get "[crosstalk]" (skip signature matching)
        raw_segments = []
        for i, ((start, end, _parent_idx), label) in enumerate(zip(subsegments, labels)):
            if overlap_mask[i]:
                mapped_label = "[crosstalk]"
            else:
                label_int = int(label)
                mapped_label = label_map.get(label_int, "Unknown Speaker")
            raw_segments.append(SpeakerSegment(
                speaker_label=mapped_label,
                start_time=start,
                end_time=end,
            ))

        raw_segments.sort(key=lambda s: s.start_time)
        return _merge_segments(raw_segments)
    finally:
        try:
            norm_path.unlink()
        except OSError:
            pass


# Minimum duration (seconds) each child must have after splitting.
# Below this threshold, splits are not created — the proportional word
# distribution becomes too sparse and produces empty/single-word segments.
MIN_SPLIT_CHILD_DURATION = 5.0


def _split_transcript_segments(
    transcript_segs: list[dict],
    speaker_segs: list[SpeakerSegment],
) -> list[dict]:
    """Split transcript segments at diarization speaker-change boundaries.

    Only splits where EVERY resulting child would be at least MIN_SPLIT_CHILD_DURATION
    seconds long. Rapid back-and-forth exchanges shorter than that threshold cannot
    be resolved without word-level timestamps and are left as a single segment
    (assigned to the majority speaker by align_speakers_with_transcript).

    Text is distributed proportionally by word count (relative to sub-interval duration).
    All sub-segments become children (id=None) so the original DB row stays intact
    for future re-diarize runs.

    Args:
        transcript_segs: List of dicts with id, session_id, text, start_time, end_time.
        speaker_segs: List of SpeakerSegment objects from diarization.

    Returns:
        Expanded list of transcript segment dicts (may be longer than input).
    """
    result: list[dict] = []

    for t_seg in transcript_segs:
        t_start = t_seg["start_time"]
        t_end = t_seg["end_time"]

        # Collect diarization start-times that fall strictly inside this segment
        all_split_points = sorted({
            s.start_time for s in speaker_segs
            if t_start < s.start_time < t_end
        })

        if not all_split_points:
            result.append(t_seg)
            continue

        # Filter: greedily keep only split points that are at least
        # MIN_SPLIT_CHILD_DURATION seconds from the previous kept point.
        valid_split_points: list[float] = []
        prev = t_start
        for pt in all_split_points:
            if pt - prev >= MIN_SPLIT_CHILD_DURATION:
                valid_split_points.append(pt)
                prev = pt

        # Also drop the last split point if the final interval would be too short.
        while valid_split_points and t_end - valid_split_points[-1] < MIN_SPLIT_CHILD_DURATION:
            valid_split_points.pop()

        if not valid_split_points:
            result.append(t_seg)
            continue

        # Build final sub-intervals
        boundaries = [t_start] + valid_split_points + [t_end]
        merged: list[tuple[float, float]] = [
            (boundaries[i], boundaries[i + 1]) for i in range(len(boundaries) - 1)
        ]

        # Split text proportionally by word count
        words = (t_seg.get("text") or "").split()
        total_duration = t_end - t_start
        word_chunks: list[list[str]] = []
        remaining = words[:]
        for start, end in merged[:-1]:
            proportion = (end - start) / total_duration if total_duration > 0 else 1.0 / len(merged)
            n = max(0, min(round(proportion * len(words)), len(remaining)))
            word_chunks.append(remaining[:n])
            remaining = remaining[n:]
        word_chunks.append(remaining)

        # Original row is superseded — all sub-segments become children (id=None)
        # so the original row stays intact in the DB for future re-diarize runs.
        original_id = t_seg["id"]
        for (start, end), chunk in zip(merged, word_chunks):
            child = dict(t_seg)
            child["id"] = None
            child["parent_segment_id"] = original_id
            child["start_time"] = start
            child["end_time"] = end
            child["text"] = " ".join(chunk)
            result.append(child)

    logger.debug(
        "Transcript split: %d segments -> %d segments at diarization boundaries",
        len(transcript_segs), len(result),
    )
    return result


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


def align_speakers_with_transcript(
    speaker_segments: list[SpeakerSegment],
    transcript_segments: list[dict],
) -> list[dict]:
    """Align speaker labels with transcript segments.

    For each transcript segment, find the speaker segment that
    overlaps the most and assign that speaker.
    """
    aligned = []

    for t_seg in transcript_segments:
        t_start = t_seg["start_time"]
        t_end = t_seg["end_time"]

        overlapping = []
        for s_seg in speaker_segments:
            overlap_start = max(t_start, s_seg.start_time)
            overlap_end = min(t_end, s_seg.end_time)
            if overlap_start < overlap_end:
                overlapping.append((s_seg, overlap_end - overlap_start))

        if not overlapping:
            t_seg["is_overlap"] = 0
            aligned.append(t_seg)
            continue

        overlapping.sort(key=lambda x: x[1], reverse=True)
        best_seg = overlapping[0][0]
        if best_seg.speaker_label == "[crosstalk]":
            t_seg["is_overlap"] = 1
            # Don't assign speaker_label — segment stays unassigned
        else:
            t_seg["is_overlap"] = 0
            t_seg["speaker_label"] = best_seg.speaker_label
        aligned.append(t_seg)

    return aligned


async def generate_voice_signatures(session_id: int) -> list[dict]:
    """Generate voice signatures from a manually-labeled session.

    For each speaker linked to a roster entry, extract an averaged embedding
    from their transcript segments and store it in the voice_signatures table.
    """
    import json
    from talekeeper.services.audio import audio_to_wav

    async with get_db() as db:
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

        audio_file = Path(audio_path)
        wav_path = audio_to_wav(audio_file)

        try:
            results = []
            for row in speakers_with_roster:
                speaker = dict(row)
                segments = await db.execute_fetchall(
                    "SELECT start_time, end_time FROM transcript_segments WHERE session_id = ? AND speaker_id = ? ORDER BY start_time",
                    (session_id, speaker["speaker_id"]),
                )

                time_ranges = [(s["start_time"], s["end_time"]) for s in segments]
                if not time_ranges:
                    continue

                embedding = extract_speaker_embedding(wav_path, time_ranges)
                if embedding is None:
                    continue

                embedding_json = json.dumps(embedding.tolist())
                num_samples = len(time_ranges)

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


async def enroll_speaker_voice(speaker_id: int, session_id: int) -> None:
    """Enroll or update a voice signature when a speaker is assigned to a roster entry.

    Samples up to 120 seconds of the speaker's transcript segments (longest first),
    extracts an embedding via extract_speaker_embedding, then creates a new signature
    or weighted-merges with the existing one. Silently returns on any missing prerequisite.
    """
    import json
    from talekeeper.services.audio import audio_to_wav

    _AUDIO_CAP_SECONDS = 120.0
    _MIN_SEGMENT_SECS = 0.5

    async with get_db() as db:
        speaker_rows = await db.execute_fetchall(
            "SELECT * FROM speakers WHERE id = ?", (speaker_id,)
        )
        if not speaker_rows:
            logger.warning("enroll_speaker_voice: speaker %d not found", speaker_id)
            return
        speaker = dict(speaker_rows[0])

        if not speaker.get("player_name") or not speaker.get("character_name"):
            logger.debug("enroll_speaker_voice: speaker %d has no player/character name", speaker_id)
            return

        session_rows = await db.execute_fetchall(
            "SELECT id, campaign_id, audio_path FROM sessions WHERE id = ?", (session_id,)
        )
        if not session_rows:
            logger.warning("enroll_speaker_voice: session %d not found", session_id)
            return
        session = dict(session_rows[0])

        if not session.get("audio_path"):
            logger.warning("enroll_speaker_voice: session %d has no audio path", session_id)
            return

        audio_path = Path(session["audio_path"])
        if not audio_path.exists():
            logger.warning("enroll_speaker_voice: audio file %s not found", audio_path)
            return

        campaign_id = session["campaign_id"]

        roster_rows = await db.execute_fetchall(
            """SELECT id FROM roster_entries
               WHERE campaign_id = ? AND player_name = ? AND character_name = ? AND is_active = 1""",
            (campaign_id, speaker["player_name"], speaker["character_name"]),
        )
        if not roster_rows:
            logger.debug(
                "enroll_speaker_voice: no active roster entry for %s/%s in campaign %d",
                speaker["player_name"], speaker["character_name"], campaign_id,
            )
            return
        roster_entry_id = roster_rows[0]["id"]

        segment_rows = await db.execute_fetchall(
            "SELECT start_time, end_time FROM transcript_segments WHERE session_id = ? AND speaker_id = ?",
            (session_id, speaker_id),
        )
        if not segment_rows:
            logger.debug("enroll_speaker_voice: no segments for speaker %d", speaker_id)
            return

        segments = sorted(
            [(float(r["start_time"]), float(r["end_time"])) for r in segment_rows],
            key=lambda s: s[1] - s[0],
            reverse=True,
        )

        time_ranges: list[tuple[float, float]] = []
        accumulated = 0.0
        for start, end in segments:
            if accumulated >= _AUDIO_CAP_SECONDS:
                break
            remaining = _AUDIO_CAP_SECONDS - accumulated
            actual_end = min(end, start + remaining)
            duration = actual_end - start
            if duration < _MIN_SEGMENT_SECS:
                continue
            time_ranges.append((start, actual_end))
            accumulated += duration

        if not time_ranges:
            logger.debug("enroll_speaker_voice: no usable time ranges for speaker %d", speaker_id)
            return

        existing_rows = await db.execute_fetchall(
            "SELECT embedding, num_samples FROM voice_signatures WHERE roster_entry_id = ?",
            (roster_entry_id,),
        )
        old_embedding = None
        old_count = 0
        if existing_rows:
            old_embedding = np.array(json.loads(existing_rows[0]["embedding"]))
            old_count = int(existing_rows[0]["num_samples"])

    try:
        wav_path = audio_to_wav(audio_path)
        try:
            new_embedding = extract_speaker_embedding(wav_path, time_ranges)
        finally:
            if wav_path.exists() and wav_path != audio_path:
                wav_path.unlink()
    except Exception:
        logger.warning(
            "enroll_speaker_voice: failed to extract embedding for speaker %d",
            speaker_id,
            exc_info=True,
        )
        return

    if new_embedding is None:
        logger.debug("enroll_speaker_voice: no embedding extracted for speaker %d", speaker_id)
        return

    new_count = len(time_ranges)

    if old_embedding is not None and old_count > 0:
        combined = (old_embedding * old_count + new_embedding * new_count) / (old_count + new_count)
        norm = np.linalg.norm(combined)
        if norm > 0:
            combined = combined / norm
        final_embedding = combined
        final_count = old_count + new_count
    else:
        final_embedding = new_embedding
        final_count = new_count

    embedding_json = json.dumps(final_embedding.tolist())

    async with get_db() as db:
        await db.execute(
            "DELETE FROM voice_signatures WHERE roster_entry_id = ?",
            (roster_entry_id,),
        )
        await db.execute(
            """INSERT INTO voice_signatures
               (campaign_id, roster_entry_id, embedding, source_session_id, num_samples)
               VALUES (?, ?, ?, ?, ?)""",
            (campaign_id, roster_entry_id, embedding_json, session_id, final_count),
        )

    logger.info(
        "enroll_speaker_voice: enrolled speaker %d (roster_entry %d), %d total samples (was %d)",
        speaker_id, roster_entry_id, final_count, old_count,
    )


async def run_final_diarization(
    session_id: int,
    wav_path: Path,
    num_speakers_override: int | None = None,
    progress_callback: ProgressCallback | None = None,
) -> None:
    """Run final diarization pass and update all speaker labels in DB.

    When voice signatures exist, uses signature-based matching with the campaign's
    similarity_threshold. Otherwise falls back to unsupervised diarization.
    """
    import json

    async with get_db() as db:
        session_rows = await db.execute_fetchall(
            "SELECT campaign_id FROM sessions WHERE id = ?", (session_id,)
        )
        campaign_id = session_rows[0]["campaign_id"] if session_rows else None

        num_speakers = num_speakers_override
        similarity_threshold = 0.75

        if campaign_id:
            campaign_rows = await db.execute_fetchall(
                "SELECT num_speakers, similarity_threshold FROM campaigns WHERE id = ?", (campaign_id,)
            )
            if campaign_rows:
                if num_speakers is None:
                    num_speakers = campaign_rows[0]["num_speakers"]
                if campaign_rows[0]["similarity_threshold"] is not None:
                    similarity_threshold = campaign_rows[0]["similarity_threshold"]

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
        sig_pairs = [(s[0], s[1]) for s in signatures]
        segments = diarize_with_signatures(
            wav_path, sig_pairs,
            similarity_threshold=similarity_threshold,
            num_speakers=num_speakers,
            progress_callback=progress_callback,
        )

        roster_info = {s[0]: (s[2], s[3]) for s in signatures}

        async with get_db() as db:
            speaker_id_map = {}
            for seg in segments:
                label = seg.speaker_label
                if label == "[crosstalk]" or label in speaker_id_map:
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
                    cursor = await db.execute(
                        "INSERT INTO speakers (session_id, diarization_label) VALUES (?, ?)",
                        (session_id, label),
                    )
                speaker_id_map[label] = cursor.lastrowid

            t_rows = await db.execute_fetchall(
                "SELECT id, session_id, text, start_time, end_time FROM transcript_segments WHERE session_id = ? ORDER BY start_time",
                (session_id,),
            )
            transcript_segs = [dict(r) for r in t_rows]
            transcript_segs = _split_transcript_segments(transcript_segs, segments)
            aligned = align_speakers_with_transcript(segments, transcript_segs)

            for seg in aligned:
                is_overlap = seg.get("is_overlap", 0)
                label = seg.get("speaker_label")
                if seg.get("id") is not None:
                    if is_overlap:
                        await db.execute(
                            "UPDATE transcript_segments SET speaker_id = NULL, is_overlap = 1 WHERE id = ?",
                            (seg["id"],),
                        )
                    elif label and label in speaker_id_map:
                        await db.execute(
                            "UPDATE transcript_segments SET speaker_id = ?, is_overlap = 0 WHERE id = ?",
                            (speaker_id_map[label], seg["id"]),
                        )
                    else:
                        await db.execute(
                            "UPDATE transcript_segments SET is_overlap = 0 WHERE id = ?",
                            (seg["id"],),
                        )
                else:
                    speaker_id_val = speaker_id_map.get(label) if (label and not is_overlap) else None
                    await db.execute(
                        """INSERT INTO transcript_segments
                           (session_id, parent_segment_id, speaker_id, text, start_time, end_time, is_overlap)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            seg["session_id"],
                            seg.get("parent_segment_id"),
                            speaker_id_val,
                            seg.get("text", ""),
                            seg["start_time"],
                            seg["end_time"],
                            1 if is_overlap else 0,
                        ),
                    )
    else:
        segments = diarize(wav_path, num_speakers, progress_callback=progress_callback)
        # Exclude [crosstalk] from speaker creation
        unique_labels = sorted(set(
            s.speaker_label for s in segments if s.speaker_label != "[crosstalk]"
        ))

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
                "SELECT id, session_id, text, start_time, end_time FROM transcript_segments WHERE session_id = ? ORDER BY start_time",
                (session_id,),
            )
            transcript_segs = [dict(r) for r in t_rows]
            transcript_segs = _split_transcript_segments(transcript_segs, segments)
            aligned = align_speakers_with_transcript(segments, transcript_segs)

            for seg in aligned:
                is_overlap = seg.get("is_overlap", 0)
                label = seg.get("speaker_label")
                if seg.get("id") is not None:
                    if is_overlap:
                        await db.execute(
                            "UPDATE transcript_segments SET speaker_id = NULL, is_overlap = 1 WHERE id = ?",
                            (seg["id"],),
                        )
                    elif label and label in speaker_id_map:
                        await db.execute(
                            "UPDATE transcript_segments SET speaker_id = ?, is_overlap = 0 WHERE id = ?",
                            (speaker_id_map[label], seg["id"]),
                        )
                    else:
                        await db.execute(
                            "UPDATE transcript_segments SET is_overlap = 0 WHERE id = ?",
                            (seg["id"],),
                        )
                else:
                    speaker_id_val = speaker_id_map.get(label) if (label and not is_overlap) else None
                    await db.execute(
                        """INSERT INTO transcript_segments
                           (session_id, parent_segment_id, speaker_id, text, start_time, end_time, is_overlap)
                           VALUES (?, ?, ?, ?, ?, ?, ?)""",
                        (
                            seg["session_id"],
                            seg.get("parent_segment_id"),
                            speaker_id_val,
                            seg.get("text", ""),
                            seg["start_time"],
                            seg["end_time"],
                            1 if is_overlap else 0,
                        ),
                    )
