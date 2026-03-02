## Why

TaleKeeper sessions are currently named manually by users and identified only by database IDs and dates. There is no automatic session numbering (Session 0, Session 1, etc.) and no way for the system to generate meaningful session titles. For tabletop RPG groups, session numbering is a fundamental organizational convention, and a catchy title derived from what actually happened makes sessions easier to find and recall.

## What Changes

- Add a `session_number` integer field to sessions, auto-incremented per campaign
- Allow campaigns to configure a starting session number (e.g., start from Session 5 if migrating from another tool)
- After transcription completes, use the configured LLM to generate a short, catchy session title from the transcript content
- Auto-apply the generated name in the format "Session N: Catchy Title" (e.g., "Session 3: The Dragon's Lair")
- Allow users to edit the auto-generated name afterward
- Display session numbers in the campaign dashboard and session detail views

## Capabilities

### New Capabilities
- `session-naming`: LLM-based session name generation from transcript content, including the prompt design, auto-application after transcription, and editability

### Modified Capabilities
- `campaign-management`: Add session numbering (auto-increment per campaign, configurable starting number, display in dashboard and session views)

## Impact

- **Database**: New `session_number` column on `sessions` table; new `session_start_number` column on `campaigns` table
- **Backend**: New LLM prompt + endpoint for name generation; modified session creation to assign next number; modified processing pipeline to trigger naming after transcription
- **Frontend**: Updated session display to show numbered titles; campaign setting for starting session number; editable session name field
- **LLM integration**: Reuses existing `llm_client.py` infrastructure with a new prompt template
- **Existing sessions**: Migration needed to backfill session numbers based on creation date order within each campaign
