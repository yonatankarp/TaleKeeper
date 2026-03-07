## MODIFIED Requirements

### Requirement: Automatic speaker detection
The system SHALL automatically detect and distinguish different speakers in the audio using the diarize library (Silero VAD + WeSpeaker + spectral clustering). When voice signatures exist for the session's campaign, the system SHALL use signature-based matching via the Hungarian algorithm as the primary identification method. When no signatures exist, the system SHALL use spectral clustering. During final diarization, the system SHALL pass the campaign's `num_speakers` setting to the clustering step for fixed-count speaker detection. Each detected speaker MUST be assigned a provisional label (e.g., "Player 1", "Player 2") or matched to a known roster entry name. After clustering, the system SHALL run overlap detection and assign the label `[crosstalk]` to ambiguous subsegments before assembling the final segment list.

#### Scenario: Speakers detected with voice signatures
- **WHEN** a recording is processed and the campaign has voice signatures
- **THEN** the system matches audio segments against stored signatures using the Hungarian algorithm and labels transcript segments with the matched roster entry names

#### Scenario: Speakers detected without voice signatures (cold start)
- **WHEN** a recording is processed and the campaign has no voice signatures
- **THEN** the system uses spectral clustering and labels transcript segments with provisional identifiers (e.g., "Player 1", "Player 2")

#### Scenario: Single speaker detected
- **WHEN** only one person has spoken during the recording
- **THEN** all transcript segments are assigned to "Player 1" or the matched roster entry name

#### Scenario: Final diarization uses campaign speaker count
- **WHEN** a recording is stopped in a campaign with `num_speakers` set to 5
- **THEN** the final diarization pass uses spectral clustering with `num_speakers=5` to detect exactly 5 speaker groups

#### Scenario: Speaker count fetched from campaign
- **WHEN** `run_final_diarization` is called for a session
- **THEN** the system looks up the session's campaign and retrieves its `num_speakers` value, passing it to the clustering step

#### Scenario: Single speaker campaign
- **WHEN** a campaign has `num_speakers` set to 1
- **THEN** all transcript segments are assigned to a single speaker

#### Scenario: Retranscribe with speaker count override
- **WHEN** the user retranscribes a session with `num_speakers` set to 3
- **THEN** the final diarization pass uses `num_speakers=3`, regardless of the campaign's default

#### Scenario: Recording with speaker count override
- **WHEN** the user sets `num_speakers` to 4 before recording
- **THEN** the final diarization after recording stop uses 4 speakers, regardless of the campaign's default

#### Scenario: Overlap segments produced alongside speaker segments
- **WHEN** diarization completes on a session where players spoke simultaneously
- **THEN** the resulting segment list contains both speaker-attributed segments and `[crosstalk]` segments interleaved by timestamp

### Requirement: Speaker-transcript alignment
The system SHALL align speaker diarization results with transcript segments so that each transcript segment is associated with exactly one speaker or flagged as `[crosstalk]`. When a single transcript segment overlaps most with a `[crosstalk]` diarization segment, it MUST be stored with `speaker_id = NULL` and `is_overlap = 1`. When using signature-based matching, speaker labels SHALL use the roster entry's player/character name directly instead of generic labels.

#### Scenario: Segments aligned with speakers
- **WHEN** diarization and transcription have both completed for a session
- **THEN** every transcript segment has either exactly one speaker label or is flagged as `[crosstalk]`, and the speaker changes align with actual voice changes in the audio

#### Scenario: Segments aligned with known speakers
- **WHEN** diarization using voice signatures has completed for a session
- **THEN** every attributed transcript segment has a speaker label matching a roster entry name

#### Scenario: Segments aligned with unknown speakers
- **WHEN** diarization has completed and some segments could not be matched to any voice signature
- **THEN** those segments are labeled "Unknown Speaker" and the user can manually reassign them

#### Scenario: Crosstalk segment not assigned to any speaker
- **WHEN** a transcript segment's maximum overlap is with a `[crosstalk]` diarization segment
- **THEN** that transcript segment is stored with `speaker_id = NULL` and `is_overlap = 1`
