## 1. Backend Upload Endpoint

- [x] 1.1 Add `POST /api/sessions/{session_id}/upload-audio` endpoint that accepts a multipart file upload via FastAPI `UploadFile`
- [x] 1.2 Validate the uploaded file has an audio MIME type (audio/*), reject with 400 otherwise
- [x] 1.3 Save the file to `data/audio/{campaign_id}/{session_id}.{ext}` deriving extension from the uploaded filename
- [x] 1.4 If session already has audio: delete old file, clear transcript_segments and speakers for the session
- [x] 1.5 Update session's `audio_path` in the database

## 2. Backend Process Endpoint

- [x] 2.1 Add `POST /api/sessions/{session_id}/process-audio` endpoint that returns an SSE `StreamingResponse`
- [x] 2.2 Reuse `transcribe_chunked` pipeline from existing retranscribe flow to process audio with chunk progress events
- [x] 2.3 Run `run_final_diarization` after transcription completes
- [x] 2.4 Set session status to `transcribing` at start, `completed` on success, recover on error

## 3. Audio Playback MIME Type

- [x] 3.1 Update `get_session_audio` endpoint in `recording.py` to derive MIME type from file extension instead of hardcoding `audio/webm`

## 4. Frontend Upload UI

- [x] 4.1 Add "Upload Audio" button to `RecordingControls.svelte` alongside "Start Recording"
- [x] 4.2 Add hidden file input accepting `audio/*` and wire it to the upload button
- [x] 4.3 Implement upload fetch call to `/api/sessions/{id}/upload-audio` with the selected file
- [x] 4.4 Show "Uploading..." state with disabled controls during upload
- [x] 4.5 After successful upload, automatically connect to `/api/sessions/{id}/process-audio` SSE stream
- [x] 4.6 Display transcription chunk progress (e.g., "Transcribing chunk 3 of 50")
- [x] 4.7 On completion, reload session data; on error, display error message

## 5. API Client

- [x] 5.1 Add `uploadAudio(sessionId, file)` method to `api.ts`
- [x] 5.2 Add `processAudio(sessionId)` SSE helper to `api.ts` that returns an EventSource or equivalent
