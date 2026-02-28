## Why

TaleKeeper currently only supports live browser-based recording via WebSocket. Users who record sessions on external devices (e.g., an iPhone voice memo) have no way to import that audio for transcription and summarization. This is a common use case — the DM records a 4-hour session on their phone and wants to process it later on their computer.

## What Changes

- Add a backend endpoint to accept audio file uploads (m4a, mp3, wav, webm, etc.) and save them in their original format
- Add a backend endpoint to trigger the transcription + diarization pipeline on uploaded audio, with SSE progress streaming
- Add an "Upload Audio" button on the Recording tab alongside the existing "Start Recording" button
- Show upload progress, then transcription progress (chunk N/M) in the UI
- Uploading to a session that already has audio replaces the existing audio and clears old transcript/speakers

## Capabilities

### New Capabilities
- `audio-upload`: Accepting audio file uploads from external devices, storing in original format, and triggering the transcription/diarization pipeline with progress feedback

### Modified Capabilities
- `audio-capture`: Adding upload as an alternative audio ingestion path alongside live recording. The storage requirement changes to support multiple audio formats (not just webm).

## Impact

- **Backend**: New router or endpoints in `recording.py` for file upload and processing. Uses existing `transcribe_chunked` and `run_final_diarization` pipelines.
- **Frontend**: Changes to `RecordingControls.svelte` to add upload button and progress UI.
- **Storage**: Audio files may now be .m4a, .mp3, etc. instead of only .webm. The `audio_path` column already stores the full path so no DB schema change needed.
- **Dependencies**: pydub/ffmpeg already handles format conversion in the chunked pipeline — no new dependencies.
