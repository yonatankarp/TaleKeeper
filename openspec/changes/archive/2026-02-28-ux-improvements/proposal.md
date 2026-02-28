# UX Improvements

## Why

The frontend lacks polish for a smooth DM workflow — no loading states, browser-native confirm dialogs, no breadcrumbs, no keyboard navigation, and poor empty states.

## What Changes

- Add ConfirmDialog and Spinner shared components
- Add sidebar active page indicator
- Add "Continue Last Session" button to campaign dashboard
- Show recording status badge in session header
- Add transcript search/filter
- Batch speaker assignment with roster quick-picks
- Replace browser confirm() with styled ConfirmDialog
- Add breadcrumb navigation
- Add loading spinners to all route pages
- Add elapsed time to summary generation
- Add keyboard navigation to language dropdown
- Improve empty state messages
- Add form validation for required name fields
- Detect OS color scheme preference
- Show audio badge on session cards
- Improve email sharing dialog UX
- Add keyboard shortcuts for tab switching (1-4)

## Capabilities

### New Capabilities
- `ux-shared-components`: ConfirmDialog, Spinner reusable components
- `keyboard-shortcuts`: Number key tab switching in session detail

### Modified Capabilities
- `campaign-management`: Loading states, confirm dialogs, form validation, empty states
- `speaker-diarization`: Batch editing, roster suggestions
- `transcription`: Search/filter, recording badge
- `summary-generation`: Elapsed time progress
- `export-and-sharing`: Email dialog improvements

## Impact

- Frontend only — all Svelte components and routes
- No backend changes
