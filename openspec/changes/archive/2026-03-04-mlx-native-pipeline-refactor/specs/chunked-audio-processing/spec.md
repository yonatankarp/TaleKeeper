# Chunked Audio Processing

## REMOVED Requirements

### Requirement: Incremental-only live transcription
**Reason**: Live transcription during recording has been removed from the system. The lightning-whisper-mlx engine is optimized for batched processing of complete audio segments, not incremental chunk-by-chunk transcription during recording. All transcription now occurs in the post-recording processing phase.
**Migration**: Transcription is triggered via the "Process Audio" or "Process All" endpoints after recording stops. The WebSocket recording endpoint now handles audio chunk storage only.
