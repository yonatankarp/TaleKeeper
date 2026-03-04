## Context

TaleKeeper's ML pipeline currently uses four main service modules:

- **transcription.py** — faster-whisper with global model caching, supports batch (`transcribe`), streaming (`transcribe_stream`), and chunked (`transcribe_chunked`) modes. Live transcription during WebSocket recording runs every ~10 chunks via `_run_transcription_on_chunk` in `recording.py`.
- **diarization.py** — speechbrain ECAPA-TDNN encoder with compatibility shims for torchaudio 2.9+ and huggingface_hub 1.0+. Custom sliding-window embedding extraction + AgglomerativeClustering. Voice signature matching at 0.25 cosine similarity threshold.
- **image_generation.py** + **image_client.py** — Two-step pipeline: LLM crafts a scene description, then an external OpenAI-compatible image API generates the image. The image client talks to a separate server (default port 11434).
- **llm_client.py** — Generic OpenAI Chat Completions client. Used by summarization, image scene crafting, and session naming.

All services are async-first. Models are cached globally and never explicitly unloaded during normal operation. There is no memory orchestration between phases — each phase loads its model independently, and models accumulate in memory.

The recording WebSocket in `recording.py` handles both audio capture and live transcription. The `process-audio` SSE endpoint runs transcription → diarization sequentially. Summary and image generation are triggered independently by the user.

## Goals / Non-Goals

**Goals:**
- Replace faster-whisper with lightning-whisper-mlx for MLX-native transcription on Apple Silicon
- Replace speechbrain with pyannote.audio v4.0+ for GPU-accelerated diarization via MPS
- Replace external image API with in-process mflux for zero-dependency image generation
- Add memory orchestration to keep the full pipeline within 32GB unified memory
- Add a "Process All" pipeline endpoint that chains all phases with cleanup between them
- Auto-detect Ollama and send provider-specific parameters (num_ctx, keep_alive)
- Auto-invalidate existing voice signatures (incompatible embeddings)
- Make similarity threshold and batch size configurable

**Non-Goals:**
- Supporting non-Apple hardware (this refactor targets Apple Silicon specifically)
- Adding cloud-based ML services or APIs
- Changing the LLM summarization prompts or POV logic (deferred to post-transcription quality evaluation)
- Modifying the frontend beyond necessary UI changes (settings, pipeline button, progress)
- Supporting live transcription during recording (explicitly removed)
- Implementing incremental voice enrollment (separate change, already spec'd)

## Decisions

### 1. Transcription: lightning-whisper-mlx with VAD pre-pass

**Decision:** Replace faster-whisper with lightning-whisper-mlx. Run a Silero VAD pre-pass to identify speech regions, then transcribe only those regions using batched decoding.

**Why:** lightning-whisper-mlx runs natively on Apple's MLX framework, using the unified memory architecture and Apple GPU directly. faster-whisper uses CTranslate2 which falls back to CPU on Apple Silicon. The VAD pre-pass filters out non-speech audio (dice rolling, table noise, laughter) before it reaches the transcription model, reducing processing time and hallucination.

**How it works:**
1. Convert audio to WAV (16kHz mono) — reuse existing `audio_to_wav`
2. Run Silero VAD to produce speech timestamp ranges
3. Concatenate speech-only regions into a contiguous audio buffer, preserving a time-offset map
4. Transcribe the speech-only buffer with lightning-whisper-mlx using `batch_size` from settings
5. Map transcription timestamps back to original audio timestamps using the offset map
6. For chunked processing: the existing chunk strategy (5min chunks, 30s overlap, primary-zone dedup) remains, but each chunk goes through VAD → transcribe instead of direct transcription

**Batch size auto-detection:** Query `sysctl hw.perflevel0.logicalcpu` (performance core count) at startup. Map to batch size: ≤6 cores → 8, ≤10 cores → 12, >10 cores → 16. Store as a session-level default, overridable via settings.

**Model caching:** Same global caching pattern as today. `get_model()` loads once, `unload_model()` sets to None and triggers `mlx.core.metal.clear_cache()`.

**Alternative considered:** whisper.cpp via Python bindings. Rejected because it still requires manual Metal integration and doesn't leverage MLX's automatic memory management. Also considered mlx-whisper but lightning-whisper-mlx has better batched decoding support and community quantized models.

### 2. Live transcription removal

**Decision:** Remove live transcription from the WebSocket recording flow. The WebSocket will only handle audio chunk capture. All transcription happens in the post-recording `process-audio` phase.

**Why:** User confirmed this is acceptable. lightning-whisper-mlx's batched decoding is optimized for processing complete audio segments, not incremental chunks. Removing live transcription also simplifies the recording WebSocket significantly and eliminates a class of race conditions (transcription task outliving the WebSocket).

**What changes:**
- `recording.py`: Remove `_run_transcription_on_chunk`, remove transcription imports, remove `live_transcription` setting reads, remove `transcription_in_progress` tracking. The WebSocket becomes a simple chunk-to-disk writer.
- `settings` table: The `live_transcription` setting becomes unused. Leave it in the DB (no migration needed) but stop reading it.

**Alternative considered:** Keeping live transcription using a lightweight model (e.g., whisper-tiny via lightning-whisper-mlx) for real-time preview, then re-transcribing with the full model in post-processing. Rejected for complexity and memory concerns.

### 3. Diarization: pyannote.audio v4.0+ with MPS backend

**Decision:** Replace the custom speechbrain + scikit-learn pipeline with pyannote.audio's pre-built diarization pipeline, running on MPS (Apple GPU).

**Why:** pyannote.audio 4.0+ is the state-of-the-art for speaker diarization. It handles the full pipeline (VAD → segmentation → embedding → clustering) internally, eliminating our custom windowed-embedding and AgglomerativeClustering code. It produces higher quality results especially in noisy environments with overlapping speakers.

**How it works:**
1. Load pyannote `Pipeline.from_pretrained("pyannote/speaker-diarization-3.1")`
2. Move to MPS device: `pipeline.to(torch.device("mps"))`
3. Run pipeline on WAV file with `num_speakers` parameter when known from campaign settings
4. Extract speaker segments from the `Annotation` result
5. For voice signatures: use pyannote's embedding model (`pyannote/embedding`) to extract 192-dim embeddings instead of speechbrain ECAPA-TDNN

**HuggingFace token management:**
- Settings table: add `hf_token` key (sensitive — stored in DB like API keys)
- Environment variable fallback: `HF_TOKEN`
- Pass to pyannote via `use_auth_token` parameter
- Settings page: add a "HuggingFace Token" field in the Providers section with a link to the pyannote license agreement page
- Show clear error in the UI if no token is configured when diarization is attempted

**Voice signature extraction:** Replace `extract_speaker_embedding()` with pyannote's embedding model. Same workflow: extract embeddings from speaker time ranges, average, L2-normalize. The `diarize_with_signatures()` function stays conceptually the same but uses pyannote embeddings for both stored signatures and runtime comparison.

**Model caching:** Cache the pipeline and embedding model globally, similar to today. Unload with explicit `del` + `torch.mps.empty_cache()` + `gc.collect()`.

**Alternative considered:** NeMo speaker diarization. Rejected because pyannote has broader community adoption, better documentation, and native pipeline support. Also considered keeping speechbrain for embeddings + pyannote for segmentation only, but the embedding incompatibility makes this needlessly complex.

### 4. In-process image generation with mflux

**Decision:** Replace the external OpenAI-compatible image API with in-process mflux, loading the FLUX model directly in TaleKeeper's Python process.

**Why:** Eliminates the need for a separate image generation server. mflux is MLX-native and generates images in under 20 seconds with the Klein-4B model. The user specifically chose this over keeping the external API approach.

**How it works:**
1. Remove `image_client.py` entirely
2. Rewrite `image_generation.py` to import and use mflux directly
3. On image generation request:
   a. Load FLUX model (lazy, cached globally until explicitly unloaded)
   b. Generate image with configured steps (default 4) and guidance_scale (default 0)
   c. Save PNG to disk + metadata to DB (same as today)
   d. Unload model after generation if running in pipeline mode (memory orchestration)
4. Health check: instead of probing an external API, verify that mflux is importable and the model files exist on disk

**Settings changes:**
- Remove: `image_base_url`, `image_api_key` settings (no longer needed)
- Keep: `image_model` (default `FLUX.2-Klein-4B-Distilled`)
- Add: `image_steps` (default 4), `image_guidance_scale` (default 0)

**Alternative considered:** Keeping the external API as a fallback alongside mflux. Rejected per user decision — they want the simpler single-process approach. If someone later needs external API support, it can be re-added as a separate feature.

### 5. Memory orchestration via resource manager

**Decision:** Introduce a `resource_orchestration.py` service module with explicit cleanup functions called between pipeline phases. No global resource manager daemon or background task — just explicit function calls.

**Why:** All ML models share 32GB unified memory. Without cleanup, the transcription model (~2-4GB), diarization pipeline (~1-2GB), LLM (via Ollama, variable), and FLUX model (~4GB) would coexist in memory. The sequential pipeline must unload each phase's models before the next phase loads its own.

**Design:**

```
cleanup_transcription()
  → transcription.unload_model()
  → mlx.core.metal.clear_cache()
  → gc.collect()

cleanup_diarization()
  → del diarization._pipeline, diarization._embedding_model
  → torch.mps.empty_cache()
  → gc.collect()

cleanup_llm(base_url, api_key, model)
  → if _is_ollama(base_url):
      POST {ollama_base}/api/generate with keep_alive: "0"
  → gc.collect()

cleanup_image_generation()
  → image_generation.unload_model()
  → mlx.core.metal.clear_cache()
  → gc.collect()

cleanup_all()
  → runs all four cleanups
```

**When cleanup runs:**
- **Pipeline mode** ("Process All"): automatically between each phase
- **Individual triggers**: after each phase completes (via existing SSE generators and router endpoints)
- **App startup**: no change (existing orphaned chunk cleanup stays)

**Ollama detection for keep_alive:**
Detect Ollama by attempting `GET {base_url}/../api/tags` (strip `/v1` suffix, call the native Ollama endpoint). If it responds with a valid JSON containing `models`, it's Ollama. Cache the detection result per base_url. When Ollama is detected, pass `extra_body={"options": {"num_ctx": 32768}}` in chat completion requests and call the keep_alive endpoint for cleanup.

**Alternative considered:** A central ResourceManager class that tracks all loaded models and enforces memory limits. Rejected as over-engineering — explicit cleanup functions called at known transition points are simpler and sufficient. The pipeline is strictly sequential, so there's no concurrent model loading to manage.

### 6. Session pipeline endpoint

**Decision:** Add a new SSE endpoint `POST /api/sessions/{session_id}/process-all` that chains: transcription → diarization → summaries → image generation, with memory cleanup between each phase.

**Why:** Users want a one-click "process everything" flow. The existing individual endpoints remain for granular control.

**How it works:**
1. SSE stream with multi-phase events:
   - `phase: "transcription"` → runs chunked transcription (reuses existing logic)
   - `phase: "diarization"` → runs final diarization (reuses existing logic)
   - `cleanup` event between phases (not visible to user, internal tracking)
   - `phase: "summaries"` → generates full summary + POV summaries for all roster characters
   - `phase: "image_generation"` → crafts scene + generates image
   - `done` → all phases complete
2. Each phase is wrapped in try/except — failure in one phase reports the error but the pipeline stops (no partial progress past the failed phase)
3. Memory cleanup runs between each phase via `resource_orchestration` functions

**Router location:** Add to `recording.py` alongside `process-audio`, since it's an extension of that flow.

**Alternative considered:** Running phases in parallel where possible (e.g., summaries while generating image). Rejected because they compete for the same GPU/memory, and the sequential approach is needed for the memory orchestration to work.

### 7. Voice signature invalidation and configurable threshold

**Decision:** Add a DB migration that deletes all rows from `voice_signatures` on upgrade. Add a `similarity_threshold` column to `campaigns` with a default of 0.65.

**Why:** pyannote embeddings are incompatible with speechbrain embeddings. Existing signatures are unusable. The threshold is changing from hardcoded 0.25 to configurable, with a moderate default of 0.65 (higher than the old 0.25 because pyannote embeddings are more discriminative, but lower than the user's initial suggestion of 0.85 to allow for noisy audio).

**Migration approach:**
- Add migration in `db/connection.py` migration chain
- `DELETE FROM voice_signatures` — clear all rows
- `ALTER TABLE campaigns ADD COLUMN similarity_threshold REAL DEFAULT 0.65` — SQLite supports this
- No data loss beyond voice signatures (users re-enroll players)

**The `diarize_with_signatures` function:** Read `similarity_threshold` from the campaign row. Use it instead of the hardcoded `SIGNATURE_SIMILARITY_THRESHOLD` constant.

**Alternative considered:** Setting the default threshold to 0.85 as the user initially proposed. But with a configurable threshold, starting at 0.65 provides a safer default that users can tighten per-campaign. If pyannote's embeddings prove highly discriminative in testing, the default can be bumped.

### 8. Ollama-aware LLM client

**Decision:** Keep the OpenAI-compatible API as the primary interface. When Ollama is detected, inject `extra_body` parameters for `num_ctx` and handle `keep_alive` cleanup.

**Why:** The user wants to stay provider-agnostic while getting Ollama-specific optimizations. Most users will use Ollama, so the optimizations should be automatic, not require manual configuration.

**Implementation in `llm_client.py`:**
- Add `_is_ollama(base_url: str) -> bool` — cached detection via endpoint probing
- In `generate()`: when Ollama is detected, add `extra_body={"options": {"num_ctx": 32768}}` to the chat completion request. The OpenAI Python client supports `extra_body` natively.
- Add `unload_model(base_url: str, api_key: str | None, model: str)` — POST to Ollama's `/api/generate` with `keep_alive: "0"` to force model unload

**Context window for non-Ollama providers:** The `num_ctx` parameter is Ollama-specific. For other providers, context window is typically server-configured, so no action needed.

**Alternative considered:** Adding a `provider_type` dropdown in settings (Ollama, OpenAI, LM Studio, etc.) for explicit selection. Rejected — auto-detection is simpler and reduces configuration burden. If detection fails, the system falls back to generic mode with no harm.

## Risks / Trade-offs

**[Risk] lightning-whisper-mlx API instability** — It's a newer library with potentially breaking API changes between versions.
→ Pin to a specific version in pyproject.toml. Wrap all calls behind our own `transcription.py` API boundary so the rest of the codebase is insulated.

**[Risk] pyannote HuggingFace token friction** — Users must create a HuggingFace account, accept the pyannote license, and generate a token before diarization works.
→ Show clear setup instructions in the Settings page with a direct link to the license agreement. Show an actionable error if the token is missing or invalid when diarization is triggered.

**[Risk] mflux model download size** — FLUX.2-Klein-4B-Distilled is ~4GB. First-time users must download it before image generation works.
→ Add a model download progress indicator or at minimum a clear error message explaining the first-run download. Consider adding a "Download Models" button to the Settings page.

**[Risk] Memory pressure during pipeline execution** — Even with cleanup between phases, memory fragmentation or incomplete cleanup could push the process toward 32GB.
→ The cleanup functions call both framework-specific cache clearing (MLX, MPS) and Python GC. Monitor actual memory usage during benchmarking and adjust the pipeline if needed (e.g., add explicit `del` for large tensors, or add a short sleep between phases for OS memory reclamation).

**[Risk] Ollama detection false positives** — If a non-Ollama server happens to respond to `/api/tags`, the detection could misfire.
→ Check for Ollama-specific response structure (JSON with a `models` array). Cache the result so detection only runs once per base_url per process lifetime.

**[Trade-off] Losing live transcription** — Users who relied on seeing transcript during recording will lose that feature.
→ Accepted trade-off per user decision. The post-recording transcription with lightning-whisper-mlx should be fast enough that the wait is minimal.

**[Trade-off] Apple Silicon only** — This refactor makes the ML pipeline Apple Silicon specific. Users on Linux/Windows with NVIDIA GPUs will need a different path.
→ Accepted for the current user's use case. The application is local-first and the primary target is macOS. Non-Apple support can be added later as a separate configuration path.

**[Trade-off] Removing external image API support** — Users with dedicated GPU servers lose the ability to offload image generation.
→ Accepted per user decision. Can be re-added later if needed.

## Migration Plan

1. **Dependencies:** Update `pyproject.toml` — remove `faster-whisper`, `speechbrain`. Add `lightning-whisper-mlx`, `pyannote.audio`, `mflux`, `mlx`.
2. **DB migration:** Add migration step in `db/connection.py` — delete voice_signatures, add `similarity_threshold` to campaigns, add new settings keys.
3. **Service rewrites:** Replace transcription.py, diarization.py, image_generation.py. Remove image_client.py. Modify llm_client.py and summarization.py.
4. **Router changes:** Simplify recording.py (remove live transcription). Update images.py (remove external API health check). Add pipeline endpoint.
5. **Frontend:** Add settings fields, pipeline button, update image generation UI.
6. **Testing:** Update all unit and integration tests to work with new libraries. Mock MLX/pyannote/mflux in unit tests.
7. **Documentation:** Update README, Docker setup, and any deployment docs for new requirements (HuggingFace token, model downloads).

**Rollback:** If the new stack has critical issues, revert the commits. Old voice signatures are already gone (dropped in migration), but can be re-generated from existing audio using the old code if needed.

## Open Questions

1. **Silero VAD vs pyannote VAD:** pyannote.audio includes its own VAD as part of the diarization pipeline. Should we use Silero VAD for the transcription pre-pass (separate from pyannote), or try to reuse pyannote's VAD output for both transcription and diarization? Using separate VAD models is simpler but loads two models; reusing pyannote's VAD means diarization must run before transcription (changing the pipeline order).

2. **FLUX model download UX:** Should TaleKeeper download the FLUX model on first image generation attempt (lazy), or should there be an explicit "Download Models" step in the settings/setup wizard? Lazy download means the first image generation will be slow; explicit download gives users control but adds a step.

3. **Default similarity threshold:** The design proposes 0.65 as a starting default. This needs validation with real pyannote embeddings on D&D audio. The actual optimal threshold may differ significantly — this should be tuned during benchmarking.
