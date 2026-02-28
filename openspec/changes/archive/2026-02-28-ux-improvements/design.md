## Context

TaleKeeper is a D&D session transcription app with a Svelte 5 frontend. The DM workflow (record → transcribe → assign speakers → summarize → export) requires frequent interaction across multiple pages and components. Current UX has friction: no navigation orientation, tedious speaker assignment, no search, jarring native dialogs, no loading feedback, and no keyboard shortcuts.

All 16 improvements are frontend-only. The backend API already supports everything needed - no new endpoints or data model changes required.

## Goals / Non-Goals

**Goals:**
- Reduce clicks and confusion across the core DM workflow
- Add visual orientation (sidebar highlight, breadcrumbs, loading states)
- Speed up repetitive tasks (batch speaker assignment, keyboard shortcuts, transcript search)
- Replace jarring browser dialogs with styled components
- Detect OS theme preference for better first-run experience

**Non-Goals:**
- Backend changes or new API endpoints
- Mobile-responsive layout (future work)
- Internationalization / i18n
- Accessibility audit beyond keyboard navigation for dropdowns and tabs
- New features beyond UX polish (no new functional capabilities)

## Decisions

### Shared components over inline duplication
Create reusable `ConfirmDialog` and `Spinner` components rather than duplicating dialog/spinner markup in each page. This keeps the codebase DRY and ensures consistent styling.

**Alternative considered:** Inline each dialog per component. Rejected because 6+ components need confirm dialogs and 5+ need loading spinners.

### Batch speaker assignment with parallel API calls
Replace one-by-one speaker editing with a form showing all speakers simultaneously. Save uses `Promise.all()` to update all speakers in parallel rather than sequential calls.

**Alternative considered:** Single batch API endpoint. Rejected because it requires backend changes and the existing per-speaker PUT endpoint works fine with parallel calls.

### Breadcrumbs via API fetch in App.svelte
App.svelte fetches campaign/session names when the route changes to populate breadcrumbs. This adds a small API call but avoids prop-drilling names through the component tree.

**Alternative considered:** Pass names up from child route components. Rejected because it requires adding callback props to every route component and complicates the routing layer.

### Recording badge via callback prop
RecordingControls exposes recording state to SessionDetail via an `onRecordingStateChange` callback. SessionDetail renders the badge in the header outside the tabs.

**Alternative considered:** Shared Svelte store. Rejected as over-engineering for a parent-child relationship.

### Keyboard shortcuts scoped to session detail
Tab-switching shortcuts (1-4) are only active in the session detail view and are suppressed when focus is in input/textarea/select elements.

**Alternative considered:** Global shortcut system. Rejected - only session detail needs shortcuts right now.

## Risks / Trade-offs

**Breadcrumb API calls on every route change** → Minimal impact since these are small GET requests for a single record. The campaign/session objects are likely already cached by the browser.

**Batch speaker save with Promise.all** → If one speaker update fails, others still succeed, leaving partial state. Mitigation: reload speakers after save regardless of partial failure, show error if any call fails.

**ConfirmDialog doesn't trap focus** → A full accessibility-compliant dialog requires focus trapping and return-focus-on-close. Current implementation uses backdrop click and Escape key but doesn't trap tab focus. Acceptable for now; can be enhanced later.

**Theme detection only on initial load** → OS theme changes after page load won't auto-switch the app theme. The user must toggle manually. This matches user expectation since they may deliberately pick a different theme.
