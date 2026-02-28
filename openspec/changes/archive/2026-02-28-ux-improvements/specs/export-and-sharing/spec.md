## MODIFIED Requirements

### Requirement: Email summary content generation
The system SHALL generate email-ready content for each summary, including a subject line and formatted body text. The email dialog MUST be titled "Share via Email" (not "Prepare Email"). The dialog MUST appear as a modal overlay that closes when clicking the backdrop. Readonly fields (subject, body) MUST be visually distinct from editable fields with reduced opacity and different background color.

#### Scenario: Share via email dialog
- **WHEN** the DM clicks "Share via Email" on a POV summary
- **THEN** a modal overlay appears with pre-filled subject and body (visually distinct as readonly), a "Copy Subject" and "Copy Body" button, and an optional direct send form

#### Scenario: Close email dialog by clicking backdrop
- **WHEN** the email dialog is open and the DM clicks outside the dialog
- **THEN** the dialog closes

#### Scenario: Readonly fields visually distinct
- **WHEN** the email dialog is open
- **THEN** the subject and body fields appear with reduced opacity and a darker background to indicate they are readonly templates
