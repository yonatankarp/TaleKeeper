## 1. Project Scaffolding

- [x] 1.1 Initialize Python package structure with `pyproject.toml`, `src/talekeeper/` layout, and entry point for `talekeeper serve` CLI command
- [x] 1.2 Set up FastAPI application skeleton with health check endpoint, CORS config, and static file serving mount point
- [x] 1.3 Scaffold Svelte frontend with Vite, TypeScript, and SvelteKit-style file routing; configure Vite proxy to FastAPI for development
- [x] 1.4 Add Python dependencies: `fastapi`, `uvicorn`, `faster-whisper`, `pyannote-audio`, `weasyprint`, `aiosqlite`, `pydub`, `httpx` (for Ollama), `python-multipart`
- [x] 1.5 Add frontend dependencies: `svelte`, `svelte-routing` (or equivalent), TypeScript types
- [x] 1.6 Create `talekeeper serve` CLI command that starts uvicorn, creates data directories (`data/audio/`, `data/db/`), and opens the browser

## 2. Database Layer

- [x] 2.1 Create SQLite database initialization module with async connection management via `aiosqlite`
- [x] 2.2 Define and apply schema migrations for `campaigns` table (id, name, description, created_at, updated_at)
- [x] 2.3 Define and apply schema migrations for `sessions` table (id, campaign_id FK, name, date, status, audio_path, created_at, updated_at)
- [x] 2.4 Define and apply schema migrations for `speakers` table (id, session_id FK, diarization_label, player_name, character_name)
- [x] 2.5 Define and apply schema migrations for `transcript_segments` table (id, session_id FK, speaker_id FK, text, start_time, end_time)
- [x] 2.6 Define and apply schema migrations for `summaries` table (id, session_id FK, type, speaker_id FK nullable, content, model_used, generated_at)
- [x] 2.7 Define and apply schema migrations for `roster_entries` table (id, campaign_id FK, player_name, character_name, is_active, created_at)
- [x] 2.8 Define and apply schema migrations for `settings` table (key, value) for app-wide configuration (whisper model, ollama model, SMTP settings)

## 3. Campaign Management Backend

- [x] 3.1 Implement campaign CRUD API endpoints: POST/GET/PUT/DELETE `/api/campaigns` and `/api/campaigns/{id}`
- [x] 3.2 Implement session CRUD API endpoints: POST/GET/PUT/DELETE `/api/campaigns/{id}/sessions` and `/api/sessions/{id}`
- [x] 3.3 Implement roster CRUD API endpoints: POST/GET/PUT/DELETE `/api/campaigns/{id}/roster` and `/api/roster/{id}`
- [x] 3.4 Implement campaign dashboard endpoint: GET `/api/campaigns/{id}/dashboard` returning session count, total recorded time, most recent session date
- [x] 3.5 Implement cascade deletion logic: deleting a campaign removes all sessions, transcripts, summaries, speakers, roster entries, and audio files
- [x] 3.6 Implement session status tracking with automatic transitions (draft → recording → transcribing → completed)

## 4. Frontend Shell and Campaign UI

- [x] 4.1 Build app shell layout with navigation sidebar (campaigns list) and main content area
- [x] 4.2 Build campaign list page showing all campaigns with create/edit/delete actions
- [x] 4.3 Build campaign dashboard page showing session count, total time, recent session, and action buttons (New Session, Continue Last)
- [x] 4.4 Build session list component within campaign view, showing sessions ordered by date with name, date, and status badge
- [x] 4.5 Build campaign roster management page with add/edit/deactivate player-character entries
- [x] 4.6 Build session detail page skeleton with tabs/sections for: Recording, Transcript, Summaries, Export

## 5. Audio Capture Frontend

- [x] 5.1 Implement microphone permission request and error handling (denied, no device) with user-facing error messages
- [x] 5.2 Implement MediaRecorder integration: configure WebM/Opus encoding, mono channel, 44100 Hz sample rate with fallback
- [x] 5.3 Build recording control UI: Start, Pause, Resume, Stop buttons with recording indicator and elapsed time display
- [x] 5.4 Implement WebSocket connection from frontend to backend for streaming audio chunks during recording
- [x] 5.5 Implement single-recording enforcement: disable recording controls in other sessions when one is active

## 6. Audio Capture Backend

- [x] 6.1 Implement WebSocket endpoint `/ws/recording/{session_id}` that receives audio chunks from the frontend
- [x] 6.2 Implement audio chunk accumulation and assembly into a complete WebM file on the backend
- [x] 6.3 Implement audio file persistence: save completed recordings to `data/audio/<campaign-id>/<session-id>.webm` and update session record
- [x] 6.4 Implement WebM-to-WAV conversion utility using `pydub`/`ffmpeg` for feeding audio to ML models
- [x] 6.5 Implement audio playback API endpoint: GET `/api/sessions/{id}/audio` serving the stored audio file with range request support

## 7. Audio Playback Frontend

- [x] 7.1 Build audio player component with standard controls (play, pause, seek, volume) for completed sessions
- [x] 7.2 Implement click-to-seek from transcript segments: clicking a segment seeks the audio player to that segment's start time

## 8. Transcription Backend

- [x] 8.1 Implement faster-whisper model manager: download, load, and cache the selected Whisper model with configurable model size
- [x] 8.2 Implement transcription service: accept WAV audio input and return timestamped transcript segments with text, start_time, end_time
- [x] 8.3 Implement real-time transcription pipeline: process audio chunks as they arrive during recording, producing partial transcript segments
- [x] 8.4 Implement transcript segment persistence: save segments to database associated with session
- [x] 8.5 Implement transcript retrieval API: GET `/api/sessions/{id}/transcript` returning all segments ordered by start_time
- [x] 8.6 Implement re-transcription endpoint: POST `/api/sessions/{id}/retranscribe` that re-processes stored audio with a specified model and replaces existing segments
- [x] 8.7 Enforce English language setting on all Whisper transcription calls

## 9. Real-Time Transcription Streaming

- [x] 9.1 Extend recording WebSocket to stream transcript segments back to the frontend as they are produced by faster-whisper
- [x] 9.2 Build live transcript view component in Svelte: auto-scrolling list of transcript segments that updates in real-time via WebSocket
- [x] 9.3 Implement incremental audio chunk conversion (WebM → WAV) during recording to feed faster-whisper without waiting for recording to end

## 10. Speaker Diarization Backend

- [x] 10.1 Implement pyannote-audio model loading and initialization with Metal acceleration support
- [x] 10.2 Implement diarization service: accept WAV audio and return speaker segments with speaker labels, start_time, end_time
- [x] 10.3 Implement speaker-transcript alignment: merge diarization speaker segments with Whisper transcript segments, splitting transcript segments at speaker boundaries when needed
- [x] 10.4 Implement near-real-time diarization during recording: process buffered 30-second audio windows with overlap, send provisional speaker labels via WebSocket
- [x] 10.5 Implement final diarization pass: re-run diarization on complete audio after recording stops and update all speaker labels for consistency
- [x] 10.6 Persist speakers to database: create speaker records with diarization_label, associate transcript segments with speakers

## 11. Speaker Management Frontend

- [x] 11.1 Build speaker list panel in session view showing all detected speakers with their provisional labels and assigned names
- [x] 11.2 Build speaker name assignment UI: click a speaker label to assign player_name and character_name, with dropdown pre-populated from campaign roster
- [x] 11.3 Implement speaker reassignment for individual segments: select a transcript segment and change its speaker via dropdown
- [x] 11.4 Implement bulk speaker reassignment: multi-select consecutive transcript segments and reassign to a different speaker
- [x] 11.5 Display speaker labels on transcript segments as colored badges showing "CharacterName (PlayerName)" format

## 12. Speaker Management Backend

- [x] 12.1 Implement speaker name assignment API: PUT `/api/speakers/{id}` to update player_name and character_name, cascading display changes to all associated segments
- [x] 12.2 Implement segment speaker reassignment API: PUT `/api/transcript-segments/{id}/speaker` to change an individual segment's speaker
- [x] 12.3 Implement bulk segment reassignment API: PUT `/api/sessions/{id}/reassign-segments` accepting a list of segment IDs and target speaker ID
- [x] 12.4 Implement roster-to-speaker suggestion endpoint: GET `/api/sessions/{id}/speaker-suggestions` returning campaign roster entries for the assignment dropdown

## 13. Summary Generation Backend

- [x] 13.1 Implement Ollama client service: health check, model list, and generate endpoints via httpx calling `http://localhost:11434`
- [x] 13.2 Implement Ollama connectivity checks: verify Ollama is running and the configured model is available, with descriptive error messages
- [x] 13.3 Implement full session summary prompt: build the prompt template that takes a transcript with speaker labels and requests a narrative session summary
- [x] 13.4 Implement per-player POV summary prompt: build the prompt template that takes a transcript and a character name, requesting a summary from that character's perspective
- [x] 13.5 Implement transcript chunking for long sessions: split transcript into overlapping chunks by token count, summarize each chunk, then produce a meta-summary
- [x] 13.6 Implement summary generation API: POST `/api/sessions/{id}/generate-summary` (type: full or pov) that runs the LLM and stores the result
- [x] 13.7 Implement summary CRUD endpoints: GET/PUT/DELETE `/api/summaries/{id}` for retrieval, manual editing, and deletion
- [x] 13.8 Implement summary regeneration with confirmation: POST `/api/sessions/{id}/regenerate-summary` that replaces existing summaries
- [x] 13.9 Store summary metadata: model name and generation timestamp on every summary record

## 14. Summary Frontend

- [x] 14.1 Build summary section in session detail page showing full session summary and per-player POV summaries
- [x] 14.2 Build "Generate Summary" and "Generate POV Summaries" buttons with loading states; disable when prerequisites not met (no transcript, no speaker names)
- [x] 14.3 Build summary display component with markdown rendering, model/timestamp metadata display, and "Edit" toggle
- [x] 14.4 Build inline summary editor: switch between read-only and editable modes with save/cancel
- [x] 14.5 Build regeneration UI with confirmation dialog before overwriting existing summaries
- [x] 14.6 Display Ollama connectivity errors with setup guidance (install Ollama, pull model)

## 15. Export and Sharing Backend

- [x] 15.1 Implement PDF export endpoint: GET `/api/summaries/{id}/export/pdf` generating a styled PDF via WeasyPrint with session metadata header
- [x] 15.2 Implement text export endpoint: GET `/api/summaries/{id}/export/text` generating a plain text file with metadata header
- [x] 15.3 Implement batch POV export endpoint: GET `/api/sessions/{id}/export/pov-all` returning a ZIP file containing one PDF per character
- [x] 15.4 Implement transcript export endpoint: GET `/api/sessions/{id}/export/transcript` generating a text file with `[timestamp] Speaker: text` format
- [x] 15.5 Implement email content generation endpoint: GET `/api/summaries/{id}/email-content` returning pre-filled subject line and formatted body
- [x] 15.6 Implement direct email sending endpoint: POST `/api/summaries/{id}/send-email` using configured SMTP settings; validate config exists before attempting

## 16. Export and Sharing Frontend

- [x] 16.1 Build export button group on summary view: "Export PDF", "Export Text", "Copy to Clipboard" for each summary
- [x] 16.2 Implement clipboard copy with toast confirmation notification
- [x] 16.3 Build "Export All POV Summaries" button that downloads the ZIP of all character PDFs
- [x] 16.4 Build "Export Transcript" button on the transcript tab
- [x] 16.5 Build "Prepare Email" view showing pre-filled subject and body with copy buttons
- [x] 16.6 Build "Send Email" dialog with recipient email input, preview, and send/cancel buttons; show error on failure

## 17. Settings

- [x] 17.1 Implement settings API: GET/PUT `/api/settings` for reading and updating app configuration
- [x] 17.2 Build settings page with Whisper model selection dropdown (tiny, base, small, medium, large-v3)
- [x] 17.3 Build settings section for Ollama model configuration with a text input and "Test Connection" button
- [x] 17.4 Build settings section for email SMTP configuration (host, port, username, password, sender address) with "Send Test Email" button
- [x] 17.5 Implement SMTP credential storage with encryption at rest for the password field

## 18. First-Run Experience and Polish

- [x] 18.1 Implement first-run detection and setup wizard: check for data directory, Whisper model, and Ollama availability on startup
- [x] 18.2 Build first-run wizard UI: guide DM through initial Whisper model download and Ollama setup with progress indicators
- [x] 18.3 Configure PWA manifest and service worker for offline-capable browser experience
- [x] 18.4 Build Svelte frontend production build pipeline and integrate static assets into the Python package for serving via FastAPI
- [x] 18.5 Add global error boundary and toast notification system for async operation failures
- [x] 18.6 Implement `data/` directory backup guidance: display data directory path in settings so the DM knows what to back up
