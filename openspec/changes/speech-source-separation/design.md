## Context

The diarization pipeline (`services/diarization.py`) processes a single mixed-channel recording where all players share one microphone. When a distant player speaks at the same time as a nearby player, the nearby player's voice dominates the audio — the distant player's voice is effectively invisible to WeSpeaker because the embedding is computed on the mixed signal. The overlap-detection-crosstalk change marks these segments as `[crosstalk]` rather than misattributing them, but still loses the content. Source separation runs before diarization and decomposes the mixed channel into separated streams — giving WeSpeaker cleaner, single-speaker audio to embed.

The existing pipeline is: AGC compression → VAD → speaker change detection → embedding extraction → clustering → signature matching. Source separation inserts as stage 0, before AGC, and feeds separated streams into the subsequent stages.

SpeechBrain is already the third speaker embedding backend the project has evaluated (after pyannote and WeSpeaker). The `diarize` library's `wespeakerruntime` handles embeddings today. SpeechBrain for *separation* (not embeddings) is a distinct use case that avoids the MPS/PyTorch issues that caused pyannote to be removed — separation runs as a single CPU inference pass over the full audio file, not a streaming per-segment inference like pyannote's diarization pipeline.

## Goals / Non-Goals

**Goals:**
- Decompose the single-channel recording into 2 separated speaker streams before diarization
- Feed both streams through VAD + embedding extraction, pooling the cleaner embeddings into clustering
- Expose separation as an opt-in boolean per campaign (off by default)
- Report separation progress via two new SSE stage events (`separation_start`, `separation_done`)
- Clean up separated stream temp files in `finally` blocks

**Non-Goals:**
- Separating more than 2 simultaneous speakers (SepFormer is a 2-speaker model; 3+ simultaneous speakers are not improved by this change)
- Replacing the existing embedding or clustering steps — separation feeds into the same pipeline
- Running separation during live recording (post-session only)
- Improving attribution for players speaking alone (separation helps overlap segments only)

## Decisions

### 1. Model: SpeechBrain SepFormer over Conv-TasNet or Demucs

Use SpeechBrain's `speechbrain/sepformer-wsj02mix` (pre-trained on WSJ0-2mix, 2-speaker English speech separation).

**Why:** SepFormer is trained specifically on conversational speech and achieves state-of-the-art SI-SNRi on the WSJ0-2mix benchmark. Conv-TasNet is smaller but lower quality. Demucs (`htdemucs`) is designed for music source separation (vocals/drums/bass) — it works on speech but is not optimised for it. SpeechBrain has an Apache 2.0 license, runs on CPU, and the model is ~200MB.

**Alternative considered: Asteroid toolkit (Conv-TasNet).** Rejected — lower separation quality than SepFormer, and Asteroid has fewer active maintainers. SepFormer is better without meaningful added complexity.

**Alternative considered: Demucs `htdemucs`.** Rejected — the "vocals" output from Demucs captures the loudest voice (typically the DM), not a balanced 2-speaker separation. Its training data is music, not tabletop sessions.

### 2. Pipeline integration: separate full audio, pool both streams into existing VAD+embedding stages

Run SepFormer on the full session audio, producing 2 output streams (stream_0.wav, stream_1.wav). Then run VAD + embedding extraction independently on each stream. Pool all embeddings from both streams together into the existing clustering step, tagging each embedding with its source stream. All downstream stages (clustering, signature matching, segment assembly) remain unchanged.

**Why:** This is the minimal integration point. The existing pipeline already handles variable numbers of embeddings from a variable number of subsegments. Feeding 2× the embeddings (one set per stream) requires no structural changes to clustering or signature matching. VAD on separated streams naturally filters out the "bleed" (when stream_0 contains mainly speaker A, stream_1 for the same time window is largely silence — VAD skips it).

**Alternative considered: Replace the original audio entirely with separated streams.** Rejected — if separation degrades quality for non-overlapping segments (a real risk), the entire session is harmed. Pooling keeps original embeddings alongside separated ones; clustering will weight the cleaner embeddings naturally.

**Alternative considered: Run separation only on segments flagged as [crosstalk] by overlap detection.** Rejected — overlap detection runs after embedding extraction. Running it before requires a two-pass pipeline (first pass for overlap detection, second for separation). The added complexity isn't justified at this stage.

### 3. Separation as a new `services/separation.py` service, not inline in `diarization.py`

Implement `separate_audio(wav_path: Path, progress_callback) -> list[Path]` in a new service module. `diarization.py` calls it as stage 0 when `source_separation_enabled` is true.

**Why:** `diarization.py` is already 1,000+ lines. Separation has its own model lifecycle (download on first use, CPU inference, temp file management). Isolating it makes the separation logic independently testable and keeps diarization.py readable.

**Alternative considered: Inline in diarization.py.** Rejected — the module is already large and the separation model lifecycle is distinct from the WeSpeaker lifecycle.

### 4. CPU inference in a thread pool executor

SpeechBrain's SepFormer is a PyTorch model running on CPU (no MPS — separation doesn't hit the MPS timestamp bug because it processes the full waveform in one call, not streaming per-segment inference). Since it's CPU-bound and runs synchronously, it must be called via `asyncio.get_event_loop().run_in_executor(None, ...)` to avoid blocking the async event loop.

**Why:** The existing pattern for blocking work (VAD, WeSpeaker) in `diarization.py` is to call them synchronously inside functions that are themselves called from async contexts using FastAPI's thread pool. Source separation follows the same pattern — no new infrastructure needed.

**Alternative considered: Dedicated worker process.** Rejected — overkill for a single-user local app. Thread pool is sufficient.

### 5. `source_separation_enabled` as a campaign boolean, default false

Add `source_separation_enabled INTEGER NOT NULL DEFAULT 0` to the `campaigns` table via additive migration. The campaign edit form gains a toggle with a processing time warning.

**Why:** Separation adds ~0.5–1× real-time overhead (a 30-min session takes 15–30 min extra). Most sessions won't need it. Per-campaign opt-in means the DM can enable it only for sessions with a known distant-player problem, without slowing down other campaigns.

**Alternative considered: Global setting in the settings table.** Rejected — different campaigns may have different setups (same group, different venues). Per-campaign is more precise.

### 6. Fallback: if separation fails, continue with original audio

If `separate_audio` raises an exception (e.g., model download fails, out of memory), log the error and continue diarization on the original audio without separation. Emit a `separation_error` SSE progress event so the frontend can surface a warning.

**Why:** A failed separation should not abort the entire session processing. Falling back to non-separated diarization is better than a total failure.

## Risks / Trade-offs

**[Separation degrades quality for clean recordings]** SepFormer can introduce artefacts (echoes, spectral smearing) on audio that has no significant overlap. Pooling both streams with the original mitigates this — clean original embeddings will form tight clusters while artefact-bearing stream embeddings will be outliers. → Monitor by comparing clustering quality (inter-cluster distance) with and without separation on test sessions.

**[Model download on first use (~200MB)]** SpeechBrain downloads `sepformer-wsj02mix` to `~/.cache/speechbrain` on first use, requiring internet access. → Surface a "Downloading separation model (200MB)…" progress message during the first separation run. Subsequent runs use the cached model.

**[Processing time: 0.5–1× real-time on CPU]** A 4-hour session takes 2–4 hours of extra processing. → Opt-in only. Warn the DM in the settings toggle. The existing async SSE stream keeps the UI responsive during processing.

**[SepFormer is a 2-speaker model]** In 5-player sessions, at most 2 speakers are separated at any moment. Three-way simultaneous speech is not improved. → Acceptable — the primary failure mode is one distant player + one nearby player overlap (2 speakers), which is exactly what SepFormer handles. Three-way overlap is rarer and already flagged as [crosstalk].

**[Memory: ~2GB peak RAM during SepFormer inference on long audio]** → Chunk long audio into 30-second windows before passing to SepFormer, concatenating separated outputs. This keeps peak RAM bounded regardless of session length.

## Migration Plan

1. Add `source_separation_enabled INTEGER NOT NULL DEFAULT 0` migration to `db/connection.py`
2. Implement `services/separation.py` with `separate_audio()` and model caching
3. Wire into `diarize()` and `diarize_with_signatures()` as stage 0 when flag is set
4. Add `separation_start` / `separation_done` / `separation_error` SSE events
5. Update campaign edit form with the toggle
6. Existing campaigns default to separation disabled — no backfill, no behaviour change

## Open Questions

- **Chunk size for long audio:** 30 seconds is a reasonable starting point for keeping RAM bounded; needs validation on actual 4-hour sessions.
- **Stream assignment after clustering:** When embeddings from stream_0 and stream_1 are pooled, do we need to track which stream each embedding came from to improve segment assembly? Initial implementation ignores this; revisit if clustering results are worse than expected.
