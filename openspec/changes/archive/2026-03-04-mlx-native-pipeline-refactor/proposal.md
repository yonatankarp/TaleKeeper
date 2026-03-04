## Why

The current ML pipeline (faster-whisper + speechbrain) takes ~45 minutes to process a 2-hour D&D session on Apple Silicon and produces inaccurate diarization in noisy tabletop environments. These libraries use generic CPU/CUDA paths that underutilize Apple's unified memory architecture. Players currently get their session recap the next day instead of while still at the table. Replacing the stack with MLX-native and MPS-accelerated libraries unlocks the full potential of Apple Silicon, dramatically reducing processing time and improving accuracy.

## What Changes

### Transcription engine replacement
- **BREAKING**: Replace `faster-whisper` with `lightning-whisper-mlx` for MLX-native transcription
- **BREAKING**: Remove live transcription during WebSocket recording — transcription now happens only in the post-recording processing phase
- Add a dedicated Voice Activity Detection (VAD) pre-pass to filter non-speech audio (dice rolls, table noise, background chatter) before transcription
- Implement batched decoding with hardware-aware batch size (auto-detected from Apple Silicon variant, configurable override)
- Default model: `mlx-community/whisper-large-v3-turbo` (4-bit quantized). Models remain configurable with recommended defaults shown in UI

### Diarization engine replacement
- **BREAKING**: Replace `speechbrain` (ECAPA-TDNN) with `pyannote.audio` v4.0+ for speaker diarization
- Target Apple GPU explicitly via `pipeline.to(torch.device("mps"))`
- Requires HuggingFace access token (gated model) — configurable via Settings page with `HF_TOKEN` env var fallback

### Voice signature migration
- **BREAKING**: Auto-invalidate all existing voice signatures on upgrade (speechbrain embeddings are incompatible with pyannote embeddings). Users must re-enroll players
- Extract 192-dim speaker embeddings using pyannote's embedding model
- Make cosine similarity threshold configurable per campaign (replacing the current hardcoded 0.25)

### In-process image generation
- **BREAKING**: Replace external OpenAI-compatible image API with in-process `mflux` library using FLUX.2-Klein-4B-Distilled model
- Remove `image_client.py` and external image server dependency
- Default settings: `steps=4`, `guidance_scale=0` for fast generation. Configurable with recommended defaults in UI

### Memory orchestration
- Implement resource cleanup between ML phases: `mlx.core.metal.clear_cache()` + `gc.collect()` after each phase completes
- When Ollama is detected as the LLM provider, send `keep_alive: 0` after summary generation to free RAM before image generation
- Ensure the full pipeline (transcription → diarization → summaries → image) stays within 32GB unified memory without triggering system swap

### Session processing pipeline
- Add a "Process All" button that runs the full pipeline sequentially: Transcription → Diarization → Summaries → Session Art, with memory cleanup between each phase
- Keep existing individual phase triggers (process audio, generate summary, generate image) for manual control
- SSE progress reporting across the full pipeline

### Ollama-aware LLM configuration
- Stay provider-agnostic (OpenAI-compatible API as the interface)
- Auto-detect Ollama endpoints and send provider-specific parameters (`num_ctx: 32768` for full transcript context, `keep_alive: 0` for memory management)
- Update Docker setup and documentation for recommended Ollama configuration

## Capabilities

### New Capabilities
- `resource-orchestration`: Memory management and cleanup between ML pipeline phases, including MLX cache clearing, garbage collection, and Ollama keep_alive control
- `session-pipeline`: "Process All" button that runs the full session processing pipeline (transcription → diarization → summaries → image) sequentially with progress tracking and memory cleanup between phases

### Modified Capabilities
- `transcription`: Engine changes from faster-whisper to lightning-whisper-mlx; removal of live/streaming transcription during recording; addition of VAD pre-pass; batched decoding with hardware-aware batch size
- `speaker-diarization`: Engine changes from speechbrain to pyannote.audio with MPS backend; pyannote pipeline replaces custom windowed-embedding + clustering approach
- `voice-signatures`: Embedding model changes to pyannote (incompatible with existing signatures); auto-invalidation on upgrade; configurable similarity threshold per campaign
- `summary-generation`: Ollama-aware context window override (num_ctx: 32768); keep_alive memory management
- `llm-provider`: Ollama endpoint auto-detection; provider-specific parameter passthrough
- `image-generation`: Replace external API with in-process mflux library; remove image_client.py; FLUX model loaded directly in TaleKeeper process
- `audio-capture`: Remove live transcription from WebSocket recording flow; WebSocket now handles audio capture only
- `streaming-retranscription`: Adapt to new lightning-whisper-mlx engine for re-transcription of existing sessions
- `chunked-audio-processing`: Adapt chunked processing to lightning-whisper-mlx batched decoding

## Impact

### Dependencies
- **Remove**: `faster-whisper`, `speechbrain`
- **Add**: `lightning-whisper-mlx`, `pyannote.audio`, `mflux`, `mlx`
- **Keep**: `openai` (for LLM client), `scikit-learn`, `scipy`, `pydub`
- **New system requirement**: HuggingFace account + access token (for pyannote gated models)

### Database
- Migration to drop all rows from `voice_signatures` table on upgrade (auto-invalidation)
- Add `similarity_threshold` column to `campaigns` table (or settings)
- Add `hf_token` to settings table
- Add `whisper_batch_size` to settings table

### Backend
- Rewrite: `services/transcription.py`, `services/diarization.py`, `services/image_generation.py`
- Remove: `services/image_client.py`
- Modify: `services/summarization.py`, `services/llm_client.py`, `app.py`
- New: `services/resource_orchestration.py` (or integrated into existing pipeline)
- Modify: `routers/recording.py` (remove live transcription), `routers/images.py` (remove external API health check)

### Frontend
- Add "Process All" button to session page
- Add pipeline progress UI (multi-phase SSE tracking)
- Add HuggingFace token field to Settings page
- Add similarity threshold setting to campaign settings
- Add batch size setting to advanced settings
- Update image generation UI (remove external server configuration)
- Show recommended models with performance notes in model selection dropdowns

### Performance
- Target: benchmark full pipeline on 2-hour audio, then optimize bottlenecks
- Memory budget: 32GB unified memory, no swap
