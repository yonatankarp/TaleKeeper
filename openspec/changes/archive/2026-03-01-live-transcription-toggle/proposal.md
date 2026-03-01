## Why

Live transcription during recording (`_run_transcription_on_chunk`) produces low-quality preview segments that confuse users — they look like the final transcript but are much worse quality. Users don't understand why the transcript changes after recording stops. The feature should be opt-in per campaign, disabled by default, and when enabled the transcript view should clearly communicate that visible segments are preliminary while full processing is underway.

## What Changes

- Add a `live_transcription` boolean setting to campaigns (default: off)
- Gate incremental WebSocket transcription on the campaign setting — when off, no segments appear during recording
- When live transcription is enabled and audio is still processing after recording stops, show an explicit "preview" notice in the transcript view distinguishing preliminary segments from the final result
- Add toggle to campaign create/edit forms

## Capabilities

### New Capabilities

_(none — this is configuration of existing behavior)_

### Modified Capabilities

- `campaign-management`: Add `live_transcription` boolean field (default false) to campaign CRUD — creation, editing, validation, and persistence
- `transcription`: Gate real-time transcription during recording on the campaign's `live_transcription` setting; when enabled and audio is still processing, transcript view must show a "preview" banner explaining segments are preliminary
- `audio-capture`: After recording stops, session transitions to `audio_ready` status (already implemented); no change to capture behavior itself

## Impact

- **DB schema**: Add `live_transcription` column to `campaigns` table + migration
- **Backend**: `recording.py` WS handler reads campaign setting before running incremental transcription; `campaigns.py` models updated
- **Frontend**: `CampaignList.svelte` gains a toggle; `TranscriptView.svelte` gains a preview banner when live segments exist during processing
