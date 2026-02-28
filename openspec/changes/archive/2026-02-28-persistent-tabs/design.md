## Context

SessionDetail.svelte renders tab content using `{#if activeTab === ...}` / `{:else if}` blocks. Switching tabs destroys the active component and mounts the new one. This is problematic because RecordingControls holds a MediaRecorder, WebSocket connection, and timer interval in component-local state — all of which are lost on unmount.

The four tabs are: recording, transcript, summaries, export.

## Goals / Non-Goals

**Goals:**
- Tab switching preserves all running processes (recording, WebSocket, timers)
- Single-file change to SessionDetail.svelte
- No child component modifications

**Non-Goals:**
- Cross-tab recording indicator (user switches back to recording tab to control it)
- Lifting recording state into a shared store or context
- Changes to any child component lifecycle or API

## Decisions

### Render all tabs, hide inactive with CSS

Replace the `{#if}`/`{:else if}` chain with four sibling `<div>` wrappers that are always rendered. Each wrapper uses Svelte's `class:hidden` directive tied to `activeTab`. A `.hidden { display: none }` CSS rule hides inactive tabs.

**Why this over conditional rendering:** Components stay mounted in the DOM, so MediaRecorder, WebSocket, and setInterval survive tab switches. No state management refactoring needed.

**Why this over a shared store:** A store would require extracting recording logic from RecordingControls into a separate module, adding complexity for a problem that CSS solves trivially.

### AudioPlayer remains conditionally rendered within its tab wrapper

The `{#if hasAudio}` guard on AudioPlayer stays — it's a data dependency (no audio file yet), not a tab visibility concern. It lives inside the always-mounted transcript tab wrapper.

## Risks / Trade-offs

- **All 4 components mounted simultaneously** → Negligible memory overhead. These are lightweight UI components with minimal DOM footprint.
- **Background components receive reactive updates** → TranscriptView's `$effect` will continue polling/updating while hidden. This is actually beneficial (live transcript updates persist). SummarySection and ExportSection do one-time loads on mount, so no ongoing cost.
- **AudioPlayer bind:this may be undefined when transcript tab is hidden** → No issue — `audioPlayer?.seekTo()` already uses optional chaining, and the user can only click transcript segments when the transcript tab is visible.
