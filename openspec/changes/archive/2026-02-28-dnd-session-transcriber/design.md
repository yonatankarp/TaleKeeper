## Context

TaleKeeper is a greenfield offline-first application for Dungeon Masters to record, transcribe, and summarize D&D sessions. It runs entirely on the DM's local machine (targeting Apple Silicon Macs) with no cloud dependencies. The app captures audio, transcribes speech on-device, identifies speakers, and generates narrative summaries using a local LLM.

The primary user is the DM. Players receive summaries after the session via export (PDF/text) or email — they do not interact with the app directly.

## Goals / Non-Goals

**Goals:**

- All ML workloads (transcription, diarization, summarization) run locally on Apple Silicon with Metal acceleration
- Single-command startup: DM launches the app and opens a browser — no complex setup
- Real-time transcription feedback during recording so the DM can see it's working
- Clean separation between ML pipeline (Python) and UI, so each can evolve independently
- Data durability: audio files and transcripts survive app restarts, stored locally

**Non-Goals:**

- Multi-user / collaborative editing — only the DM uses the app
- Cloud deployment or hosted version
- Mobile support — desktop browser on macOS only for v1
- Real-time translation or multi-language support (English only for v1)
- Voice cloning, speech synthesis, or any generative audio features
- Player-facing accounts or login system

## Decisions

### 1. Architecture: FastAPI backend + Svelte frontend

**Decision:** Python FastAPI backend serving a Svelte SPA frontend. The backend handles all ML workloads, data persistence, and business logic. The frontend is a lightweight single-page app for the DM's UI.

**Rationale:** The DM needs real-time transcript updates, interactive speaker reassignment, and campaign/session navigation — this requires a reactive frontend. Svelte was chosen over React because it compiles to vanilla JS (smaller bundle, no runtime), has simpler syntax approachable for Python-focused developers, and the app's UI complexity doesn't warrant React's ecosystem overhead. FastAPI was chosen for its async support (critical for streaming transcription results), automatic OpenAPI docs, and Python-native ML library compatibility.

**Alternatives considered:**
- *HTMX + Jinja server rendering*: Simpler stack but too limiting for the interactive transcript editing and real-time WebSocket updates needed during live recording.
- *Gradio/Streamlit*: Fast to prototype but too constrained for custom UI interactions like speaker label drag-and-drop, timeline scrubbing, and multi-panel layouts.
- *React*: Heavier runtime, steeper learning curve, overkill for this app's scale.

### 2. Transcription engine: faster-whisper

**Decision:** Use `faster-whisper` (CTranslate2-based Whisper implementation) rather than OpenAI's original `openai-whisper`.

**Rationale:** faster-whisper is 4-6x faster than the original on the same hardware, uses significantly less memory, and supports Apple Silicon acceleration via CoreML/Metal through CTranslate2. It produces identical output quality since it uses the same model weights. The `large-v3` model provides the best accuracy and runs well on M1/M2 machines with 16GB+ RAM.

**Alternatives considered:**
- *openai-whisper*: Slower, higher memory usage, no CTranslate2 optimizations.
- *whisper.cpp*: Excellent performance but C++ library — harder to integrate with Python pipeline and pyannote-audio.
- *Browser-based Whisper (transformers.js)*: Would eliminate the backend for transcription but WASM performance is poor for large models and diarization still needs Python.

### 3. Speaker diarization: pyannote-audio 3.x

**Decision:** Use `pyannote-audio` for speaker diarization, running as a post-processing step on recorded audio segments.

**Rationale:** pyannote-audio is the most accurate open-source diarization toolkit, supports overlapping speech detection, and integrates naturally with the Python ML pipeline. It produces speaker segments with timestamps that can be aligned with Whisper's transcript output.

**Processing approach:** Diarization runs in near-real-time on buffered audio chunks (e.g., 30-second windows with overlap) during recording. Results are merged and refined when the session ends. The DM sees provisional speaker labels during recording that stabilize over time.

**Alternatives considered:**
- *Simple energy-based VAD + clustering*: Much less accurate, poor with overlapping speakers.
- *Resemblyzer/spectral clustering*: Decent but pyannote-audio 3.x outperforms significantly on DER (Diarization Error Rate).

### 4. Local LLM: Ollama

**Decision:** Use Ollama as the local LLM runtime rather than embedding llama-cpp-python directly.

**Rationale:** Ollama provides model management (download, update, delete models via CLI), a simple REST API, Metal acceleration out of the box on macOS, and runs as an independent process. This decouples model lifecycle management from the app — the DM can choose and swap models without app changes. It also avoids bundling large model weights with the application.

The app will recommend specific models for summarization (e.g., `llama3.1:8b` or `mistral:7b`) but allow the DM to configure any Ollama-compatible model.

**Alternatives considered:**
- *llama-cpp-python*: More tightly integrated but requires managing model downloads, GPU allocation, and process lifecycle within the app. Less flexibility for model swapping.
- *Local API-compatible servers (LM Studio, LocalAI)*: Similar approach to Ollama but less widespread adoption and CLI tooling.

### 5. Data storage: SQLite + filesystem

**Decision:** SQLite for structured data (campaigns, sessions, transcripts, summaries, speaker mappings). Local filesystem for audio files (organized by campaign/session).

**Rationale:** SQLite is zero-configuration, file-based (easy backup — just copy the directory), handles concurrent reads well, and has excellent Python support. Audio files are large binary blobs that don't belong in a database — storing them as files allows easy access, playback, and re-processing.

**Schema overview:**

```
campaigns
  ├── id, name, description, created_at
  └── has many → sessions

sessions
  ├── id, campaign_id, name, date, status (recording|completed), audio_path
  └── has many → transcript_segments, summaries

transcript_segments
  ├── id, session_id, speaker_id, text, start_time, end_time
  └── belongs to → speakers

speakers
  ├── id, session_id, diarization_label, player_name, character_name
  └── (DM assigns player_name and character_name after diarization)

summaries
  ├── id, session_id, type (full|pov), speaker_id (null for full), content, model_used
  └── (generated after session ends)
```

**Audio file layout:**

```
data/
  audio/
    <campaign-id>/
      <session-id>.webm
```

### 6. Real-time communication: WebSockets

**Decision:** Use WebSockets (via FastAPI's built-in support) for streaming transcription results from backend to frontend during live recording.

**Rationale:** The DM needs to see transcript text appearing in near-real-time as the session is recorded. HTTP polling would add latency and unnecessary overhead. WebSockets provide bidirectional, low-latency streaming that's well-suited for this use case. FastAPI supports WebSockets natively.

**Message flow during recording:**
1. Frontend captures audio via MediaRecorder API → sends chunks to backend via WebSocket
2. Backend feeds chunks to faster-whisper → streams transcript segments back
3. Backend periodically runs diarization on buffered audio → sends speaker updates
4. Frontend renders transcript with provisional speaker labels in real-time

### 7. Audio capture: MediaRecorder API with WebM/Opus

**Decision:** Use the browser's MediaRecorder API to capture audio, encoding as WebM with Opus codec.

**Rationale:** MediaRecorder is universally supported in modern browsers, requires no plugins, and Opus provides excellent compression at speech-quality bitrates (32-64 kbps). This keeps audio files small while maintaining transcription quality. The backend converts to WAV as needed for ML processing using `ffmpeg` or `pydub`.

### 8. PDF generation: WeasyPrint

**Decision:** Use WeasyPrint for generating PDF exports of session summaries.

**Rationale:** WeasyPrint renders HTML/CSS to PDF, allowing summary templates to be styled with CSS (consistent with the web UI's look). It's pure Python, easy to install, and produces clean, printable output. The DM can export a full session summary or individual POV summaries as PDFs.

**Alternatives considered:**
- *ReportLab*: Lower-level API, more control but more verbose for document generation.
- *fpdf2*: Lightweight but limited styling capabilities.
- *Pandoc*: External dependency, overkill for this use case.

### 9. Application packaging and startup

**Decision:** Distribute as a Python package installable via `pip` (or `pipx`). A single CLI command (`talekeeper serve`) starts the FastAPI server and opens the browser.

**Rationale:** Python developers on macOS already have Python available. `pipx` provides isolated installs. This avoids the complexity of Electron/Tauri packaging while keeping the "single command to start" goal. Ollama is a separate install (one-time setup) with its own CLI.

**Startup flow:**
1. DM runs `talekeeper serve`
2. Backend starts FastAPI on `localhost:8000`
3. Browser opens automatically to `http://localhost:8000`
4. App checks Ollama connectivity and model availability on first run

### 10. Frontend build and serving

**Decision:** Svelte frontend is built at package build time. The compiled static assets are bundled with the Python package and served by FastAPI's `StaticFiles` mount.

**Rationale:** No separate frontend dev server needed in production. The DM installs one package and everything works. During development, Vite's dev server proxies API calls to FastAPI for hot-reload.

## Risks / Trade-offs

**[Memory pressure from concurrent ML models]** → Running Whisper + pyannote-audio during recording, then an LLM for summarization, could exceed available RAM on 8GB machines. **Mitigation:** Use smaller Whisper models (`medium` or `small`) as configurable options. Never run Whisper and LLM simultaneously — summarization only starts after recording ends and transcription completes. Document minimum recommended specs (16GB RAM).

**[Diarization accuracy with many speakers]** → pyannote-audio accuracy degrades with 6+ overlapping speakers, which is common in a D&D session (4-6 players + DM). **Mitigation:** Manual correction UI is a first-class feature, not an afterthought. The DM can quickly reassign mislabeled segments. Over time, speaker profiles from previous sessions in the same campaign can improve accuracy.

**[Ollama as external dependency]** → Requiring Ollama to be installed separately adds friction to setup. **Mitigation:** Clear first-run setup wizard in the app that checks for Ollama, guides installation, and recommends a model. The app functions for recording/transcription without Ollama — summarization is just unavailable until configured.

**[WebM-to-WAV conversion overhead]** → ML models need WAV input but we record WebM. **Mitigation:** Use `ffmpeg` (commonly available on macOS via Homebrew, or bundled) for fast conversion. Convert chunks incrementally during recording rather than the full file at the end.

**[Browser microphone quality]** → Browser audio capture may have lower quality than native recording. **Mitigation:** Request high-quality audio settings via MediaRecorder constraints (`sampleRate: 44100`, `channelCount: 1` for mono speech). Whisper is robust to moderate audio quality issues. The DM can also use an external USB microphone for better pickup in a room setting.

**[Long session transcript size]** → A 4-hour session could produce 50,000+ words of transcript, which may exceed LLM context windows for summarization. **Mitigation:** Chunk the transcript into segments (e.g., 30-minute blocks), summarize each chunk, then produce a meta-summary. Use models with larger context windows (32k+ tokens) when available.

## Open Questions

- **Speaker profile persistence across sessions:** Should the app learn speaker voices across sessions within a campaign to improve diarization accuracy automatically? This would require storing voice embeddings and adds complexity. Deferring to v2.
- **Recommended LLM model:** Need to benchmark summary quality vs. speed for `llama3.1:8b`, `mistral:7b`, and `gemma2:9b` on Apple Silicon to make a default recommendation.
- **Session pause/resume:** Should the DM be able to pause and resume recording within a single session (e.g., for breaks)? This affects audio chunking and transcript continuity. Likely needed but adds state management complexity.
