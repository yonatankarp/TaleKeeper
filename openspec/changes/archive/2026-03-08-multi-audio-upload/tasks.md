## 1. Database

- [x] 1.1 Add `session_audio_files` table migration in `db/connection.py` with columns: `id`, `session_id` (FK → sessions ON DELETE CASCADE), `file_path`, `original_name`, `sort_order`, `created_at`
- [x] 1.2 Add `_migrate_add_session_audio_files_table()` function and call it in the migration chain

## 2. Backend — Audio Parts Endpoints

- [x] 2.1 Add `POST /api/sessions/{session_id}/audio-parts` endpoint: accepts `UploadFile`, saves to disk under `data/audio/<campaign_id>/parts/<session_id>/`, inserts row into `session_audio_files` with next sort_order
- [x] 2.2 Add `GET /api/sessions/{session_id}/audio-parts` endpoint: returns ordered list of audio parts from `session_audio_files`
- [x] 2.3 Add `DELETE /api/sessions/{session_id}/audio-parts/{part_id}` endpoint: deletes file from disk and row from DB, renumbers sort_order
- [x] 2.4 Add `PUT /api/sessions/{session_id}/audio-parts/reorder` endpoint: accepts `{"order": [id, id, ...]}` and updates sort_order values accordingly

## 3. Backend — Merge Service

- [x] 3.1 Add `merge_audio_parts(session_id, output_path)` async function in `services/audio_merge.py`: fetches ordered parts from DB, builds ffmpeg concat filelist, runs ffmpeg via `asyncio.to_thread`, returns merged file path
- [x] 3.2 Handle single-part case: copy/symlink file directly as `audio_path` without invoking ffmpeg concat
- [x] 3.3 Add `POST /api/sessions/{session_id}/merge-audio` SSE endpoint: calls merge service, updates `sessions.audio_path`, clears existing transcript/speakers, then runs the existing transcription + diarization pipeline streaming progress events

## 4. Frontend — Audio Parts UI

- [x] 4.1 Add audio parts state and `loadAudioParts()` function to the session recording tab component
- [x] 4.2 Add multi-file upload input (accepts multiple files) that calls the new `POST audio-parts` endpoint for each file sequentially
- [x] 4.3 Render the parts list: filename, remove button, up/down reorder buttons
- [x] 4.4 Wire remove button to `DELETE audio-parts/{id}` and refresh list
- [x] 4.5 Wire up/down buttons to `PUT audio-parts/reorder` and refresh list
- [x] 4.6 Add "Merge & Transcribe" button that calls `POST merge-audio` and streams SSE progress (reuse existing progress display logic)
- [x] 4.7 Disable all upload/merge controls while transcription is in progress

## 5. Tests

- [x] 5.1 Integration test: upload two audio parts, verify both rows in `session_audio_files`
- [x] 5.2 Integration test: reorder parts, verify sort_order updated
- [x] 5.3 Integration test: delete a part, verify file removed and row gone
- [x] 5.4 Unit test: `merge_audio_parts` with mocked ffmpeg — verify concat filelist contents and `audio_path` updated correctly
- [x] 5.5 Integration test: `POST merge-audio` with no parts returns 400
