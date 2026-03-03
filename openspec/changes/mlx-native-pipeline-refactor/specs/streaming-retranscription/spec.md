# Streaming Retranscription

## MODIFIED Requirements

### Requirement: Chunked processing within SSE endpoint
The retranscription endpoint SHALL split the audio file into overlapping chunks (per the chunked-audio-processing spec), run VAD pre-filtering and transcription on each chunk sequentially using lightning-whisper-mlx with batched decoding, apply overlap deduplication, and emit segments as they are produced. Only one WAV chunk SHALL be in memory at a time.

#### Scenario: Large file is processed in chunks
- **WHEN** a 2-hour audio file is retranscribed
- **THEN** the file is split into 5-minute overlapping chunks
- **AND** each chunk is VAD-filtered and transcribed sequentially using lightning-whisper-mlx
- **AND** segments are streamed to the client as each chunk completes
- **AND** memory usage remains bounded regardless of file length

#### Scenario: Small file is processed as single chunk
- **WHEN** an audio file shorter than 5 minutes is retranscribed
- **THEN** it is processed as a single chunk without splitting
- **AND** segments are still streamed via SSE
