## Context

Speaker diarization infrastructure (pyannote-audio pipeline, alignment logic, speaker DB table) existed but was never wired into the recording or retranscription flows. Transcript segments had no speaker data after recording, and the frontend only displayed speaker names when both character and player names were manually set. Raw pyannote labels like "SPEAKER_00" leaked into the speakers table when diarization was invoked manually.

## Goals / Non-Goals

**Goals:**
- Ensure diarization runs automatically after every recording stop and retranscription
- Replace raw pyannote labels with human-friendly "Player N" labels
- Display the best available speaker label in all frontend contexts
- Clean up stale speaker data when retranscribing

**Non-Goals:**
- Real-time diarization during recording (existing incremental transcription continues without speaker labels)
- New API endpoints (all changes use existing DB operations and service functions)
- Speaker reassignment UI (already specified, not part of this change)

## Decisions

### 1. Friendly "Player N" labels via enumeration
**Decision:** Generate speaker labels as `f"Player {idx}"` using `enumerate(unique_labels, start=1)` over the sorted unique pyannote labels.
**Rationale:** Raw pyannote labels (SPEAKER_00, SPEAKER_01) are meaningless to the DM. "Player 1", "Player 2" are immediately understandable and serve as useful defaults before manual name assignment. Sorting the raw labels before enumeration ensures deterministic numbering across runs of the same audio.

### 2. Diarization triggered in recording and retranscription routers
**Decision:** Call `run_final_diarization()` directly in the `finally` block of the recording WebSocket handler and inside the SSE generator of the retranscribe endpoint, rather than using a background task or queue.
**Rationale:** Diarization must complete before the session is marked "completed" so that the frontend sees speaker data on first load. Running it inline keeps the flow simple and avoids race conditions. The WebSocket is already closed by this point (recording) or the SSE stream absorbs the wait (retranscription).

### 3. WebM-to-WAV conversion with cleanup
**Decision:** Convert the merged WebM file to WAV using `webm_to_wav()` from the audio service, pass the WAV to diarization, then delete the WAV in a `finally` block.
**Rationale:** pyannote-audio requires WAV input. The WAV is a temporary artifact that can be large (16kHz mono PCM); cleaning it up immediately prevents disk bloat. The `try/finally` pattern ensures cleanup even if diarization fails.

### 4. Delete old speakers before retranscription diarization
**Decision:** Execute `DELETE FROM speakers WHERE session_id = ?` before retranscription begins, alongside deleting old transcript segments.
**Rationale:** Retranscription produces entirely new segments with potentially different timing. Old speaker records would have stale alignment data. Deleting them first ensures a clean slate for the new diarization pass.

### 5. Consistent speaker label fallback chain in frontend
**Decision:** Both `TranscriptView.speakerLabel()` and `SpeakerPanel.speakerDisplay()` use the same cascading fallback: character+player > character > player > diarization_label > empty.
**Rationale:** Users see the same label for a speaker regardless of which component they look at. The fallback ensures something meaningful is always displayed as soon as diarization completes, even before manual name assignment.

### 6. Reload transcript after retranscription completes
**Decision:** Add `await load()` in the `finally` block of `TranscriptView.retranscribe()` to re-fetch segments from the API.
**Rationale:** During retranscription, segments are streamed via SSE without speaker data (diarization runs after all segments are inserted). The reload fetches the complete segment records including speaker joins, replacing the placeholder segments from the SSE stream.
