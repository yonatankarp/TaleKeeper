# UX Improvements Design

## Overview

Sixteen UX improvements for TaleKeeper, organized by impact tier. All changes are frontend-only (Svelte components + CSS).

## High Impact

### 1. Sidebar active page indicator
Highlight the currently active campaign/page in the sidebar. Compare current hash path against each campaign link and settings link. Apply an `active` CSS class with accent-colored left border and subtle background.

### 2. Continue Last Session button
On CampaignDashboard, show a "Continue Last Session" button next to "New Session" when sessions exist. Links to the most recent session (first in the sorted list). When no sessions exist, show "Start First Session" instead of "New Session".

### 3. Recording status badge in session header
Add a persistent recording indicator (red pulsing dot + elapsed time) in the SessionDetail header, outside the tab bar. Visible from any tab. Reads recording state from RecordingControls via a shared reactive signal or callback.

### 4. Transcript search/filter
Add a text input above the transcript segment list. Filter segments client-side by matching against segment text (case-insensitive). Show match count. Clear button to reset.

### 5. Batch speaker assignment
Replace one-by-one speaker editing with a batch form. Show all speakers at once, each with player name + character name inputs and roster quick-select. Single "Save All" button updates all speakers in one action.

### 6. Styled confirmation dialogs
Replace browser `confirm()` with a custom modal component. Show item name, warning text, and styled Cancel/Delete buttons. Red-colored delete button. Used for campaign delete, session delete, roster remove, summary regenerate.

## Medium Impact

### 7. Breadcrumbs
Add a breadcrumb bar at the top of main content. Shows navigation path: Campaigns > [Campaign Name] > [Session Name]. Each segment is a clickable link. Only shown on campaign, roster, and session pages.

### 8. Loading states
Add a simple spinner/skeleton when fetching data. Apply to: CampaignList, CampaignDashboard, SessionDetail, RosterPage, SettingsPage. Use a `loading` flag that's true until the initial API call resolves.

### 9. Summary generation progress
Replace static "Generating..." text with an animated spinner and elapsed time counter. Start a timer when generation begins, stop when complete. Show "Generating summary... (12s)" with a spinning icon.

### 10. Language dropdown keyboard navigation
Add arrow key up/down to move through filtered options, Enter to select, Escape to close. Track a `highlightedIndex` state that updates on keydown. Scroll highlighted option into view.

### 11. Better empty states
Replace terse "No X yet" messages with helpful guidance:
- Campaign list: "Create your first campaign to start recording sessions"
- Session list: "Create a session to begin recording your next game"
- Transcript: "Start recording or upload audio to generate a transcript"
- Summaries: "Generate a summary after your session is transcribed"

### 12. Form validation
Add required field validation to campaign create/edit and session create forms. Show red border and "Required" message on empty name fields. Disable submit button until required fields are filled.

## Lower Priority

### 13. System theme detection
Default theme to OS preference via `window.matchMedia('(prefers-color-scheme: dark)')`. Only apply if no localStorage preference exists. Existing user preference takes priority.

### 14. Session card context
Add recording duration and summary availability to session cards on the campaign dashboard. Show "2h 15m" if audio exists, "Summary available" badge if summaries exist. Requires the session list API to include these fields (or derive from existing data).

### 15. Email dialog UX
Rename "Prepare Email" to "Share via Email". Make the flow clearer: show a preview of the email content, then allow editing before send. Close modal on backdrop click. Add visual distinction between readonly preview and editable fields.

### 16. Keyboard shortcuts
Add shortcuts for core actions: Space for record/pause (when on recording tab), 1-4 for tab switching in session detail, Escape to close modals/dialogs. Register via window keydown listener with appropriate guards (not in input fields).
