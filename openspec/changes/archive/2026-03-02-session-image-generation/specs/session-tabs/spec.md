## MODIFIED Requirements

### Requirement: Tab labels use D&D-themed terminology
The session detail view SHALL use D&D-themed names for its tab labels. The tab previously labeled "Transcript" SHALL be labeled "Chronicle". The tab previously labeled "Summaries" SHALL be labeled "Tales". The new illustrations tab SHALL be labeled "Visions".

#### Scenario: Visions tab is displayed
- **WHEN** user views the session detail page
- **THEN** the 5th tab SHALL be labeled "Visions" with keyboard shortcut `5`

## ADDED Requirements

### Requirement: Five-tab navigation with Illustrations tab
The session detail view SHALL display five tabs: Recording, Chronicle, Tales, Export, and Visions. The Visions tab SHALL be the 5th tab with keyboard shortcut `5`. The tab SHALL use an appropriate icon consistent with the existing tab icon style. The Visions tab content SHALL remain mounted in the DOM when switching tabs, following the existing pattern for preserving component state.

#### Scenario: Keyboard shortcut 5 switches to Visions tab
- **WHEN** user presses the `5` key while not focused on an input/textarea/select
- **THEN** the active tab SHALL switch to the Visions tab

#### Scenario: Visions tab preserves state when switching away
- **WHEN** user is on the Visions tab viewing images and switches to another tab then back
- **THEN** the Visions tab content SHALL be in the same state (loaded images, scroll position, any in-progress prompt editing)
