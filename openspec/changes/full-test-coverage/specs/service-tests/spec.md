## ADDED Requirements

### Requirement: Transcription service tests
The test suite SHALL include unit tests for the transcription service with a mocked WhisperModel. Tests SHALL cover `transcribe()`, `transcribe_stream()`, and `transcribe_chunked()`.

#### Scenario: Transcribe returns segments
- **WHEN** `transcribe()` is called with a wav path and the WhisperModel is mocked to return canned segments
- **THEN** the function returns a list of `TranscriptSegment` objects with correct text, start_time, and end_time

#### Scenario: Transcribe stream yields segments incrementally
- **WHEN** `transcribe_stream()` is called with a mocked model
- **THEN** the iterator yields `TranscriptSegment` objects one at a time

#### Scenario: Transcribe chunked yields progress and segments
- **WHEN** `transcribe_chunked()` is called with a mocked model and audio splitter
- **THEN** the iterator yields both `ChunkProgress` and `TranscriptSegment` objects

#### Scenario: Model caching
- **WHEN** `get_model()` is called twice with the same model_size
- **THEN** the same WhisperModel instance is returned (not reloaded)

### Requirement: Diarization service tests
The test suite SHALL include unit tests for diarization with a mocked speechbrain encoder. Tests SHALL cover `diarize()`, `diarize_with_signatures()`, `align_speakers_with_transcript()`, and segment merging.

#### Scenario: Diarize returns speaker segments
- **WHEN** `diarize()` is called with a wav path and a mocked encoder returning fake embeddings
- **THEN** the function returns a list of `SpeakerSegment` objects with speaker labels and time ranges

#### Scenario: Diarize with voice signatures matches known speakers
- **WHEN** `diarize_with_signatures()` is called with signatures and a mocked encoder
- **THEN** segments are labeled using the provided signature roster entry IDs

#### Scenario: Align speakers with transcript assigns speaker IDs
- **WHEN** `align_speakers_with_transcript()` is called with speaker segments and transcript segments
- **THEN** each transcript segment is assigned the speaker whose time range overlaps most

#### Scenario: Merge adjacent same-speaker segments
- **WHEN** `_merge_segments()` is called with consecutive segments from the same speaker
- **THEN** adjacent segments are merged into one with combined time range

### Requirement: Audio service tests
The test suite SHALL include unit tests for audio conversion and chunking with mocked pydub.

#### Scenario: audio_to_wav converts file
- **WHEN** `audio_to_wav()` is called with a mock audio path and pydub is mocked
- **THEN** a wav file path is returned

#### Scenario: webm_to_wav converts WebM input
- **WHEN** `webm_to_wav()` is called with a WebM path and pydub is mocked
- **THEN** a wav file path is returned

#### Scenario: split_audio_to_chunks yields chunk tuples
- **WHEN** `split_audio_to_chunks()` is called with a mocked audio file of known duration
- **THEN** the iterator yields `(chunk_index, chunk_path, start_ms, end_ms)` tuples with correct overlap

#### Scenario: compute_primary_zone calculates non-overlap regions
- **WHEN** `compute_primary_zone()` is called with chunk parameters
- **THEN** the returned time range excludes the overlap regions (except for first/last chunks)

### Requirement: Summarization service tests
The test suite SHALL include unit tests for summarization with a mocked LLM client.

#### Scenario: Generate full summary
- **WHEN** `generate_full_summary()` is called with transcript text and a mocked LLM
- **THEN** a summary string is returned

#### Scenario: Generate POV summary
- **WHEN** `generate_pov_summary()` is called with transcript text, character name, and a mocked LLM
- **THEN** a summary string is returned

#### Scenario: Format transcript produces readable output
- **WHEN** `format_transcript()` is called with segment dicts containing speaker and timing info
- **THEN** the output is a formatted string with timestamps and speaker names

#### Scenario: Chunk long transcript
- **WHEN** `_chunk_transcript()` is called with text exceeding MAX_CONTEXT_TOKENS
- **THEN** multiple chunks are returned, each within the token limit, with overlap

### Requirement: LLM client tests
The test suite SHALL include unit tests for the LLM client with mocked httpx/OpenAI calls.

#### Scenario: Health check succeeds
- **WHEN** `health_check()` is called and the LLM endpoint responds successfully
- **THEN** `{"status": "ok"}` is returned

#### Scenario: Health check fails on connection error
- **WHEN** `health_check()` is called and the LLM endpoint is unreachable
- **THEN** a dict with `{"status": "error", "message": ...}` is returned

#### Scenario: Generate text
- **WHEN** `generate()` is called with a prompt and the LLM is mocked to return a response
- **THEN** the response text is returned as a string

#### Scenario: Resolve config reads from settings
- **WHEN** `resolve_config()` is called and settings contain custom base_url and model
- **THEN** the returned config dict reflects those settings

### Requirement: Image client tests
The test suite SHALL include unit tests for the image client with mocked OpenAI calls.

#### Scenario: Health check succeeds
- **WHEN** `health_check()` is called and the image endpoint responds
- **THEN** `{"status": "ok"}` is returned

#### Scenario: Generate image returns bytes
- **WHEN** `generate_image()` is called with a prompt and the client is mocked
- **THEN** image bytes are returned

### Requirement: Image generation service tests
The test suite SHALL include unit tests for scene description crafting and the image generation pipeline.

#### Scenario: Craft scene description
- **WHEN** `craft_scene_description()` is called with session content and a mocked LLM
- **THEN** a scene description string is returned

#### Scenario: Generate session image stores result in database
- **WHEN** `generate_session_image()` is called with a mocked image client and LLM
- **THEN** an image record is inserted into the `session_images` table and the image file is saved

### Requirement: Setup service test
The test suite SHALL include a unit test for the setup status checker.

#### Scenario: First run detected
- **WHEN** `check_first_run()` is called on a fresh data directory
- **THEN** the returned dict has `is_first_run: true`
