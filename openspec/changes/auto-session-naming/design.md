## Context

Sessions are currently identified by a user-provided `name`, a `date`, and an auto-increment `id`. There is no session numbering, and names are whatever the user types at creation time. The LLM infrastructure (`llm_client.py`) already supports OpenAI-compatible completions and is used by the summarization service. The processing pipeline flows: recording → `audio_ready` → `transcribing` → `completed`, with transcription and diarization running in an SSE stream before the status is set to `completed`.

## Goals / Non-Goals

**Goals:**
- Automatic session numbering scoped per campaign, assigned at session creation
- Configurable starting number per campaign (for groups migrating from other tools)
- LLM-generated catchy session title from transcript content, triggered after transcription
- Auto-applied naming in "Session N: Title" format, editable afterward
- Backfill migration for existing sessions

**Non-Goals:**
- Renaming sessions based on edited transcripts (regeneration is manual only)
- Generating names from summary content (we use the raw transcript)
- Multi-language prompt templates (use English prompts; the LLM handles multilingual transcripts)
- Custom naming format patterns (hardcoded "Session N: Title" format)

## Decisions

### 1. Session number assignment — at creation time

Assign `session_number` during `create_session` by querying `MAX(session_number)` for the campaign and adding 1. The starting offset comes from `session_start_number` on the campaigns table (default 0).

**Why not at completion time?** Users expect to see "Session 5" immediately when they create it, not after recording finishes. The number is an index, not derived from content.

**Alternatives considered:**
- Assign at completion: Deferred numbers are confusing; a draft session should already show its number.
- Use database `id` as number: IDs are global, not per-campaign, so Session 1 of Campaign B might be id=47.

### 2. Name generation — separate from the processing pipeline

Add a dedicated service function `generate_session_name()` in a new `services/session_naming.py` module, called after the status transitions to `completed`. This runs as a fire-and-forget task after the SSE stream's `done` event — the processing pipeline itself is not blocked by name generation.

**Why not inline in the SSE stream?** Name generation is non-critical. If the LLM is down or slow, it should not delay the "done" signal. The session already has its "Session N" prefix; the title is a nice-to-have enhancement.

**Why a separate module?** `summarization.py` handles multi-paragraph narrative output with chunking. Session naming is a single short prompt returning 2-6 words. Different concerns, different prompts, different output format.

**Alternatives considered:**
- Add a new SSE phase: Couples name generation to the processing stream; failure would require special error handling in the SSE protocol.
- Generate name when user requests summary: Delays naming unnecessarily; users may never generate a summary.

### 3. Transcript sampling for the prompt

Send the first ~2000 and last ~2000 characters of the formatted transcript to the LLM. Most sessions have a clear arc: the beginning sets the scene, the end has the climax/resolution. This avoids sending massive transcripts for a 3-word title.

**Why not the full transcript?** A 4-hour session transcript can be 50k+ tokens. We need 3-5 words back. Sampling is sufficient and keeps cost/latency minimal.

**Why not use the summary?** The summary may not exist yet (it's user-triggered). We want naming to be automatic and immediate.

### 4. Database schema — two new columns via migration

- `sessions.session_number INTEGER` — nullable for backward compatibility; backfill migration assigns numbers by `created_at` order per campaign
- `campaigns.session_start_number INTEGER NOT NULL DEFAULT 0` — the number of the first session (0 = "Session 0", 1 = "Session 1", etc.)

**Why nullable session_number?** The `CREATE TABLE IF NOT EXISTS` pattern means the column won't exist on older databases. The migration adds it and backfills. After migration, new sessions always get a number.

### 5. Name storage — reuse the existing `name` field

The auto-generated name overwrites `sessions.name` with "Session N: Catchy Title". No new column needed. Users already edit `name` via the update endpoint.

**Why not a separate `title` column?** Adding a column means managing two display strings. The current `name` field is already user-editable and displayed everywhere. Overwriting it is simpler and the user can change it to whatever they want.

### 6. Frontend display — show session number as primary identifier

The campaign dashboard and session detail views show "Session N: Title" from the `name` field. The `session_number` column is used for sorting and for generating the "Session N" prefix on creation — it is the source of truth for ordering, while `name` is the display string.

## Risks / Trade-offs

- **LLM unavailable at naming time** → The session keeps its creation-time name ("Session N") which is still useful. No degradation in core functionality.
- **Concurrent session creation race condition** → Two simultaneous `create_session` calls for the same campaign could get the same `MAX(session_number)`. Mitigation: use a transaction with `SELECT MAX(...) + 1` in a single atomic query. SQLite's WAL mode serializes writes.
- **Backfill ordering ambiguity** → Existing sessions without numbers are ordered by `created_at`. If two sessions share the same second, ordering is by `id` (stable but arbitrary). Acceptable for a one-time migration.
- **Name overwrite surprise** → Users who set a custom name at creation time will have it overwritten after transcription. Mitigation: only generate a name if the current name matches the auto-assigned "Session N" pattern (i.e., the user hasn't customized it).

## Migration Plan

1. Add `session_number` column to `sessions` (nullable INTEGER)
2. Add `session_start_number` column to `campaigns` (INTEGER DEFAULT 0)
3. Backfill: for each campaign, number existing sessions by `created_at ASC, id ASC` starting from 0
4. Update existing session names to "Session N" format (only for sessions whose name doesn't already contain meaningful text — skip if name is non-empty and doesn't match a generic pattern)

Rollback: columns can be dropped, but SQLite doesn't support `DROP COLUMN` in older versions. Acceptable since this is additive-only.

## Open Questions

- Should "Session 0" be the default for the first session (D&D convention for a "session zero"), or should it start at "Session 1"? Currently defaulting to 0 per user's original description.
