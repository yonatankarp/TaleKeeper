# UX Shared Components

## Purpose

Provide reusable UI components and patterns used across the application, including styled confirmation dialogs, loading spinners, and consistent loading states on all page routes.

## Requirements

### Requirement: Styled confirmation dialog
The system SHALL provide a reusable ConfirmDialog component that replaces browser-native `confirm()` dialogs. The dialog MUST display a title, descriptive message, and Cancel/Confirm buttons. The confirm button MUST be styled with danger coloring for destructive actions. The dialog MUST close when clicking the backdrop or pressing Escape.

#### Scenario: Delete confirmation uses styled dialog
- **WHEN** the DM triggers a destructive action (delete campaign, delete session, remove roster entry, delete summary)
- **THEN** a styled modal dialog appears with the item context (e.g., "Delete Campaign"), a warning message, and Cancel/Delete buttons

#### Scenario: Dialog closes on backdrop click
- **WHEN** a confirmation dialog is open and the DM clicks outside the dialog
- **THEN** the dialog closes without performing the action

#### Scenario: Dialog closes on Escape key
- **WHEN** a confirmation dialog is open and the DM presses Escape
- **THEN** the dialog closes without performing the action

### Requirement: Loading spinner component
The system SHALL provide a reusable Spinner component for indicating loading state. The spinner MUST support configurable size and use theme-aware colors.

#### Scenario: Page loading shows spinner
- **WHEN** a page route is loading data from the API
- **THEN** a spinner with loading text is displayed until data arrives

### Requirement: Loading states on all page routes
The system SHALL display a loading spinner on every page route (campaign list, campaign dashboard, session detail, roster, settings) while initial data is being fetched from the API.

#### Scenario: Campaign list shows loading state
- **WHEN** the DM navigates to the campaigns page
- **THEN** a spinner with "Loading campaigns..." is shown until the campaign list loads

#### Scenario: Session detail shows loading state
- **WHEN** the DM navigates to a session
- **THEN** a spinner with "Loading session..." is shown until session data loads
