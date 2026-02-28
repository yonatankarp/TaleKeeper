## Why

The current TaleKeeper UI works but has significant UX friction for the core DM workflow (record session, transcribe, assign speakers, generate summaries, export). Key issues: no visual orientation (no active sidebar indicator, no breadcrumbs), tedious one-by-one speaker assignment, no transcript search for long sessions, jarring browser `confirm()` dialogs, no loading feedback, and missing keyboard shortcuts. These improvements reduce clicks and confusion across every session.

## What Changes

- Add active page indicator to sidebar navigation
- Add "Continue Last Session" shortcut button on campaign dashboard
- Show persistent recording status badge in session header (visible across all tabs)
- Add text search/filter to transcript view
- Replace one-by-one speaker editing with batch assignment (edit all speakers at once, single save)
- Replace all browser `confirm()` dialogs with styled modal dialogs
- Add breadcrumb navigation trail (Campaigns > Campaign > Session)
- Add loading spinners to all page routes during data fetch
- Add elapsed time counter to summary generation progress
- Add keyboard navigation (arrow keys, Enter, Escape) to language dropdown
- Improve empty state messages with helpful guidance text
- Add form validation (required field highlighting) to campaign/session create forms
- Detect OS color scheme preference for initial theme default
- Show audio/summary availability badges on session cards
- Improve email sharing dialog (rename, backdrop close, visual distinction for readonly fields)
- Add keyboard shortcuts for tab switching (1-4 keys) in session detail

## Capabilities

### New Capabilities
- `ux-shared-components`: Reusable ConfirmDialog and Spinner components used across all pages
- `keyboard-shortcuts`: Keyboard navigation for session tabs and language dropdown

### Modified Capabilities
- `campaign-management`: Add "Continue Last Session" button, form validation, loading states, styled confirmations, session card badges, improved empty states
- `session-tabs`: Add recording status badge in header, keyboard shortcuts for tab switching
- `speaker-diarization`: Replace one-by-one editing with batch speaker assignment
- `transcription`: Add search/filter bar to transcript view, improved empty state
- `summary-generation`: Add elapsed time progress during generation, styled confirm for regenerate/delete
- `export-and-sharing`: Improve email dialog UX (rename, backdrop close, readonly styling)

## Impact

- **Frontend only** - all changes are in Svelte components and CSS, no backend modifications
- **Files affected**: All 5 route components, 7 existing components, 2 new shared components, theme utility, App.svelte
- **No breaking changes** - all improvements are additive or in-place replacements
- **No new dependencies** - uses existing Svelte 5 runes and CSS variables
