# Speaker Diarization

## MODIFIED Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically detect and distinguish different speakers in the audio using pyannote.audio's speaker diarization pipeline running on the Apple GPU via MPS. When voice signatures exist for the session's campaign, the system SHALL use signature-based nearest-neighbor matching as the primary identification method. When no signatures exist, the system SHALL use pyannote's built-in clustering. During final diarization, the system SHALL pass the campaign's `num_speakers` setting to pyannote for fixed-count speaker detection. Each detected speaker MUST be assigned a provisional label (e.g., "Player 1", "Player 2") or matched to a known roster entry name.

#### Scenario: Speakers detected with voice signatures
- **WHEN** a recording is processed and the campaign has voice signatures
- **THEN** the system matches audio segments against stored signatures and labels transcript segments with the matched roster entry names

#### Scenario: Speakers detected without voice signatures (cold start)
- **WHEN** a recording is processed and the campaign has no voice signatures
- **THEN** the system uses pyannote's built-in clustering and labels transcript segments with provisional identifiers (e.g., "Player 1", "Player 2")

#### Scenario: Single speaker detected
- **WHEN** only one person has spoken during the recording
- **THEN** all transcript segments are assigned to "Player 1" or the matched roster entry name

#### Scenario: Final diarization uses campaign speaker count
- **WHEN** a recording is stopped in a campaign with `num_speakers` set to 5
- **THEN** the final diarization pass uses pyannote with `num_speakers=5` to detect exactly 5 speaker groups

#### Scenario: Speaker count fetched from campaign
- **WHEN** `run_final_diarization` is called for a session
- **THEN** the system looks up the session's campaign and retrieves its `num_speakers` value, passing it to the pyannote pipeline

#### Scenario: Single speaker campaign
- **WHEN** a campaign has `num_speakers` set to 1
- **THEN** all transcript segments are assigned to a single speaker

#### Scenario: Retranscribe with speaker count override
- **WHEN** the user retranscribes a session with `num_speakers` set to 3
- **THEN** the final diarization pass uses pyannote with `num_speakers=3`, regardless of the campaign's default

#### Scenario: Recording with speaker count override
- **WHEN** the user sets `num_speakers` to 4 before recording
- **THEN** the final diarization after recording stop uses 4 speakers, regardless of the campaign's default

## ADDED Requirements

### Requirement: HuggingFace token for pyannote access
The system SHALL require a HuggingFace access token to download and use pyannote.audio's gated models. The token SHALL be configurable via the Settings page (stored in the `settings` table as `hf_token`) with an `HF_TOKEN` environment variable as fallback. The system SHALL display a clear error with setup instructions if no token is configured when diarization is attempted.

#### Scenario: Token configured via settings
- **WHEN** the DM enters a HuggingFace token in the Settings page
- **THEN** the token is stored in the settings table and used for pyannote model access

#### Scenario: Token configured via environment variable
- **WHEN** no `hf_token` is stored in settings but the `HF_TOKEN` environment variable is set
- **THEN** the system uses the environment variable value for pyannote model access

#### Scenario: No token configured
- **WHEN** diarization is triggered and no HuggingFace token is configured (neither settings nor env var)
- **THEN** the system returns an error with a message explaining that a HuggingFace token is required, including a link to the pyannote license agreement page

#### Scenario: HuggingFace token field in settings UI
- **WHEN** the DM opens the Settings page
- **THEN** a "HuggingFace Token" field is displayed in the Providers section with a link to the pyannote license agreement

## REMOVED Requirements

### Requirement: Near-real-time diarization during recording
**Reason**: Live transcription during recording has been removed (see transcription spec). Without live transcript segments, there is no need for provisional speaker labels during recording. All diarization now runs in the post-recording processing phase.
**Migration**: Speaker labels are assigned during the post-recording "process audio" phase, which runs the full pyannote diarization pipeline on the complete audio.
