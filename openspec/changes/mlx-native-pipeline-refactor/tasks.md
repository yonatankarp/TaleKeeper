## 1. Dependencies

- [x] 1.1 Update `pyproject.toml`: remove `faster-whisper` and `speechbrain` dependencies
- [x] 1.2 Update `pyproject.toml`: add `lightning-whisper-mlx` (pinned version), `pyannote.audio>=4.0`, `mflux`, `mlx`
- [x] 1.3 Add `silero-vad` (or `torch` with Silero hub model) as a dependency for VAD pre-pass
- [x] 1.4 Reinstall venv and verify all new dependencies resolve without conflicts

## 2. Database Migrations

- [x] 2.1 Add migration in `db/connection.py`: `DELETE FROM voice_signatures` to invalidate all existing signatures
- [x] 2.2 Add migration in `db/connection.py`: `ALTER TABLE campaigns ADD COLUMN similarity_threshold REAL DEFAULT 0.65`
- [x] 2.3 Add migration in `db/connection.py`: insert default settings rows for `hf_token`, `whisper_batch_size`, `image_steps`, `image_guidance_scale`
- [x] 2.4 Verify migrations run cleanly on a fresh DB and on an existing DB with data

## 3. LLM Client — Ollama Detection

- [x] 3.1 Add `_is_ollama(base_url: str) -> bool` function to `services/llm_client.py` with cached endpoint probing (strip `/v1`, probe `/api/tags`)
- [x] 3.2 Modify `generate()` in `services/llm_client.py` to inject `extra_body={"options": {"num_ctx": 32768}}` when Ollama is detected
- [x] 3.3 Add `unload_model(base_url, api_key, model)` function to `services/llm_client.py` that POSTs `keep_alive: "0"` to Ollama's `/api/generate`
- [x] 3.4 Write unit tests for `_is_ollama` detection (mock HTTP responses for Ollama and non-Ollama endpoints)
- [x] 3.5 Write unit tests for `generate()` verifying `extra_body` is injected only for Ollama

## 4. Transcription Service Rewrite

- [x] 4.1 Rewrite `services/transcription.py`: replace faster-whisper imports with lightning-whisper-mlx, implement `get_model()` with MLX model loading and global caching
- [x] 4.2 Implement `unload_model()` in `services/transcription.py` that sets globals to None and calls `mlx.core.metal.clear_cache()`
- [x] 4.3 Implement `_run_vad(wav_path)` in `services/transcription.py`: run Silero VAD, return list of speech timestamp ranges
- [x] 4.4 Implement `_build_speech_buffer(wav_path, vad_ranges)`: concatenate speech-only regions, return audio buffer + offset map
- [x] 4.5 Rewrite `transcribe()` in `services/transcription.py`: VAD pre-pass → speech buffer → lightning-whisper-mlx batched decoding → timestamp remapping
- [x] 4.6 Rewrite `transcribe_chunked()` to use new `transcribe()` (VAD + batched decoding per chunk), keeping the existing chunk strategy and primary-zone dedup
- [x] 4.7 Remove `transcribe_stream()` function (no longer needed without live transcription)
- [x] 4.8 Implement batch size auto-detection: query `sysctl hw.perflevel0.logicalcpu`, map core count to batch size, read override from settings
- [x] 4.9 Update `SUPPORTED_LANGUAGES` set if lightning-whisper-mlx supports a different language list
- [x] 4.10 Write unit tests for VAD pre-pass (mock Silero, verify speech regions extracted)
- [x] 4.11 Write unit tests for `transcribe()` (mock lightning-whisper-mlx, verify VAD → transcribe → timestamp remapping)
- [x] 4.12 Write unit tests for batch size auto-detection logic

## 5. Diarization Service Rewrite

- [ ] 5.1 Rewrite `services/diarization.py`: remove all speechbrain imports, compatibility shims, and ECAPA-TDNN encoder code
- [ ] 5.2 Implement pyannote pipeline loading with HF token resolution (settings table → `HF_TOKEN` env var) and MPS device targeting
- [ ] 5.3 Implement `diarize()` using pyannote pipeline: load WAV, run pipeline with optional `num_speakers`, extract `SpeakerSegment` list from `Annotation` result
- [ ] 5.4 Implement `extract_speaker_embedding()` using pyannote's embedding model (`pyannote/embedding`): extract 192-dim embeddings from time ranges, average, L2-normalize
- [ ] 5.5 Rewrite `diarize_with_signatures()` to use pyannote embeddings for cosine similarity matching, reading `similarity_threshold` from campaign settings
- [ ] 5.6 Update `run_final_diarization()` to use new pyannote-based `diarize()` and `diarize_with_signatures()`, passing campaign `similarity_threshold`
- [ ] 5.7 Update `generate_voice_signatures()` to use new `extract_speaker_embedding()` with pyannote model
- [ ] 5.8 Keep `align_speakers_with_transcript()` and `_merge_segments()` unchanged (they are engine-agnostic)
- [ ] 5.9 Add `unload_models()` function to `services/diarization.py` that deletes cached pipeline + embedding model and calls `torch.mps.empty_cache()`
- [ ] 5.10 Write unit tests for pyannote diarization (mock pyannote Pipeline, verify segment extraction)
- [ ] 5.11 Write unit tests for signature matching with configurable threshold
- [ ] 5.12 Write unit tests for HF token resolution (settings → env var → missing error)

## 6. Image Generation Service Rewrite

- [ ] 6.1 Delete `services/image_client.py`
- [ ] 6.2 Rewrite `services/image_generation.py`: replace `image_client` imports with direct `mflux` usage
- [ ] 6.3 Implement `_get_model()` with lazy loading and global caching for the FLUX model
- [ ] 6.4 Implement `unload_model()` that deletes cached model and calls `mlx.core.metal.clear_cache()`
- [ ] 6.5 Implement `_resolve_image_config()` to read `image_model`, `image_steps`, `image_guidance_scale` from settings/env/defaults
- [ ] 6.6 Rewrite `generate_session_image()` to call mflux directly with configured steps and guidance_scale, save PNG to disk + DB
- [ ] 6.7 Implement `health_check()` that verifies mflux is importable and reports model availability
- [ ] 6.8 Keep `craft_scene_description()` unchanged (it uses llm_client, not the image engine)
- [ ] 6.9 Write unit tests for mflux image generation (mock mflux, verify config resolution and PNG save)
- [ ] 6.10 Write unit tests for health check (mock import check, model file existence)

## 7. Resource Orchestration

- [ ] 7.1 Create `services/resource_orchestration.py` with `cleanup_transcription()`, `cleanup_diarization()`, `cleanup_llm()`, `cleanup_image_generation()`, and `cleanup_all()`
- [ ] 7.2 Wire `cleanup_transcription()` to call `transcription.unload_model()` + `mlx.core.metal.clear_cache()` + `gc.collect()`
- [ ] 7.3 Wire `cleanup_diarization()` to call `diarization.unload_models()` + `gc.collect()`
- [ ] 7.4 Wire `cleanup_llm()` to call `llm_client.unload_model()` (Ollama-aware) + `gc.collect()`
- [ ] 7.5 Wire `cleanup_image_generation()` to call `image_generation.unload_model()` + `mlx.core.metal.clear_cache()` + `gc.collect()`
- [ ] 7.6 Write unit tests for each cleanup function (verify correct calls are made, mocks for model unloading)

## 8. Router Changes

- [ ] 8.1 Simplify `routers/recording.py`: remove `_run_transcription_on_chunk()` function entirely
- [ ] 8.2 Simplify `routers/recording.py` WebSocket handler: remove transcription imports, `live_transcription` setting read, `transcription_in_progress` tracking, and `asyncio.create_task(_do_transcribe)` call
- [ ] 8.3 Update `process_audio` SSE endpoint in `routers/recording.py`: add `cleanup_transcription()` call after transcription completes and `cleanup_diarization()` after diarization completes
- [ ] 8.4 Add `POST /api/sessions/{session_id}/process-all` SSE endpoint in `routers/recording.py`: chain transcription → cleanup → diarization → cleanup → summaries → cleanup_llm → image generation → cleanup, with multi-phase SSE events
- [ ] 8.5 Update `routers/images.py`: replace `image_client` health check with `image_generation.health_check()`, remove `image_client` imports
- [ ] 8.6 Update `routers/images.py` `generate_image` endpoint: remove pre-flight image client health check, use in-process mflux health check, add `cleanup_image_generation()` after generation
- [ ] 8.7 Write integration tests for the `process-all` pipeline endpoint (mock services, verify SSE event sequence and phase transitions)
- [ ] 8.8 Write integration tests verifying the simplified WebSocket recording (no transcription during recording)

## 9. Frontend — Settings

- [ ] 9.1 Add "HuggingFace Token" field to Settings page Providers section (password input, with link to pyannote license page)
- [ ] 9.2 Add "Transcription Batch Size" field to Settings page with auto-detected default label
- [ ] 9.3 Update Whisper model selection in Settings: change default label to `whisper-large-v3-turbo`, add model recommendations with performance notes
- [ ] 9.4 Update image generation settings: remove Base URL and API Key fields, add Steps and Guidance Scale fields, update model default to `FLUX.2-Klein-4B-Distilled` with recommendations
- [ ] 9.5 Add LLM model recommendations with performance annotations to the LLM Provider settings section
- [ ] 9.6 Wire new settings fields to `api.put('/api/settings', ...)` calls

## 10. Frontend — Campaign Settings

- [ ] 10.1 Add "Voice Signature Confidence" slider/input to campaign settings with the campaign's `similarity_threshold` value
- [ ] 10.2 Wire the threshold setting to `api.put('/api/campaigns/{id}', ...)` call

## 11. Frontend — Session Pipeline

- [ ] 11.1 Add "Process All" button to the session page (visible when session has audio and is in `audio_ready` or `completed` status)
- [ ] 11.2 Implement multi-phase SSE consumption for the `process-all` endpoint: display current phase name and progress within each phase
- [ ] 11.3 Disable all individual action buttons while the pipeline is running
- [ ] 11.4 Show pipeline completion summary (segments count, summaries generated, image generated)
- [ ] 11.5 Write frontend tests for the Process All button visibility and progress display

## 12. Integration Testing

- [ ] 12.1 Update existing transcription integration tests to use lightning-whisper-mlx (or mock it consistently)
- [ ] 12.2 Update existing diarization integration tests for pyannote pipeline
- [ ] 12.3 Update existing image generation integration tests for mflux
- [ ] 12.4 Update existing voice signature integration tests for pyannote embeddings and configurable threshold
- [ ] 12.5 Add integration test for DB migration: verify voice_signatures are cleared and similarity_threshold column exists
- [ ] 12.6 Add integration test for full pipeline endpoint: process-all with mocked services, verify end-to-end SSE event flow
