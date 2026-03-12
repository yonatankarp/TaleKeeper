## Why

Users who record D&D sessions via Google Meet with Gemini AI notes already have a complete, well-structured transcript — speaker names, timestamps, and dialogue — but cannot use it in TaleKeeper without going through the audio transcription pipeline. This forces unnecessary processing (and hardware requirements) when the transcript already exists.

## What Changes

- New endpoint `POST /api/sessions/{session_id}/import-transcript` accepts a PDF file upload and imports its content as a transcript
- New service parses Gemini's transcript format (speaker name + timestamp on one line, dialogue below) into `transcript_segments` and `speakers` rows
- Session status advances directly to `completed` after import, bypassing the `audio_ready → transcribing` pipeline
- New "Import Transcript" button in the session recording UI (alongside the existing "Upload Audio" option)
- Existing segments and speakers are cleared before importing, consistent with the retranscribe flow

## Capabilities

### New Capabilities
- `gemini-transcript-import`: Upload a Gemini-exported PDF and populate a session's transcript and speakers without audio processing

### Modified Capabilities
- `transcription`: Sessions can now reach `completed` status without an audio file or running Whisper

## Impact

- **Backend**: New `services/transcript_import.py`; new endpoint in `routers/transcripts.py`; uses existing `pymupdf` (`fitz`) dependency — no new packages required
- **Database**: No schema changes; imports write to existing `transcript_segments` and `speakers` tables; `sessions.audio_path` remains `NULL` for imported sessions
- **Frontend**: `RecordingControls.svelte` gains an "Import Transcript" button and file picker (`.pdf`); new `importTranscriptPdf` helper in `lib/api.ts`
- **Testing**: New unit tests for the PDF parser; existing transcript and session tests unaffected
