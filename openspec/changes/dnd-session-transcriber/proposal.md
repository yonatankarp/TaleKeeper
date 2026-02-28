## Why

Dungeon Masters running tabletop D&D sessions have no good way to capture what happens at the table. After a long session, details get lost — plot points, NPC interactions, player decisions, and character moments fade from memory. Existing note-taking breaks immersion, and generic transcription tools don't understand the multi-speaker, narrative nature of a TTRPG session. DMs need a tool that passively records and transcribes sessions, identifies who said what, and produces useful summaries — all without requiring an internet connection, since game nights often happen in basements, cabins, or other places with poor connectivity.

## What Changes

- **Audio capture and on-device transcription**: Record session audio via browser microphone and transcribe in real-time using Whisper, running entirely on-device (targeting Apple Silicon M1/M2).
- **Speaker diarization with manual correction**: Automatically detect and segment different speakers in the audio stream, then allow the DM to assign or correct character/player names for each detected speaker.
- **Campaign and session management**: Organize recordings into campaigns, each containing multiple sessions with their own player/character rosters.
- **Session summary generation**: After a session ends, generate a narrative summary of the session using a local LLM (via Ollama or llama-cpp-python). No cloud dependency.
- **Per-player POV summaries**: Generate individual summaries from each player character's perspective, focusing on what that character experienced, learned, and decided.
- **Export and sharing**: Export summaries as text/PDF for download. Optionally send summaries directly via email to players (configurable SMTP/API).
- **Persistent audio storage**: Store both raw audio recordings and transcripts locally, allowing replay and re-transcription.
- **Offline-first PWA**: The entire app runs locally in the browser as a Progressive Web App. All ML workloads (transcription, diarization, summarization) run on the user's machine with no cloud services required.

## Capabilities

### New Capabilities

- `audio-capture`: Browser-based audio recording, microphone access, and persistent audio storage.
- `transcription`: On-device speech-to-text using Whisper, producing timestamped transcript segments.
- `speaker-diarization`: Automatic speaker detection and segmentation, with UI for the DM to assign/correct speaker identities (player name and character name).
- `campaign-management`: CRUD operations for campaigns, sessions, and player/character rosters. Organizing sessions within campaigns.
- `summary-generation`: Local LLM-powered session summary creation — both a full session narrative summary and individual per-player POV summaries.
- `export-and-sharing`: Export summaries as text/PDF. Generate copy-paste-ready content. Optional direct email sending with configurable email service.

### Modified Capabilities

None — this is a greenfield project with no existing capabilities.

## Impact

- **New codebase**: Entirely new application. No existing code is affected.
- **Dependencies**: Whisper (or faster-whisper) for transcription, pyannote-audio for speaker diarization, llama-cpp-python or Ollama for local LLM inference, FastAPI for the backend API server, SQLite for local data persistence.
- **Hardware requirements**: Targets Apple Silicon Macs (M1/M2+) with Metal acceleration for ML workloads. Requires sufficient RAM for running Whisper + local LLM models concurrently.
- **Frontend**: Lightweight web UI served locally by the Python backend. PWA-capable for a native app feel.
- **Storage**: Local filesystem for audio files, SQLite database for transcripts, campaigns, sessions, and summaries.
