# Multi-Audio Upload

## Purpose

Allow the DM to upload multiple audio files to a session, manage them as ordered parts, and merge them into a single audio file before triggering transcription.

## Requirements

### Requirement: Upload multiple audio files to a session
The system SHALL allow the DM to upload multiple audio files to a session. Each file SHALL be stored individually on disk and tracked in a `session_audio_files` table with an explicit sort order. Accepted formats are the same as single-file upload: m4a, mp3, wav, webm, ogg, flac.

#### Scenario: Upload first audio part
- **WHEN** the DM uploads an audio file to a session that has no existing parts
- **THEN** the file is stored on disk, a row is inserted into `session_audio_files` with `sort_order = 1`, and the file appears in the parts list

#### Scenario: Upload additional audio part
- **WHEN** the DM uploads another audio file to a session that already has parts
- **THEN** the new file is stored on disk and appended to the parts list with the next sort order value

#### Scenario: Unsupported file type rejected
- **WHEN** the DM uploads a non-audio file
- **THEN** the system rejects the upload with an error indicating only audio files are accepted

### Requirement: View and manage uploaded audio parts
The system SHALL display all uploaded audio parts for a session in order. The DM SHALL be able to remove any individual part. The DM SHALL be able to reorder parts using up/down controls.

#### Scenario: List parts in order
- **WHEN** the DM opens a session with multiple audio parts uploaded
- **THEN** all parts are shown in sort order with filename, size, and remove/reorder controls

#### Scenario: Remove a part
- **WHEN** the DM clicks remove on an audio part
- **THEN** the file is deleted from disk and removed from the parts list

#### Scenario: Reorder parts
- **WHEN** the DM moves a part up or down
- **THEN** the sort order is updated and the list reflects the new order immediately

### Requirement: Merge audio parts and trigger transcription
The system SHALL merge all uploaded audio parts in sort order into a single audio file using ffmpeg, store the result as the session's `audio_path`, and then trigger the transcription pipeline. Merging SHALL be performed asynchronously so the event loop is not blocked.

#### Scenario: Merge and transcribe
- **WHEN** the DM clicks "Merge & Transcribe" with at least one audio part uploaded
- **THEN** the system concatenates all parts in order into a single wav file, sets `sessions.audio_path` to the merged file, and begins transcription with progress streamed via SSE

#### Scenario: Single part skips merge
- **WHEN** the DM clicks "Merge & Transcribe" with exactly one audio part
- **THEN** the system uses the single file directly (or copies it) as `audio_path` without invoking ffmpeg concat

#### Scenario: No parts uploaded
- **WHEN** the DM clicks "Merge & Transcribe" with no audio parts uploaded
- **THEN** the system returns a 400 error and no processing begins
