# Transcription

## Purpose

Provide on-device speech-to-text transcription using lightning-whisper-mlx on Apple Silicon, supporting post-recording batch processing, timestamped segments, model selection, VAD pre-filtering, re-transcription, and language configuration.

## Requirements

### Requirement: On-device speech-to-text
The system SHALL transcribe audio using lightning-whisper-mlx running locally on the DM's machine via Apple's MLX framework. Transcription MUST NOT require any network connectivity or cloud services. The system SHALL use MLX-native inference to leverage Apple Silicon's unified memory architecture and GPU cores.

#### Scenario: Transcribe session audio
- **WHEN** a completed recording is submitted for transcription
- **THEN** lightning-whisper-mlx processes the audio on-device using MLX and produces text output with word-level timestamps

#### Scenario: No network required
- **WHEN** the machine has no internet connectivity
- **THEN** transcription functions identically to when the machine is online

### Requirement: Timestamped transcript segments
The system SHALL produce transcript segments with start and end timestamps aligned to the session audio timeline. Each segment MUST contain the transcribed text and its time range.

#### Scenario: Segment timestamps match audio
- **WHEN** the DM clicks on a transcript segment showing timestamp "00:12:30 - 00:12:45"
- **THEN** playing the audio from 00:12:30 produces speech matching the segment's text

### Requirement: Transcript persistence
The system SHALL store all transcript segments in the database, associated with their session. Transcripts MUST persist across application restarts.

#### Scenario: Transcript available after restart
- **WHEN** the application is restarted after a session has been transcribed
- **THEN** the full transcript is available when the DM opens that session

### Requirement: Whisper model selection
The system SHALL allow the DM to select which Whisper model to use for transcription. The system MUST default to `mlx-community/whisper-large-v3-turbo` (4-bit quantized). The settings UI SHALL show recommended models with performance notes to help the DM choose.

#### Scenario: Change model size
- **WHEN** the DM changes the Whisper model in settings
- **THEN** subsequent transcriptions use the newly selected model

#### Scenario: Default model selection
- **WHEN** the DM has not configured a model preference
- **THEN** the system defaults to `mlx-community/whisper-large-v3-turbo` as the recommended model for Apple Silicon

#### Scenario: Model recommendations shown in UI
- **WHEN** the DM opens the Whisper model selection in settings
- **THEN** the UI shows available models with performance annotations (e.g., speed vs accuracy trade-offs)

### Requirement: Re-transcription of stored audio
The system SHALL allow the DM to re-transcribe a previously recorded session using a different model or settings. Re-transcription MUST replace the existing transcript segments.

#### Scenario: Re-transcribe with larger model
- **WHEN** the DM selects "Re-transcribe" on a completed session and chooses the `large-v3` model
- **THEN** the system re-processes the stored audio file with the selected model, replaces the existing transcript segments, and preserves any speaker assignments that can be re-aligned

### Requirement: Transcription language
The system SHALL transcribe audio in English. The language MUST be explicitly set to English rather than relying on auto-detection.

#### Scenario: English language forced
- **WHEN** transcription is initiated
- **THEN** the Whisper model is configured with language set to English for optimal accuracy

### Requirement: Transcript search and filtering
The system SHALL provide a search bar above the transcript view that filters segments by text content or speaker name. The filter SHALL be case-insensitive and update in real-time as the DM types. The system MUST show a match count and a clear button when a search is active.

#### Scenario: Search transcript by keyword
- **WHEN** the DM types "dragon" in the transcript search bar
- **THEN** only transcript segments containing "dragon" (case-insensitive) are shown, with a count like "12 matches"

#### Scenario: Search by speaker name
- **WHEN** the DM types "Thorin" in the search bar
- **THEN** segments where the speaker is Thorin are shown

#### Scenario: Clear search
- **WHEN** the DM clicks the "Clear" button next to the search bar
- **THEN** the search is cleared and all segments are shown again

#### Scenario: No matches found
- **WHEN** the DM searches for a term that doesn't appear in any segment
- **THEN** the message "No matches found." is displayed

### Requirement: Transcript empty state guidance
The system SHALL display a helpful message when no transcript is available.

#### Scenario: No transcript available
- **WHEN** the DM views a session with no transcript and no active recording
- **THEN** the message "No transcript available. Start recording or retranscribe audio to generate one." is displayed

### Requirement: Voice Activity Detection pre-pass
The system SHALL run a Silero VAD pass on audio before transcription to identify speech regions and filter out non-speech audio (dice rolls, table noise, laughter, background chatter). Only speech regions SHALL be passed to the transcription model. Original audio timestamps SHALL be preserved by maintaining an offset map from VAD-filtered audio back to the original timeline.

#### Scenario: Non-speech audio filtered
- **WHEN** a 2-hour recording containing 90 minutes of speech and 30 minutes of non-speech (dice rolls, side conversations, silence) is transcribed
- **THEN** the transcription model processes only the 90 minutes of detected speech, and the resulting transcript segments have timestamps aligned to the original 2-hour audio timeline

#### Scenario: Fully silent audio
- **WHEN** an audio file contains no detected speech
- **THEN** the transcription produces zero segments and the system reports that no speech was detected

### Requirement: Hardware-aware batched decoding
The system SHALL use batched decoding with a batch size automatically determined from the Apple Silicon hardware variant. The system SHALL detect the number of performance CPU cores and map them to an appropriate batch size. The batch size SHALL be overridable via a setting.

#### Scenario: Batch size auto-detected
- **WHEN** the system starts on an Apple M2 Pro (10 performance cores)
- **THEN** the batch size is automatically set to 12

#### Scenario: Batch size overridden in settings
- **WHEN** the DM sets a custom batch size of 16 in settings
- **THEN** transcription uses batch size 16 regardless of the auto-detected value

#### Scenario: Batch size setting persists
- **WHEN** the DM saves a custom batch size
- **THEN** the setting persists across application restarts
