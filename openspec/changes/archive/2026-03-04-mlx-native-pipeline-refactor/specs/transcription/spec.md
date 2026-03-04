# Transcription

## MODIFIED Requirements

### Requirement: On-device speech-to-text
The system SHALL transcribe audio using lightning-whisper-mlx running locally on the DM's machine via Apple's MLX framework. Transcription MUST NOT require any network connectivity or cloud services. The system SHALL use MLX-native inference to leverage Apple Silicon's unified memory architecture and GPU cores.

#### Scenario: Transcribe session audio
- **WHEN** a completed recording is submitted for transcription
- **THEN** lightning-whisper-mlx processes the audio on-device using MLX and produces text output with word-level timestamps

#### Scenario: No network required
- **WHEN** the machine has no internet connectivity
- **THEN** transcription functions identically to when the machine is online

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

## ADDED Requirements

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

## REMOVED Requirements

### Requirement: Real-time transcription during recording
**Reason**: Replaced by post-recording transcription using lightning-whisper-mlx, which is optimized for batched processing of complete audio segments rather than incremental chunks. Live transcription is incompatible with the new engine's batched decoding approach.
**Migration**: All transcription now occurs in the post-recording "process audio" phase. Users trigger transcription after stopping the recording.
