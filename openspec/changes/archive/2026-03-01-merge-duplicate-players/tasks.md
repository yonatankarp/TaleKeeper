## 1. Backend API

- [x] 1.1 Add `MergeSpeakers` Pydantic request model with `source_speaker_id` and `target_speaker_id` fields in `src/talekeeper/routers/speakers.py`
- [x] 1.2 Implement `POST /api/sessions/{session_id}/merge-speakers` endpoint: validate both speakers exist, belong to the same session matching the URL param, and are different; reassign all transcript segments from source to target; look up source speaker's roster entry and delete its voice signature if one exists; delete the source speaker record; return the updated target speaker with segment count. Wrap in a single DB transaction for atomicity.
- [x] 1.3 Add backend tests for the merge endpoint: successful merge with segment reassignment, merge preserves target identity, merge with zero-segment source, self-merge rejection (400), cross-session rejection (400), nonexistent speaker (404), session mismatch (400), voice signature cleanup when source has signature, no-op when neither has signature

## 2. Frontend API Layer

- [x] 2.1 Add `mergeSpeakers(sessionId, sourceSpeakerId, targetSpeakerId)` function in `frontend/src/lib/api.ts` that calls `POST /api/sessions/{sessionId}/merge-speakers`

## 3. Frontend UI — Speaker Panel

- [x] 3.1 Add a "Merge into..." button per speaker row in batch edit mode in `frontend/src/components/SpeakerPanel.svelte`
- [x] 3.2 Implement target speaker selector: clicking "Merge into..." shows a dropdown of other speakers in the session (excluding the source speaker itself)
- [x] 3.3 Implement confirmation dialog before merge: display source speaker name, target speaker name, number of segments to reassign, and a voice signature warning if the source has one. Include "Confirm" and "Cancel" buttons.
- [x] 3.4 On confirm: call `mergeSpeakers`, reload the speaker list, and show a success notification. On cancel: close dialog and return to batch edit mode.
- [x] 3.5 Fetch segment counts per speaker so the confirmation dialog can display how many segments will be reassigned
