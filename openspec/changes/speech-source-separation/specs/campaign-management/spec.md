## ADDED Requirements

### Requirement: Source separation opt-in per campaign
Each campaign SHALL have a `source_separation_enabled` boolean field (stored as `INTEGER NOT NULL DEFAULT 0`). The campaign creation and edit forms SHALL include a toggle for this setting labelled "Enable source separation" with a visible warning that it adds significant processing time (~0.5–1× real-time per session). The setting MUST default to disabled for all campaigns, including existing ones after migration.

#### Scenario: Source separation disabled by default
- **WHEN** a new campaign is created without explicitly enabling source separation
- **THEN** `source_separation_enabled` is set to 0 and diarization runs without separation

#### Scenario: Enable source separation for a campaign
- **WHEN** the DM edits a campaign and enables the source separation toggle
- **THEN** `source_separation_enabled` is saved as 1 and subsequent diarization runs for that campaign include the separation stage

#### Scenario: Processing time warning shown
- **WHEN** the DM enables the source separation toggle in the campaign form
- **THEN** a visible warning is displayed explaining that source separation adds roughly 0.5–1× the session length in extra processing time

#### Scenario: Existing campaigns default to separation disabled
- **WHEN** the database migration adds the `source_separation_enabled` column
- **THEN** all existing campaign rows have `source_separation_enabled = 0` and their diarization behaviour is unchanged
