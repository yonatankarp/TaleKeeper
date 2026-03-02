# Router Tests

## Purpose

Provide integration test coverage for all backend API router endpoints.

## Requirements

### Requirement: Campaign router CRUD tests
The test suite SHALL include integration tests for all campaign endpoints: create, list, get, update, and delete. Tests SHALL use the httpx `client` fixture.

#### Scenario: Create a campaign
- **WHEN** POST `/api/campaigns` is called with `{"name": "Test Campaign"}`
- **THEN** the response status is 200 and the body contains the campaign with an `id` and the given name

#### Scenario: List campaigns
- **WHEN** GET `/api/campaigns` is called after creating two campaigns
- **THEN** the response contains a list of 2 campaigns

#### Scenario: Get a campaign by ID
- **WHEN** GET `/api/campaigns/{id}` is called with a valid ID
- **THEN** the response contains the campaign details

#### Scenario: Update a campaign
- **WHEN** PUT `/api/campaigns/{id}` is called with `{"name": "Updated"}`
- **THEN** the response contains the campaign with the updated name

#### Scenario: Delete a campaign
- **WHEN** DELETE `/api/campaigns/{id}` is called
- **THEN** the response contains `{"deleted": true}` and a subsequent GET returns 404

#### Scenario: Get campaign dashboard
- **WHEN** GET `/api/campaigns/{id}/dashboard` is called
- **THEN** the response contains `session_count`, `total_recorded_time`, and `most_recent_session_date`

### Requirement: Session router CRUD tests
The test suite SHALL include integration tests for all session endpoints: create, list, get, update, and delete.

#### Scenario: Create a session under a campaign
- **WHEN** POST `/api/campaigns/{campaign_id}/sessions` is called with a valid name and date
- **THEN** the response status is 200 and the body contains the session linked to the campaign

#### Scenario: List sessions for a campaign
- **WHEN** GET `/api/campaigns/{campaign_id}/sessions` is called
- **THEN** the response contains all sessions for that campaign

#### Scenario: Get a session by ID
- **WHEN** GET `/api/sessions/{id}` is called with a valid ID
- **THEN** the response contains the session details

#### Scenario: Update a session
- **WHEN** PUT `/api/sessions/{id}` is called with `{"name": "Renamed"}`
- **THEN** the response contains the updated session

#### Scenario: Delete a session
- **WHEN** DELETE `/api/sessions/{id}` is called
- **THEN** the response contains `{"deleted": true}`

### Requirement: Speaker router tests
The test suite SHALL include integration tests for speaker listing, updating, segment reassignment, merge, speaker suggestions, and re-diarize (initial SSE response only).

#### Scenario: List speakers for a session
- **WHEN** GET `/api/sessions/{session_id}/speakers` is called
- **THEN** the response contains all speakers for that session

#### Scenario: Update a speaker
- **WHEN** PUT `/api/speakers/{id}` is called with `{"player_name": "Bob"}`
- **THEN** the response contains the speaker with the updated player_name

#### Scenario: Reassign a segment to a different speaker
- **WHEN** PUT `/api/transcript-segments/{segment_id}/speaker` is called with a valid speaker_id
- **THEN** the response contains the updated segment

#### Scenario: Bulk reassign segments
- **WHEN** PUT `/api/sessions/{session_id}/reassign-segments` is called with segment IDs and a target speaker
- **THEN** the response contains `{"updated": N}` where N matches the number of segments

#### Scenario: Get speaker suggestions from roster
- **WHEN** GET `/api/sessions/{session_id}/speaker-suggestions` is called
- **THEN** the response contains roster entries for the session's campaign

### Requirement: Transcript router tests
The test suite SHALL include integration tests for transcript retrieval.

#### Scenario: Get transcript for a session with segments
- **WHEN** GET `/api/sessions/{session_id}/transcript` is called for a session with seeded segments
- **THEN** the response contains the segments with speaker info, ordered by start_time

#### Scenario: Get transcript for empty session
- **WHEN** GET `/api/sessions/{session_id}/transcript` is called for a session with no segments
- **THEN** the response is an empty list

### Requirement: Summary router tests
The test suite SHALL include integration tests for summary CRUD and the LLM status endpoint. Summary generation endpoints SHALL mock the LLM client.

#### Scenario: List summaries for a session
- **WHEN** GET `/api/sessions/{session_id}/summaries` is called
- **THEN** the response contains all summaries for that session

#### Scenario: Generate a full summary
- **WHEN** POST `/api/sessions/{session_id}/generate-summary` is called with `{"type": "full"}` and the LLM client is mocked
- **THEN** the response contains a summary with type "full" and non-empty content

#### Scenario: Get LLM status
- **WHEN** GET `/api/llm/status` is called with a mocked LLM health check
- **THEN** the response contains `{"status": "ok"}` or an error message

#### Scenario: Update a summary
- **WHEN** PUT `/api/summaries/{id}` is called with `{"content": "New content"}`
- **THEN** the response contains the summary with updated content

#### Scenario: Delete a summary
- **WHEN** DELETE `/api/summaries/{id}` is called
- **THEN** the response contains `{"deleted": true}`

### Requirement: Roster router CRUD tests
The test suite SHALL include integration tests for all roster endpoints: create, list, update, and delete.

#### Scenario: Create a roster entry
- **WHEN** POST `/api/campaigns/{campaign_id}/roster` is called with player and character names
- **THEN** the response contains the roster entry with an `id`

#### Scenario: List roster entries
- **WHEN** GET `/api/campaigns/{campaign_id}/roster` is called
- **THEN** the response contains all roster entries for that campaign

#### Scenario: Update a roster entry
- **WHEN** PUT `/api/roster/{id}` is called with `{"character_name": "Gandalf"}`
- **THEN** the response contains the entry with the updated character_name

#### Scenario: Delete a roster entry
- **WHEN** DELETE `/api/roster/{id}` is called
- **THEN** the response contains `{"deleted": true}`

### Requirement: Export router tests
The test suite SHALL include integration tests for PDF export, text export, transcript export, and email content. PDF generation SHALL mock WeasyPrint.

#### Scenario: Export summary as PDF
- **WHEN** GET `/api/summaries/{id}/export/pdf` is called with a mocked WeasyPrint
- **THEN** the response has content-type `application/pdf` and non-empty body

#### Scenario: Export summary as text
- **WHEN** GET `/api/summaries/{id}/export/text` is called
- **THEN** the response has content-type `text/plain` and contains the summary text

#### Scenario: Export session transcript as text
- **WHEN** GET `/api/sessions/{session_id}/export/transcript` is called for a session with segments
- **THEN** the response contains the formatted transcript text

#### Scenario: Get email content for a summary
- **WHEN** GET `/api/summaries/{id}/email-content` is called
- **THEN** the response contains `subject`, `body`, and `meta` fields

### Requirement: Settings router tests
The test suite SHALL include integration tests for reading and updating settings.

#### Scenario: Get settings (empty state)
- **WHEN** GET `/api/settings` is called on a fresh database
- **THEN** the response is an object (may be empty)

#### Scenario: Update and retrieve settings
- **WHEN** PUT `/api/settings` is called with `{"settings": {"llm_base_url": "http://localhost:11434/v1"}}`
- **THEN** a subsequent GET `/api/settings` returns the saved value

#### Scenario: Passwords are masked in settings response
- **WHEN** a setting key contains "password" or "key" and GET `/api/settings` is called
- **THEN** the value is masked (not returned in plaintext)

### Requirement: Voice signature router tests
The test suite SHALL include integration tests for generating, listing, and deleting voice signatures. Generation SHALL mock the speechbrain encoder.

#### Scenario: List voice signatures for a campaign
- **WHEN** GET `/api/campaigns/{campaign_id}/voice-signatures` is called
- **THEN** the response contains a list of signatures without embedding data

#### Scenario: Delete a voice signature
- **WHEN** DELETE `/api/voice-signatures/{id}` is called
- **THEN** the response contains `{"deleted": true}`

### Requirement: Image router tests
The test suite SHALL include integration tests for listing images, deleting images, image health check, and scene crafting. Image generation SSE SHALL be tested for correct content-type.

#### Scenario: List images for a session
- **WHEN** GET `/api/sessions/{session_id}/images` is called
- **THEN** the response contains a list of images for that session

#### Scenario: Delete an image
- **WHEN** DELETE `/api/images/{id}` is called
- **THEN** the response status is 204

#### Scenario: Get image health status
- **WHEN** GET `/api/settings/image-health` is called with a mocked image client
- **THEN** the response contains `status` field

#### Scenario: Craft scene description
- **WHEN** POST `/api/sessions/{session_id}/craft-scene` is called with a mocked LLM
- **THEN** the response contains a `scene_description` string

### Requirement: Recording router audio upload test
The test suite SHALL include an integration test for audio file upload. WebSocket recording and SSE processing endpoints are excluded from this phase.

#### Scenario: Upload an audio file
- **WHEN** POST `/api/sessions/{session_id}/upload-audio` is called with a multipart file
- **THEN** the response contains `{"audio_path": ...}` and the file is saved

### Requirement: Error handling tests for invalid IDs
The test suite SHALL verify that endpoints return appropriate HTTP error codes for nonexistent resources.

#### Scenario: GET nonexistent campaign returns 404
- **WHEN** GET `/api/campaigns/99999` is called
- **THEN** the response status is 404

#### Scenario: GET nonexistent session returns 404
- **WHEN** GET `/api/sessions/99999` is called
- **THEN** the response status is 404

#### Scenario: DELETE nonexistent roster entry returns 404
- **WHEN** DELETE `/api/roster/99999` is called
- **THEN** the response status is 404
