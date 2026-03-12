## ADDED Requirements

### Requirement: Import transcript from Gemini PDF
The system SHALL accept a PDF file upload for a session and populate that session's transcript and speaker data from a Gemini-exported meeting transcript. The import MUST clear any existing transcript segments and speakers before writing the imported content. The session status SHALL be set to `completed` after a successful import, regardless of its prior status.

#### Scenario: Successful import populates transcript
- **WHEN** the user uploads a valid Gemini PDF for a session
- **THEN** the session's transcript segments and speakers are populated from the PDF content and the session status becomes `completed`

#### Scenario: Import clears existing transcript
- **WHEN** a session already has an audio-derived transcript and the user imports a Gemini PDF
- **THEN** the existing segments and speakers are deleted and replaced with the imported content

#### Scenario: Session with no prior audio can be imported
- **WHEN** a session in `draft` status (no audio) receives a Gemini PDF import
- **THEN** the import succeeds and the session reaches `completed` without any audio file

### Requirement: Parse Gemini transcript format
The system SHALL parse the Gemini AI meeting notes PDF format, where each speaker turn consists of a speaker name and timestamp on a single line (separated by two or more spaces), followed by the speaker's dialogue on the subsequent line(s). The system SHALL locate the "Transcript" section heading in the PDF and parse only that section; if no heading is found, the entire document text SHALL be parsed.

#### Scenario: Parse speaker turns with timestamps
- **WHEN** the PDF contains lines like `Alice  0:05:30` followed by dialogue text
- **THEN** the imported segment has speaker name "Alice", start_time 330.0 seconds, and the dialogue as its text

#### Scenario: Preamble before transcript section is ignored
- **WHEN** the PDF contains a meeting summary and action items before the "Transcript" heading
- **THEN** only content after the "Transcript" heading is parsed into segments

#### Scenario: Timestamp formats supported
- **WHEN** the PDF contains timestamps in `M:SS` format (e.g., `1:23`) or `H:MM:SS` format (e.g., `1:02:03`)
- **THEN** both are correctly converted to float seconds (83.0 and 3723.0 respectively)

#### Scenario: Multi-line dialogue joined
- **WHEN** a speaker's turn spans multiple consecutive lines before the next speaker header
- **THEN** all lines are joined with a space into a single segment's text

### Requirement: End-time derivation for imported segments
The system SHALL set each imported segment's `end_time` to the `start_time` of the following segment. For the final segment, the system SHALL use `start_time + 30.0` seconds as the `end_time`.

#### Scenario: End time from next segment
- **WHEN** speaker A's turn starts at 10s and speaker B's turn starts at 75s
- **THEN** speaker A's segment has end_time of 75.0

#### Scenario: Last segment end time estimate
- **WHEN** the final segment in the transcript has start_time of 300.0
- **THEN** its end_time is 330.0

### Requirement: Speaker creation from imported names
The system SHALL create one `speakers` row per unique speaker name found in the imported PDF. The speaker's `diarization_label` and `player_name` SHALL both be set to the name as it appears in the PDF, so the name is displayed immediately without requiring manual assignment. Users MAY subsequently reassign speakers to roster entries via the speaker panel.

#### Scenario: Unique speakers created
- **WHEN** a PDF contains turns from "Dungeon Master", "Alice", and "Bob"
- **THEN** three speaker rows are created for the session, with those names as both diarization_label and player_name

#### Scenario: Duplicate speaker names deduplicated
- **WHEN** the PDF contains multiple turns from the same speaker
- **THEN** only one speaker row is created for that name

### Requirement: Import validation and error handling
The system SHALL reject non-PDF uploads with an HTTP 400 error. The system SHALL return HTTP 400 if the uploaded PDF contains no extractable text (e.g., a scanned image PDF). The system SHALL return HTTP 400 if no valid speaker turns are found after parsing. The system SHALL return HTTP 404 if the target session does not exist.

#### Scenario: Non-PDF file rejected
- **WHEN** the user uploads a `.docx` or `.txt` file to the import endpoint
- **THEN** the server returns HTTP 400 with a message indicating only PDF files are supported

#### Scenario: Image-only PDF rejected
- **WHEN** the user uploads a scanned PDF with no extractable text
- **THEN** the server returns HTTP 400 with a message indicating no text was found in the PDF

#### Scenario: PDF with no transcript turns rejected
- **WHEN** the user uploads a PDF that contains text but no recognizable speaker turns
- **THEN** the server returns HTTP 400 with a message indicating no transcript content was found

#### Scenario: Non-existent session returns 404
- **WHEN** the import endpoint is called with a session_id that does not exist
- **THEN** the server returns HTTP 404

### Requirement: Import Transcript UI button
The system SHALL provide an "Import Transcript" button in the session recording panel, alongside the existing "Upload Audio" option. The button SHALL open a file picker accepting `.pdf` files only. The UI SHALL show an in-progress indicator while the import is running and display a success or error message upon completion.

#### Scenario: Import button visible in recording panel
- **WHEN** the user opens a session's recording tab
- **THEN** an "Import Transcript" button is visible alongside the audio upload controls

#### Scenario: File picker accepts only PDF
- **WHEN** the user clicks "Import Transcript"
- **THEN** the OS file picker opens filtered to `.pdf` files

#### Scenario: In-progress state shown during import
- **WHEN** the user selects a PDF and the import is in progress
- **THEN** an "Importing transcript…" indicator is shown and other session controls are disabled

#### Scenario: Success feedback after import
- **WHEN** the import completes successfully
- **THEN** the session reloads to reflect the new `completed` status and transcript content
