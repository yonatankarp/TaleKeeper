## Context

The diarization service (`src/talekeeper/services/diarization.py`) currently uses pyannote.audio 3.3 with the `speaker-diarization-3.1` pipeline model. It loads two global cached models: a diarization pipeline and an embedding model, both targeted to MPS (Apple GPU). The service exposes 7 public functions consumed by 4 routers (recording, transcripts, speakers, voice_signatures). Voice signatures are stored as 192-dim JSON arrays in the `voice_signatures` table. The `resource_orchestration.py` service handles model unloading between pipeline phases.

The MPS backend is broken for pyannote (wrong timestamps, wontfix), and CPU processing takes 2-3 hours for 2-hour audio. The `diarize` library offers a 7x faster CPU-only alternative with a compatible API surface.

## Goals / Non-Goals

**Goals:**
- Replace pyannote with `diarize` library for all diarization and embedding extraction
- Maintain identical public API surface in `diarization.py` (zero router changes)
- Provide per-stage SSE progress reporting with X/Y counters for embedding extraction
- Update voice signature infrastructure to 256-dim WeSpeaker embeddings
- Remove broken MPS code path

**Non-Goals:**
- Real-time/streaming diarization during recording (diarize lib doesn't support it; existing chunk diarization is separate and out of scope)
- Migrating existing 192-dim voice signatures to 256-dim (users regenerate)
- Removing the HF token setting from the UI (kept for future flexibility)
- Frontend changes (SSE event types unchanged, only detail messages differ)

## Decisions

### 1. Call pipeline stages individually instead of using `diarize()` top-level function

Call `run_vad()` → custom embedding loop → `cluster_speakers()` → manual segment assembly instead of the single `diarize()` call.

**Why:** The top-level `diarize()` function has no progress hooks. Calling stages individually lets us emit SSE progress between stages. The embedding extraction loop is reimplemented to add per-segment X/Y progress, matching the UX of pyannote's hook system.

**Alternative considered:** Call `diarize()` as a black box and report only 4 discrete checkpoints. Rejected because embedding extraction is the slowest stage and X/Y progress is important UX for 15+ minute processing.

### 2. Reimplement embedding extraction loop with progress callback

Instead of calling `extract_embeddings()` from the diarize library, reimplement the windowing + WeSpeaker inference loop with a progress callback parameter.

**Why:** The library's `extract_embeddings()` processes all segments in one call with no callback. For 740+ segments, reporting "Extracting embeddings (350/740)..." is critical UX. The loop is straightforward: iterate speech segments, window long segments into 1.2s chunks with 0.6s step, call `wespeakerruntime.Speaker` per chunk.

**Alternative considered:** Monkey-patch the library's loop. Rejected as fragile and version-dependent. The windowing logic is simple enough to own.

### 3. Keep `SpeakerSegment` dataclass unchanged

The existing `SpeakerSegment(speaker_label, start_time, end_time)` dataclass is the contract between diarization and all consumers. Map `diarize` output segments to this format.

**Why:** Zero changes needed in routers, alignment logic, or DB update code.

**Alternative considered:** Adopt `diarize`'s `Segment` Pydantic model directly. Rejected because it would require changes in every consumer and the dataclass is simpler.

### 4. Voice signature matching: two-pass approach

For `diarize_with_signatures()`:
1. Run full diarize pipeline (VAD → embeddings → clustering) to get speaker labels
2. Group embeddings by assigned speaker label using time overlap between subsegments and diarization output segments
3. Compute L2-normalized centroid per speaker
4. Match centroids against stored roster signatures via cosine similarity

**Why:** The diarize library doesn't have built-in signature matching. This two-pass approach reuses the library's clustering (which is good at separating speakers) and adds our own identity matching on top. It's the same pattern as the current pyannote implementation.

**Alternative considered:** Skip clustering entirely and match every embedding window against signatures directly (one-pass). Rejected because it would be slower (N windows x M signatures comparisons) and lose the benefit of spectral clustering's speaker separation.

### 5. Default similarity threshold of 0.75

WeSpeaker ResNet34-LM 256-dim embeddings have a different cosine similarity distribution than pyannote's 192-dim ECAPA-TDNN embeddings. Community testing with the diarize library found 0.75 works well for cross-session speaker matching.

**Why:** The current default (0.65) was tuned for pyannote embeddings. Using it with WeSpeaker would produce too many false matches.

**Alternative considered:** Keep 0.65 and let users tune. Rejected because it would give poor out-of-box experience. The setting remains configurable via the campaign `similarity_threshold` column.

### 6. Stateless service — no global model caching

The diarize library initializes models internally on each call. Remove the global `_pipeline` and `_embedding_model` caches. The `unload_models()` function becomes a no-op (just `gc.collect()`).

**Why:** The diarize library manages its own model lifecycle. Silero VAD and WeSpeaker ONNX models are small (~32MB total) and load fast. No benefit to caching them ourselves.

**Alternative considered:** Cache the `wespeakerruntime.Speaker` instance globally like we cached pyannote models. Rejected as premature optimization — the ONNX model loads in <1s.

### 7. Pin diarize library version

Pin to `diarize>=0.1.0,<0.2.0` in pyproject.toml since we depend on internal APIs (`run_vad`, `cluster_speakers`, `wespeakerruntime.Speaker`).

**Why:** The library is v0.1.0 and API stability is not guaranteed. Pinning to the minor version protects against breaking changes while allowing patch fixes.

**Alternative considered:** Pin exact version (`==0.1.0`). Rejected as too restrictive for bug fixes.

## Risks / Trade-offs

**[No overlap detection]** The diarize library assigns each moment to exactly one speaker. In D&D sessions with cross-talk, overlapping speech is attributed to one speaker. → Acceptable for turn-taking D&D. Pyannote's overlap detection wasn't meaningfully helping given the MPS bugs.

**[New library, v0.1.0]** The diarize library is new (March 2026) with limited battle-testing. → Mitigated by the spike approach: test with real 2h session before committing. The library's dependencies (Silero VAD, WeSpeaker, scikit-learn) are mature.

**[Speaker count estimation above 7]** The diarize library's GMM+BIC speaker count estimation drops to 0% accuracy for 8+ speakers. → Mitigated by always passing `num_speakers` (the user confirmed they always know party size). The parameter is a direct clustering input in diarize (not a post-hoc constraint like in pyannote).

**[Reimplemented embedding loop]** We own the windowing + WeSpeaker inference code instead of using the library's `extract_embeddings()`. This could drift from the library's implementation. → Mitigated by version pinning and the loop being simple (~30 lines).

**[Voice signature regeneration required]** Existing 192-dim signatures are incompatible with 256-dim WeSpeaker embeddings. → Acceptable: user confirmed no existing signatures need preserving. The regeneration flow is unchanged.

## Migration Plan

1. Swap dependencies in `pyproject.toml` (remove pyannote.audio, add diarize)
2. Rewrite `diarization.py` internals (same public API)
3. Simplify `resource_orchestration.py` cleanup
4. Update default similarity_threshold in DB schema for new campaigns
5. Update unit tests (new mocks)
6. Manual validation with real 2h D&D session recording

**Rollback:** Revert the dependency swap and restore the old `diarization.py`. No DB schema changes are destructive (similarity_threshold default only affects new campaigns).

## Open Questions

- What is the optimal `min_silence_duration_ms` for Silero VAD in D&D sessions? The default (50ms) may be too aggressive for rapid turn-taking. May need tuning after real-world testing.
- Should we expose VAD parameters (threshold, min_speech_duration, min_silence_duration) as advanced settings, or hardcode sensible defaults? Start with defaults, add settings if users request them.
