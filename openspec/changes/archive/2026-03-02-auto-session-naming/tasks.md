## 1. Database Schema & Migration

- [x] 1.1 Add `session_number INTEGER` column to sessions table in `_SCHEMA` and create migration function `_migrate_add_session_number_column` in `db/connection.py`
- [x] 1.2 Add `session_start_number INTEGER NOT NULL DEFAULT 0` column to campaigns table in `_SCHEMA` and create migration function `_migrate_add_session_start_number_column` in `db/connection.py`
- [x] 1.3 Implement backfill migration `_migrate_backfill_session_numbers` that numbers existing sessions per campaign by `created_at ASC, id ASC` starting from 0, and updates generic session names to "Session N" format

## 2. Backend — Session Numbering

- [x] 2.1 Modify `create_session` in `routers/sessions.py` to auto-assign `session_number` using `MAX(session_number) + 1` for the campaign (or `session_start_number` if no sessions exist)
- [x] 2.2 Modify `create_session` to auto-set session name to "Session N" when no name is provided by the user
- [x] 2.3 Update `SessionCreate` model to make `name` optional (default to auto-generated "Session N")
- [x] 2.4 Ensure `session_number` is included in all session query responses (`list_sessions`, `get_session`, etc.)

## 3. Backend — Session Name Generation Service

- [x] 3.1 Create `services/session_naming.py` with LLM prompt and `generate_session_name()` function that takes transcript text, calls the LLM, and returns a 2–6 word catchy title
- [x] 3.2 Implement transcript sampling in `generate_session_name`: use first ~2000 + last ~2000 chars for long transcripts, full text if under 4000 chars
- [x] 3.3 Add "Session N" pattern detection helper (`_is_auto_named(name)`) to check if a session name matches the auto-assigned pattern via regex

## 4. Backend — Auto-Naming Integration

- [x] 4.1 Add fire-and-forget name generation call after the `done` event in the SSE processing pipeline (`routers/recording.py`): if session is auto-named, generate title and update name to "Session N: Title"
- [x] 4.2 Add the same fire-and-forget call after processing in `routers/transcripts.py` (the upload-and-process path)
- [x] 4.3 Add error handling so LLM failures are logged but never surface to the user or block the pipeline

## 5. Backend — Manual Regeneration Endpoint

- [x] 5.1 Add `POST /api/sessions/{session_id}/generate-name` endpoint in `routers/sessions.py` that triggers name generation and updates the session name (overrides current name regardless of pattern)
- [x] 5.2 Return 400 error if session has no transcript segments

## 6. Backend — Campaign Start Number

- [x] 6.1 Update campaign CRUD endpoints to accept and persist `session_start_number` field
- [x] 6.2 Update `CampaignCreate` and `CampaignUpdate` Pydantic models to include `session_start_number`

## 7. Frontend — Campaign Settings

- [x] 7.1 Add `session_start_number` input field to campaign create/edit form with label "First session number" and default value 0

## 8. Frontend — Session Creation

- [x] 8.1 Make the session name field optional in the session creation form (placeholder: "Auto-generated, e.g. Session 0")
- [x] 8.2 Update `api.ts` to handle optional session name and include `session_number` in session types

## 9. Frontend — Session Display

- [x] 9.1 Update `CampaignDashboard.svelte` to display session name (which now includes the number prefix) in session cards
- [x] 9.2 Update `SessionDetail.svelte` to show the session name as the primary heading and make it inline-editable
- [x] 9.3 Add a "Regenerate Name" button in the session detail view (visible for completed sessions) that calls the generate-name endpoint and refreshes the displayed name
