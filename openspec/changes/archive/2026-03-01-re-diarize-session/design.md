## Context

After transcription completes, TaleKeeper runs `run_final_diarization` which clusters speaker embeddings and aligns them with transcript segments. The speaker count is fixed at transcription time (from campaign default or override). If the count is wrong — producing merged or split speakers — the only fix today is to retranscribe the entire session, re-running Whisper on the full audio. This is slow and unnecessary since the transcript text is correct; only the speaker clustering needs to change.

The existing `run_final_diarization(session_id, wav_path, num_speakers_override)` already supports re-running diarization given a WAV path and speaker count. However, it **inserts new speaker rows** without deleting old ones first, and assumes `transcript_segments.speaker_id` is NULL. A re-diarize operation must clean up old state before calling it.

## Goals / Non-Goals

**Goals:**
- Allow users to re-run diarization on a completed session with a different speaker count, without re-transcribing
- Preserve all transcript segment text and timestamps
- Clean up old speakers and their session-sourced voice signatures before re-diarizing
- Use campaign voice signatures for matching when available (same as initial diarization)
- Provide progress feedback to the frontend via SSE
- Place the trigger in the existing retranscribe bar, next to the "Retranscribe" button

**Non-Goals:**
- Modifying the diarization algorithm itself (clustering, embeddings, alignment)
- Adding the ability to partially re-diarize (e.g., only a time range)
- Preserving manual speaker edits across re-diarization (they are lost by design)
- Caching WAV conversions between retranscribe and re-diarize operations

## Decisions

### 1. New SSE endpoint at `POST /api/sessions/{session_id}/re-diarize`

**Choice:** Separate endpoint in `routers/speakers.py` rather than adding a flag to the retranscribe endpoint.

**Rationale:** The retranscribe endpoint orchestrates transcription + diarization in sequence. Re-diarize skips transcription entirely. Mixing both into one endpoint would add branching complexity. A separate endpoint is simpler and mirrors the clear conceptual separation: "redo text" vs "redo speakers."

**Alternatives considered:**
- Query parameter on retranscribe (`?diarize_only=true`) — rejected because it would split the endpoint's responsibility and SSE event contract

### 2. Cleanup sequence: NULL speaker_ids → delete voice signatures → delete speakers

**Choice:** Before calling `run_final_diarization`, the endpoint will:
1. Set `speaker_id = NULL` on all transcript segments for the session
2. Delete voice signatures sourced from this session (by matching `source_session_id`)
3. Delete all speaker rows for the session

**Rationale:** `run_final_diarization` creates new speaker rows and updates `speaker_id` via alignment. We must clear old speaker data first. Voice signatures sourced from this session become invalid since they were derived from the old speaker-to-segment mapping. Campaign-level voice signatures from other sessions are preserved and used for matching.

**Note on voice signature deletion:** The `voice_signatures` table has a `source_session_id` column. We delete only signatures where `source_session_id = session_id`, not all signatures for the campaign. This preserves signatures generated from other sessions.

### 3. SSE event contract

**Choice:** Reuse the same SSE event types as the retranscribe endpoint where applicable:
- `event: phase` with `{"phase": "diarization"}` — emitted at start (since there's no transcription phase)
- `event: done` with `{"segments_count": N}` — emitted on success
- `event: error` with `{"message": "..."}` — emitted on failure

**Rationale:** The frontend already handles these event types. No new event types means the frontend SSE parsing logic can be reused with minimal changes.

### 4. Session status during re-diarization

**Choice:** Set session status to `diarizing` during the operation, then back to `completed` when done (or on error).

**Rationale:** Using `transcribing` would be misleading since no transcription is happening. A distinct status lets the UI show appropriate messaging. The retranscribe bar already checks `status !== 'transcribing'` to hide itself during transcription; `diarizing` should similarly disable the buttons to prevent concurrent operations.

### 5. Request body uses `num_speakers` from JSON body

**Choice:** `POST /api/sessions/{session_id}/re-diarize` accepts `{"num_speakers": N}` in the request body, required, validated 1-10.

**Rationale:** The user explicitly chooses a new speaker count — that's the whole point of this feature. Making it required avoids ambiguity about which count is used.

### 6. Button placement in retranscribe bar

**Choice:** Add a "Re-diarize" button in the `.retranscribe-bar` div, next to the existing "Retranscribe" button. Both buttons share the same `retranscribeNumSpeakers` input — the speaker count selector serves both actions.

**Rationale:** The user asked for it near the retranscribe button. The existing speaker count input already controls the number that would be passed to diarization, so sharing it avoids UI duplication.

## Risks / Trade-offs

**Manual edits are lost** — Any speaker name assignments, segment reassignments, or merges are wiped. The frontend should show a confirmation dialog before proceeding.
→ Mitigation: Confirmation dialog with clear warning text.

**WAV conversion overhead** — The audio must be converted to WAV for diarization each time. For long sessions this takes seconds.
→ Mitigation: Acceptable since diarization itself takes longer. Could cache WAV files in the future if needed.

**Concurrent operations** — If a user triggers re-diarize while another operation is in progress, data could corrupt.
→ Mitigation: The endpoint checks session status and rejects if not `completed`. The UI disables buttons when status is not `completed`.
