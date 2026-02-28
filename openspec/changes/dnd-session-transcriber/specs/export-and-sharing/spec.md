## ADDED Requirements

### Requirement: PDF export of summaries
The system SHALL export session summaries as PDF documents using WeasyPrint. The PDF MUST include the session name, date, campaign name, and the summary content with clean formatting.

#### Scenario: Export full session summary as PDF
- **WHEN** the DM clicks "Export PDF" on a session's full summary
- **THEN** a PDF file is downloaded containing the session name, date, campaign, and the narrative summary, formatted with readable typography

#### Scenario: Export a POV summary as PDF
- **WHEN** the DM clicks "Export PDF" on a specific character's POV summary
- **THEN** a PDF is downloaded containing the character name, player name, session details, and the POV summary

### Requirement: Text export of summaries
The system SHALL export summaries as plain text files. The text MUST include a header with session metadata followed by the summary content.

#### Scenario: Export as text file
- **WHEN** the DM clicks "Export Text" on a summary
- **THEN** a `.txt` file is downloaded with session metadata as a header and the summary content as plain text

### Requirement: Copy summary to clipboard
The system SHALL allow the DM to copy any summary's content to the system clipboard with a single click.

#### Scenario: Copy to clipboard
- **WHEN** the DM clicks "Copy to Clipboard" on a summary
- **THEN** the summary text is copied to the clipboard and a confirmation toast is shown

### Requirement: Batch export of all POV summaries
The system SHALL allow the DM to export all POV summaries for a session in a single action, producing one file per character.

#### Scenario: Batch export as PDFs
- **WHEN** the DM clicks "Export All POV Summaries" for a session with 4 characters
- **THEN** 4 PDF files are downloaded (or a single ZIP containing 4 PDFs), each named with the character name (e.g., `thorin-pov-session-12.pdf`)

### Requirement: Email summary content generation
The system SHALL generate email-ready content for each summary, including a subject line and formatted body text that the DM can copy into their email client.

#### Scenario: Generate email content for a POV summary
- **WHEN** the DM clicks "Prepare Email" on Thorin's POV summary
- **THEN** the system shows a preview with a pre-filled subject line (e.g., "Session 12 - Thorin's Recap") and the POV summary formatted as email body text, with a "Copy Subject" and "Copy Body" button

### Requirement: Direct email sending
The system SHALL optionally send emails directly to players if the DM has configured an email service. Email configuration MUST support SMTP settings (host, port, username, password, sender address). The system MUST NOT require email configuration — it is an optional feature.

#### Scenario: Configure email settings
- **WHEN** the DM enters SMTP settings (host, port, credentials, sender address) in the settings page
- **THEN** the settings are saved and a test email can be sent to verify the configuration

#### Scenario: Send POV summary via email
- **WHEN** the DM has email configured and clicks "Send Email" on a POV summary, entering the player's email address
- **THEN** the system sends an email with the POV summary to the specified address and shows a success confirmation

#### Scenario: Send without email configured
- **WHEN** the DM clicks "Send Email" but has not configured email settings
- **THEN** the system prompts the DM to configure email settings in the settings page, or suggests using "Prepare Email" for copy-paste instead

#### Scenario: Email sending fails
- **WHEN** an email fails to send (SMTP error, invalid address)
- **THEN** the system displays an error message with the failure reason and the summary content remains available for manual copy-paste

### Requirement: Transcript export
The system SHALL allow the DM to export the full transcript of a session as a text file, with speaker labels and timestamps.

#### Scenario: Export transcript
- **WHEN** the DM clicks "Export Transcript" on a completed session
- **THEN** a text file is downloaded containing the full transcript with timestamps and speaker names (e.g., `[00:12:30] Thorin (Alex): I search the room for hidden doors.`)
