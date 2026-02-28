## Why

SessionDetail uses conditional rendering (`{#if}`) for tab content, which destroys and recreates components on tab switch. This kills active recording (MediaRecorder, WebSocket, timer) when navigating to the transcript tab. Users need to check live transcription while recording without interrupting the session.

## What Changes

- Replace `{#if}`/`{:else if}` conditional rendering in SessionDetail with CSS visibility toggling (`display: none`) so all tab components remain mounted
- Inactive tab content is hidden visually but stays alive in the DOM
- No changes to child components (RecordingControls, TranscriptView, SummarySection, ExportSection)

## Capabilities

### New Capabilities

None — this is a rendering strategy change within existing UI, not a new capability.

### Modified Capabilities

None — no spec-level behavior changes. All existing capabilities (audio-capture, transcription, etc.) retain their requirements. This change only affects how the session view mounts/unmounts tab components.

## Impact

- **Code**: `frontend/src/routes/SessionDetail.svelte` — tab content rendering logic and CSS
- **Behavior**: All 4 tab components stay mounted simultaneously (negligible memory overhead). Transcript live-updates continue in background. Summary/export tabs retain state across switches.
- **No API, dependency, or backend changes.**
