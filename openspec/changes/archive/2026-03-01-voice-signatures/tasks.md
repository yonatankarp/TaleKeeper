## 1. Database

- [x] 1.1 Add `voice_signatures` table to schema in `db/connection.py` (id, campaign_id, roster_entry_id, embedding TEXT, source_session_id, num_samples, created_at) with CASCADE on roster_entries and campaigns
- [x] 1.2 Add migration to create the table for existing databases

## 2. Signature Extraction

- [x] 2.1 Add `extract_speaker_embedding` function in `services/diarization.py` — given a waveform and list of (start, end) time ranges, extract windowed ECAPA-TDNN embeddings, average them, and L2-normalize
- [x] 2.2 Add `generate_voice_signatures` function that takes a session_id, loads the WAV, collects transcript segments per roster-linked speaker, calls `extract_speaker_embedding` for each, and stores results in `voice_signatures` table (replacing existing signatures for the same roster entry)

## 3. Signature-Based Diarization

- [x] 3.1 Add `diarize_with_signatures` function — given a WAV path and list of (roster_entry_id, embedding) pairs, extract windowed embeddings and assign each window to the nearest signature above the similarity threshold (0.25), labeling unmatched windows as "Unknown Speaker"
- [x] 3.2 Update `run_final_diarization` to check for campaign voice signatures and call `diarize_with_signatures` when available, falling back to clustering otherwise
- [x] 3.3 When using signature-based diarization, auto-create session speakers with player_name/character_name pre-filled from the matched roster entries

## 4. Cold-Start Clustering Tuning

- [x] 4.1 Update clustering constants: `WINDOW_SIZE_SEC` 1.5→3.0, `HOP_SIZE_SEC` 0.75→1.5, `COSINE_DISTANCE_THRESHOLD` 0.7→1.0

## 5. API Endpoints

- [x] 5.1 Add `POST /api/sessions/{session_id}/generate-voice-signatures` endpoint — calls `generate_voice_signatures`, returns count of signatures generated and samples per speaker
- [x] 5.2 Add `GET /api/campaigns/{campaign_id}/voice-signatures` endpoint — returns list of signatures with roster entry details and sample counts (no raw embeddings)
- [x] 5.3 Add `DELETE /api/voice-signatures/{signature_id}` endpoint — removes a specific signature

## 6. Frontend

- [x] 6.1 Add "Generate Voice Signatures" button to the speaker panel, visible when session has audio and at least one speaker is linked to a roster entry
- [x] 6.2 Wire button to call the generate endpoint, show loading state, and display confirmation with per-speaker sample counts
- [x] 6.3 Add signature status indicators (icon/badge) next to speakers that have voice signatures in the campaign
