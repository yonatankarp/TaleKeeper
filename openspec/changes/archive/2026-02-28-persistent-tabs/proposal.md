# Persistent Tabs

## Why

Switching tabs in SessionDetail destroys and recreates components via `{#if}`/`{:else if}` conditional rendering. This kills active recording (MediaRecorder, WebSocket, timer) when the user navigates to the transcript tab to check live transcription.

## What Changes

- Replace conditional rendering with CSS visibility toggling in SessionDetail
- All tab content components remain mounted; inactive tabs hidden with `display: none`
- Recording UI stays alive in background when viewing other tabs

## Capabilities

### New Capabilities
- `session-tabs`: Persistent tab rendering that preserves component state

### Modified Capabilities
- None

## Impact

- Single file change: `frontend/src/routes/SessionDetail.svelte`
- No changes to child components
- No new stores, contexts, or state management
