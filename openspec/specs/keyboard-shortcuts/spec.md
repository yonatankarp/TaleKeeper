# Keyboard Shortcuts

## Purpose

Provide keyboard-driven navigation and interaction throughout the application, including tab switching shortcuts in the session detail view and keyboard navigation within dropdown components.

## Requirements

### Requirement: Session tab keyboard shortcuts
The system SHALL support keyboard shortcuts for switching between session detail tabs. Pressing keys 1-4 SHALL switch to the corresponding tab (1=Recording, 2=Transcript, 3=Summaries, 4=Export). Shortcuts MUST NOT trigger when focus is in an input, textarea, or select element.

#### Scenario: Switch tabs with number keys
- **WHEN** the DM is viewing a session detail and presses the "2" key (not in a text field)
- **THEN** the active tab switches to the Transcript tab

#### Scenario: Shortcuts suppressed in text fields
- **WHEN** the DM is typing in a text input and presses "1"
- **THEN** the character "1" is typed into the input field and the tab does not switch

#### Scenario: Tab shortcut hints visible
- **WHEN** the DM views the session detail tab bar
- **THEN** each tab shows a subtle shortcut number hint (e.g., "Recording 1", "Transcript 2")

### Requirement: Language dropdown keyboard navigation
The system SHALL support keyboard navigation in the language selection dropdown. Arrow keys SHALL move the highlight up/down, Enter SHALL select the highlighted option, and Escape SHALL close the dropdown.

#### Scenario: Navigate with arrow keys
- **WHEN** the language dropdown is open and the DM presses the down arrow key
- **THEN** the next language option is highlighted and scrolled into view

#### Scenario: Select with Enter
- **WHEN** a language option is highlighted in the dropdown and the DM presses Enter
- **THEN** that language is selected and the dropdown closes

#### Scenario: Close with Escape
- **WHEN** the language dropdown is open and the DM presses Escape
- **THEN** the dropdown closes without changing the selection
