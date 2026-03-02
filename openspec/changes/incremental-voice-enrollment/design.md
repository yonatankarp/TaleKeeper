## Context

TaleKeeper uses SpeechBrain's ECAPA-TDNN encoder to extract 192-dimensional speaker embeddings from audio windows. The current diarization pipeline has two paths:

1. **Unsupervised** (no voice signatures): Agglomerative clustering with cosine distance — produces generic "Player 1", "Player 2" labels that frequently merge or split speakers incorrectly.
2. **Signature-based** (with voice signatures): Cosine similarity matching against stored per-roster-entry embeddings — produces accurate named labels.

Voice signatures are currently created only via an explicit `POST /api/sessions/{id}/generate-voice-signatures` endpoint, which extracts embeddings from ALL segments of ALL labeled speakers in a completed session. This batch-only approach means users must: fully label a session → hit a separate button → then future sessions benefit. Most users never discover this workflow.

The speaker update endpoint (`PUT /api/speakers/{id}`) already accepts player_name and character_name fields, and the frontend SpeakerPanel provides a roster dropdown. No frontend changes are needed — only the backend needs to react to these assignments.

## Goals / Non-Goals

**Goals:**
- Automatically enroll voice signatures when a speaker is assigned to a roster entry during transcript review
- Keep enrollment fast (seconds, not minutes) even for 2-4 hour session recordings
- Accumulate signature quality across multiple sessions via weighted merging
- Run enrollment non-blocking so the speaker update UI remains responsive

**Non-Goals:**
- Replacing the existing batch `generate-voice-signatures` endpoint (it remains available for explicit full re-enrollment)
- Handling multi-speaker overlap or speaker turn detection improvements
- Frontend UI changes (existing dropdown is sufficient)
- Real-time enrollment during live recording (only post-recording review)
- Tuning the diarization clustering parameters or similarity thresholds

## Decisions

### Decision 1: Trigger enrollment from `PUT /api/speakers/{id}` via BackgroundTasks

After the speaker record is updated, the endpoint checks whether the new player_name + character_name match an active roster entry in the session's campaign. If so, it schedules `enroll_speaker_voice` as a FastAPI `BackgroundTask`.

**Why:** This is the exact point where the user declares "this speaker is Alice/Gandalf." No new UI or endpoints needed — the enrollment is a natural side-effect of an action the user already performs.

**Alternative considered:** A dedicated "Learn this voice" button in the UI. Rejected because it adds UX complexity and the user has already provided all needed information via the speaker assignment.

### Decision 2: Cap audio sampling at 120 seconds, longest segments first

The enrollment function sorts the speaker's transcript segments by duration (descending) and accumulates segments until reaching ~120 seconds total. If a segment would exceed the cap, it truncates to use the remaining budget (minimum 0.5s).

**Why:** Speaker verification research shows diminishing returns after 2-3 minutes of speech. Sessions are 2-4 hours, and a single speaker may have 30-60 minutes of audio — processing all of it would take minutes of CPU time for minimal quality improvement. Selecting longest segments first maximizes clean speech (less boundary noise from short utterances). On Apple Silicon MPS, 120 seconds of audio processes in ~2-3 seconds.

**Alternative considered:** Random sampling. Rejected because long segments are more likely to contain clean, single-speaker audio, while short segments may be partial words or crosstalk.

### Decision 3: Weighted average merge for existing signatures

When a voice signature already exists for a roster entry, the new embedding is merged via weighted average: `combined = (old_emb * old_count + new_emb * new_count) / total`. The result is L2-normalized and stored with the updated total sample count.

**Why:** This ensures early corrections have proportionally less influence as more data accumulates, which is the correct behavior — a signature built from 5 sessions should not be destabilized by one new correction. The `num_samples` field already exists in the schema.

**Alternative considered:** Replace signature entirely on each enrollment. Rejected because it discards accumulated knowledge and makes signatures volatile. Also considered storing individual sample embeddings for exact averaging, but this would require schema changes and increased storage for negligible accuracy improvement.

### Decision 4: Non-blocking execution via FastAPI BackgroundTasks

Enrollment runs after the HTTP response is sent, using FastAPI's built-in `BackgroundTasks` mechanism. If enrollment fails (missing audio, extraction error), it logs a warning and silently continues — no user-facing error.

**Why:** The ECAPA-TDNN encoder inference is CPU-intensive (50-200ms per 3-second window). Even with the 120s cap, processing takes 2-3 seconds. Blocking the speaker update response would make the UI feel sluggish. BackgroundTasks is the simplest async execution mechanism already available in FastAPI — no need for Celery, task queues, or separate workers.

**Alternative considered:** `asyncio.create_task()` for fire-and-forget. Rejected because BackgroundTasks ties the lifecycle to the request and is the idiomatic FastAPI pattern. Also considered a dedicated task queue (Celery/RQ), but this is overkill for a local single-user app.

## Risks / Trade-offs

**[Risk] Enrollment from noisy/misassigned segments degrades signature quality** → The weighted merge means bad enrollments are diluted by good ones over time. Users can also delete a signature via the existing DELETE endpoint to start fresh.

**[Risk] Multiple rapid speaker updates could trigger concurrent enrollments for the same roster entry** → BackgroundTasks execute sequentially per-request, and SQLite's WAL mode handles concurrent writes. Worst case: two enrollments both read the same `num_samples`, producing a slightly off weight. Acceptable for this use case since signatures converge over time.

**[Trade-off] Weighted merge with normalized embeddings is an approximation** → The existing signature is L2-normalized (not a raw sum), so `old_emb * old_count` is not the true sum of historical embeddings. This means early samples are slightly underweighted as more data accumulates. In practice, the direction is correct and the approximation converges. Exact averaging would require storing the un-normalized embedding sum, which adds schema complexity for negligible accuracy gain.

**[Trade-off] No user feedback that enrollment happened** → The background task completes silently. Users won't know their corrections are being learned. This is acceptable for now — the value becomes apparent when the next session's diarization is more accurate. A future enhancement could add a subtle toast notification.
