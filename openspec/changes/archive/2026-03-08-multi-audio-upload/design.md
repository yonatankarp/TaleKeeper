## Context

Sessions currently support one audio file stored at `sessions.audio_path`. The single-file upload endpoint (`POST /api/sessions/{session_id}/upload-audio`) overwrites whatever was previously uploaded. Transcription and diarization read directly from `audio_path`.

ffmpeg is already a system dependency used for audio normalization and chunk merging during live recording.

## Goals / Non-Goals

**Goals:**
- Allow uploading N audio files per session, each stored individually on disk
- Let the user order files before merging
- Merge ordered files into a single audio file (stored at `sessions.audio_path`) as the trigger for transcription
- Preserve the existing single-file fast path

**Non-Goals:**
- Simultaneous multi-track mixing (files are concatenated sequentially, not mixed)
- Streaming upload progress
- Editing/trimming individual files after upload

## Decisions

### 1. New `session_audio_files` table, `audio_path` unchanged
Store each uploaded part in a new table with an explicit `sort_order` column. `sessions.audio_path` continues to hold the merged output — all downstream code (transcription, diarization, playback) is unchanged.

**Alternative considered:** Store a JSON array in `sessions.audio_path`. Rejected — type change would break all existing path reads without migration.

### 2. Merge on demand, not on upload
Merging happens when the user explicitly triggers "Merge & Transcribe", not automatically on each upload. This lets users upload all parts first, reorder them, then merge once.

**Alternative considered:** Auto-merge after every upload. Rejected — wasteful for large files and confusing if user wants to reorder.

### 3. ffmpeg concat demuxer for merging
Use `ffmpeg -f concat` with a generated filelist to concatenate parts. This is lossless for same-codec files and handles mixed formats (webm, mp3, m4a, wav) by re-encoding to a common output format (wav).

### 4. Reordering via sort_order, no drag-and-drop protocol
`sort_order` is an integer on each row. A `PUT /api/sessions/{session_id}/audio-files/reorder` endpoint accepts an ordered list of IDs and reassigns `sort_order` values. Frontend uses up/down buttons (no drag library needed).

### 5. Single-file upload preserved
`POST /api/sessions/{session_id}/upload-audio` continues to work — it inserts one row into `session_audio_files` and immediately merges + sets `audio_path`. Existing clients and the simple case both work without changes.

## Risks / Trade-offs

- **Large files**: Merging multiple large audio files is CPU/disk intensive and blocks briefly. → Run ffmpeg via `asyncio.to_thread` to keep the event loop free.
- **Partial uploads**: If a user uploads 2 of 3 files and transcribes, they get an incomplete transcript. → No automatic guard; user is responsible for uploading all parts before merging.
- **Disk space**: Individual parts + merged file are all stored. → Parts can be deleted after merge (configurable; default: keep parts).

## Migration Plan

1. Add `session_audio_files` table via a new DB migration (non-destructive, additive only).
2. Existing sessions with `audio_path` set are unaffected — the new table starts empty for them.
3. No data backfill needed.
4. Rollback: drop `session_audio_files` table; existing `audio_path` column is untouched.
