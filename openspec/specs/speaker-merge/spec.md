# Speaker Merge

## Purpose

Allow the DM to merge two speakers within a session into one, combining all transcript segments under a single speaker identity and cleaning up the absorbed speaker record.

## Requirements

### Requirement: Merge two speakers within a session
The system SHALL provide an API endpoint `POST /api/sessions/{session_id}/merge-speakers` that accepts `source_speaker_id` and `target_speaker_id`. The endpoint SHALL reassign all transcript segments from the source speaker to the target speaker, delete the source speaker record, and return the updated target speaker with segment counts. The entire operation MUST be atomic — either all changes succeed or none are applied.

#### Scenario: Successful merge of two speakers
- **WHEN** the DM merges speaker "Player 2" (source, 15 segments) into "Player 1" (target, 30 segments)
- **THEN** all 15 segments from "Player 2" are reassigned to "Player 1", the "Player 2" speaker record is deleted, and the response shows "Player 1" now has 45 segments

#### Scenario: Merge preserves target speaker identity
- **WHEN** the DM merges a source speaker into a target speaker that has player_name "Alex" and character_name "Thorin"
- **THEN** the target speaker retains its player_name, character_name, and diarization_label unchanged

#### Scenario: Merge with source having no segments
- **WHEN** the DM merges a source speaker that has 0 transcript segments into a target speaker
- **THEN** the source speaker record is deleted and the target speaker remains unchanged

#### Scenario: Merge fails atomically on error
- **WHEN** a merge operation encounters a database error during segment reassignment
- **THEN** no segments are reassigned, no speakers are deleted, and the system returns an error response

### Requirement: Merge validation
The system SHALL validate merge requests and reject invalid operations with appropriate error messages.

#### Scenario: Reject merge of speaker with itself
- **WHEN** the DM attempts to merge a speaker with itself (source_speaker_id equals target_speaker_id)
- **THEN** the system returns a 400 error with a message indicating source and target must be different

#### Scenario: Reject merge across sessions
- **WHEN** the DM attempts to merge two speakers that belong to different sessions
- **THEN** the system returns a 400 error with a message indicating both speakers must belong to the same session

#### Scenario: Reject merge with nonexistent speaker
- **WHEN** the DM attempts to merge with a source or target speaker ID that does not exist
- **THEN** the system returns a 404 error

#### Scenario: Reject merge with session mismatch
- **WHEN** the DM calls the merge endpoint on session 1 but provides speaker IDs that belong to session 2
- **THEN** the system returns a 400 error indicating the speakers do not belong to the specified session

### Requirement: Voice signature cleanup on merge
When the source speaker is linked to a roster entry that has a voice signature, the system SHALL delete that voice signature during the merge. The target speaker's voice signature (if any) SHALL be preserved.

#### Scenario: Source speaker has voice signature
- **WHEN** the DM merges a source speaker linked to roster entry "Bob/Gandalf" which has a voice signature
- **THEN** the voice signature for "Bob/Gandalf" is deleted and the target speaker's voice signature (if any) is preserved

#### Scenario: Neither speaker has voice signature
- **WHEN** the DM merges two speakers and neither is linked to a roster entry with a voice signature
- **THEN** the merge completes normally with no voice signature changes

#### Scenario: Only target speaker has voice signature
- **WHEN** the DM merges a source speaker (no voice signature) into a target speaker that has a voice signature
- **THEN** the target's voice signature is preserved and the merge completes normally

### Requirement: Merge UI in speaker panel
The speaker panel batch edit mode SHALL display a "Merge into..." action for each speaker. Clicking it SHALL present a selector of other speakers in the session as merge targets. Before executing, the system SHALL show a confirmation dialog stating which speaker will be removed, how many segments will be reassigned, and whether a voice signature will be deleted.

#### Scenario: Initiate merge from batch edit mode
- **WHEN** the DM is in batch edit mode and clicks "Merge into..." on a speaker labeled "Player 3"
- **THEN** a dropdown or selector appears listing all other speakers in the session as potential merge targets

#### Scenario: Confirmation dialog before merge
- **WHEN** the DM selects "Player 1" as the merge target for source "Player 3" (which has 12 segments)
- **THEN** a confirmation dialog appears stating: "Player 3" will be merged into "Player 1". 12 segments will be reassigned. This action cannot be undone.

#### Scenario: Confirmation dialog mentions voice signature deletion
- **WHEN** the source speaker has a linked voice signature and the DM triggers the confirmation dialog
- **THEN** the dialog includes a warning that the source speaker's voice signature will be deleted

#### Scenario: Cancel merge from confirmation dialog
- **WHEN** the DM clicks "Cancel" on the merge confirmation dialog
- **THEN** no merge occurs and the speaker panel returns to its previous state

#### Scenario: Speaker list updates after merge
- **WHEN** the DM confirms a merge and it completes successfully
- **THEN** the speaker panel refreshes to show the updated speaker list with the source speaker removed and the target speaker's segment count updated
