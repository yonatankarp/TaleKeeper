## Why

Sessions are often recorded across multiple devices or in multiple parts — a DM mic, a player mic, a phone backup, or a session split across two recording sessions. Currently TaleKeeper only accepts a single audio file per session, forcing users to manually merge audio externally before uploading.

## What Changes

- Sessions can have multiple audio files uploaded, not just one
- The upload UI accepts multiple files and lists them with ordering controls
- Files are merged in user-defined order (via ffmpeg) before transcription begins
- The merged file replaces the session's single `audio_path` for downstream processing (transcription, diarization)
- Existing single-file upload flow is preserved as the common case

## Capabilities

### New Capabilities
- `multi-audio-upload`: Upload and manage multiple audio files for a session, merge them into a single audio file for processing

### Modified Capabilities
- `audio-upload`: Extends existing single-file upload to support multiple files with ordering and merging

## Impact

- **Database**: New `session_audio_files` table to store individual uploaded file paths and their order; existing `audio_path` on sessions continues to hold the merged output path
- **Backend**: New endpoints to upload additional audio files, list them, reorder, and delete; merge step invoked before transcription using ffmpeg
- **Frontend**: Session page upload UI extended — file list with drag-to-reorder or up/down buttons, merge-and-transcribe action
- **Dependencies**: ffmpeg (already a system dep) used for audio concatenation
