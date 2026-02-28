## 1. Shared Components

- [x] 1.1 Create `ConfirmDialog.svelte` component with backdrop, Escape key, title/message/confirm/cancel props
- [x] 1.2 Create `Spinner.svelte` component with configurable size and theme-aware colors

## 2. Navigation & Orientation

- [x] 2.1 Add active page indicator to `Sidebar.svelte` — track currentPath, apply active class with accent left-border
- [x] 2.2 Add breadcrumb navigation to `App.svelte` — fetch campaign/session names, render clickable trail
- [x] 2.3 Add loading states to all 5 route pages (CampaignList, CampaignDashboard, SessionDetail, RosterPage, SettingsPage) using Spinner

## 3. Campaign Dashboard Improvements

- [x] 3.1 Add "Continue Last Session" button to CampaignDashboard — links to most recent session, changes "New Session" to "Start First Session" when empty
- [x] 3.2 Add audio badge to session cards on CampaignDashboard — show "Audio" badge when session has audio_path
- [x] 3.3 Improve empty state message in CampaignDashboard sessions list

## 4. Session Detail Improvements

- [x] 4.1 Add recording status badge to SessionDetail header — pass onRecordingStateChange callback from RecordingControls, render pulsing dot + elapsed time + REC/PAUSED label
- [x] 4.2 Add keyboard shortcuts (1-4) for tab switching in SessionDetail — suppress when in input/textarea/select
- [x] 4.3 Add shortcut number hints to tab labels

## 5. Transcript Improvements

- [x] 5.1 Add search/filter bar to TranscriptView — search state, filtered segments derived, match count, clear button
- [x] 5.2 Improve transcript empty state messages (no transcript, no matches)

## 6. Speaker Panel Batch Assignment

- [x] 6.1 Rewrite SpeakerPanel to batch mode — show all speakers simultaneously with inputs and roster suggestions, "Edit All" toggle, "Save All" with Promise.all

## 7. Styled Confirmation Dialogs

- [x] 7.1 Replace confirm() in CampaignList with ConfirmDialog
- [x] 7.2 Replace confirm() in CampaignDashboard with ConfirmDialog (session delete, campaign delete)
- [x] 7.3 Replace confirm() in RosterPage with ConfirmDialog
- [x] 7.4 Replace confirm() in SummarySection with ConfirmDialog (regenerate, delete)

## 8. Summary Generation Progress

- [x] 8.1 Add elapsed time counter and Spinner to SummarySection generate buttons — start/stop timer on generation

## 9. Language Dropdown Keyboard Navigation

- [x] 9.1 Add arrow key, Enter, Escape handling to LanguageSelect — track highlightedIndex, scroll into view, reset on filter change

## 10. Form Validation

- [x] 10.1 Add required-field validation to CampaignList create form — red border + error message on empty name
- [x] 10.2 Add required-field validation to CampaignDashboard session create form

## 11. Theme & Styling

- [x] 11.1 Add OS color scheme detection to theme.svelte.ts — use prefers-color-scheme media query as fallback when no localStorage preference

## 12. Email Dialog UX

- [x] 12.1 Rename "Prepare Email" to "Share via Email" in ExportSection
- [x] 12.2 Wrap email dialog in backdrop overlay — close on backdrop click
- [x] 12.3 Add visual distinction for readonly fields (reduced opacity, different background)

## 13. Empty States

- [x] 13.1 Improve CampaignList empty state with guidance text
- [x] 13.2 Improve RosterPage empty state with guidance text
- [x] 13.3 Improve SummarySection empty state with guidance text
