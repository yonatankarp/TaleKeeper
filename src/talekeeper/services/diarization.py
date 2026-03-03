"""Speaker diarization service using pyannote.audio."""

import logging
import os
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from talekeeper.db import get_db

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16_000

_pipeline = None
_embedding_model = None


@dataclass
class SpeakerSegment:
    speaker_label: str
    start_time: float
    end_time: float


async def _resolve_hf_token() -> str:
    """Resolve HuggingFace token: settings table > HF_TOKEN env var.

    Raises ValueError if no token is configured.
    """
    try:
        async with get_db() as db:
            rows = await db.execute_fetchall(
                "SELECT value FROM settings WHERE key = 'hf_token'"
            )
            if rows and rows[0]["value"]:
                return rows[0]["value"]
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


def _get_pipeline(hf_token: str):
    """Load and cache the pyannote diarization pipeline on MPS."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    import torch
    from pyannote.audio import Pipeline

    logger.info("Loading pyannote speaker-diarization-3.1 pipeline")
    _pipeline = Pipeline.from_pretrained(
        "pyannote/speaker-diarization-3.1",
        use_auth_token=hf_token,
    )

    # Target Apple GPU via MPS
    if torch.backends.mps.is_available():
        _pipeline.to(torch.device("mps"))
        logger.info("Pyannote pipeline moved to MPS device")

    return _pipeline


def _get_embedding_model(hf_token: str):
    """Load and cache the pyannote embedding model."""
    global _embedding_model
    if _embedding_model is not None:
        return _embedding_model

    import torch
    from pyannote.audio import Inference

    logger.info("Loading pyannote/embedding model")
    _embedding_model = Inference(
        "pyannote/embedding",
        use_auth_token=hf_token,
    )

    if torch.backends.mps.is_available():
        _embedding_model.to(torch.device("mps"))

    return _embedding_model


def unload_models() -> None:
    """Unload cached pipeline and embedding model to free memory."""
    global _pipeline, _embedding_model
    _pipeline = None
    _embedding_model = None
    try:
        import torch
        if torch.backends.mps.is_available():
            torch.mps.empty_cache()
    except Exception:
        pass


def diarize(
    wav_path: Path,
    num_speakers: int | None = None,
    hf_token: str | None = None,
) -> list[SpeakerSegment]:
    """Run pyannote diarization on a WAV file and return speaker segments."""
    if hf_token is None:
        raise ValueError("hf_token is required for diarization")

    pipeline = _get_pipeline(hf_token)

    kwargs = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers

    annotation = pipeline(str(wav_path), **kwargs)

    segments = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        segments.append(SpeakerSegment(
            speaker_label=speaker,
            start_time=turn.start,
            end_time=turn.end,
        ))

    return _merge_segments(segments)


def extract_speaker_embedding(
    wav_path: Path,
    time_ranges: list[tuple[float, float]],
    hf_token: str | None = None,
) -> np.ndarray | None:
    """Extract averaged, L2-normalized 192-dim embedding from time ranges using pyannote.

    Args:
        wav_path: Path to WAV file
        time_ranges: List of (start_sec, end_sec) tuples
        hf_token: HuggingFace token

    Returns:
        1-D numpy array (192-dim), or None if no valid embeddings found.
    """
    if hf_token is None:
        raise ValueError("hf_token is required for embedding extraction")

    from pyannote.core import Segment

    model = _get_embedding_model(hf_token)
    all_embeddings = []

    for start_sec, end_sec in time_ranges:
        # Skip very short segments
        if end_sec - start_sec < 0.3:
            continue
        try:
            segment = Segment(start_sec, end_sec)
            embedding = model.crop(str(wav_path), segment)
            if embedding is not None and len(embedding) > 0:
                # embedding shape can be (N, dim) for multi-window or (dim,)
                if embedding.ndim > 1:
                    embedding = np.mean(embedding, axis=0)
                all_embeddings.append(embedding)
        except Exception as e:
            logger.warning("Failed to extract embedding for segment %.1f-%.1f: %s", start_sec, end_sec, e)
            continue

    if not all_embeddings:
        return None

    # Average and L2-normalize
    avg_embedding = np.mean(all_embeddings, axis=0)
    norm = np.linalg.norm(avg_embedding)
    if norm > 0:
        avg_embedding = avg_embedding / norm

    return avg_embedding


def diarize_with_signatures(
    wav_path: Path,
    signatures: list[tuple[int, np.ndarray]],
    similarity_threshold: float = 0.65,
    num_speakers: int | None = None,
    hf_token: str | None = None,
) -> list[SpeakerSegment]:
    """Diarize by running pyannote pipeline then matching speakers against known signatures.

    Args:
        wav_path: Path to WAV file.
        signatures: List of (roster_entry_id, embedding) pairs.
        similarity_threshold: Cosine similarity threshold for matching.
        num_speakers: Optional number of speakers hint.
        hf_token: HuggingFace token.

    Returns:
        List of SpeakerSegments with labels like "roster_<id>" or "Unknown Speaker".
    """
    if hf_token is None:
        raise ValueError("hf_token is required for diarization")

    from pyannote.core import Segment

    pipeline = _get_pipeline(hf_token)
    embedding_model = _get_embedding_model(hf_token)

    # Run diarization
    kwargs = {}
    if num_speakers is not None:
        kwargs["num_speakers"] = num_speakers
    annotation = pipeline(str(wav_path), **kwargs)

    # Get unique speaker labels from pyannote
    speaker_labels = annotation.labels()

    # Extract embedding for each pyannote speaker
    speaker_embeddings: dict[str, np.ndarray] = {}
    for label in speaker_labels:
        segments_for_label = list(annotation.label_timeline(label))
        embs = []
        for seg in segments_for_label:
            if seg.duration < 0.3:
                continue
            try:
                emb = embedding_model.crop(str(wav_path), seg)
                if emb is not None and len(emb) > 0:
                    if emb.ndim > 1:
                        emb = np.mean(emb, axis=0)
                    embs.append(emb)
            except Exception:
                continue

        if embs:
            avg = np.mean(embs, axis=0)
            norm = np.linalg.norm(avg)
            if norm > 0:
                avg = avg / norm
            speaker_embeddings[label] = avg

    # Build signature matrix
    sig_ids = [s[0] for s in signatures]
    sig_matrix = np.stack([s[1] for s in signatures])

    # Match each pyannote speaker to a signature
    label_map: dict[str, str] = {}
    for label, emb in speaker_embeddings.items():
        similarities = emb @ sig_matrix.T
        best_idx = np.argmax(similarities)
        best_sim = similarities[best_idx]

        if best_sim >= similarity_threshold:
            label_map[label] = f"roster_{sig_ids[best_idx]}"
        else:
            label_map[label] = "Unknown Speaker"

    # Build output segments
    raw_segments = []
    for turn, _, speaker in annotation.itertracks(yield_label=True):
        mapped_label = label_map.get(speaker, "Unknown Speaker")
        raw_segments.append(SpeakerSegment(
            speaker_label=mapped_label,
            start_time=turn.start,
            end_time=turn.end,
        ))

    return _merge_segments(raw_segments)


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
            aligned.append(t_seg)
            continue

        overlapping.sort(key=lambda x: x[1], reverse=True)
        t_seg["speaker_label"] = overlapping[0][0].speaker_label
        aligned.append(t_seg)

    return aligned


async def generate_voice_signatures(session_id: int) -> list[dict]:
    """Generate voice signatures from a manually-labeled session.

    For each speaker linked to a roster entry, extract an averaged embedding
    from their transcript segments and store it in the voice_signatures table.
    """
    import json
    from talekeeper.services.audio import audio_to_wav

    hf_token = await _resolve_hf_token()

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

                embedding = extract_speaker_embedding(wav_path, time_ranges, hf_token=hf_token)
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


async def run_final_diarization(
    session_id: int, wav_path: Path, num_speakers_override: int | None = None
) -> None:
    """Run final diarization pass and update all speaker labels in DB.

    When voice signatures exist, uses signature-based matching with the campaign's
    similarity_threshold. Otherwise falls back to unsupervised pyannote diarization.
    """
    import json

    hf_token = await _resolve_hf_token()

    async with get_db() as db:
        session_rows = await db.execute_fetchall(
            "SELECT campaign_id FROM sessions WHERE id = ?", (session_id,)
        )
        campaign_id = session_rows[0]["campaign_id"] if session_rows else None

        num_speakers = num_speakers_override
        similarity_threshold = 0.65

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
            hf_token=hf_token,
        )

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
                    cursor = await db.execute(
                        "INSERT INTO speakers (session_id, diarization_label) VALUES (?, ?)",
                        (session_id, label),
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
    else:
        segments = diarize(wav_path, num_speakers, hf_token=hf_token)
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
