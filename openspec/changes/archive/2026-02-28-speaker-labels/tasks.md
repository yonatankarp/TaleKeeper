## 1. Backend: Friendly speaker labels

- [x] 1.1 In `run_final_diarization()`, replace raw pyannote label storage with friendly "Player N" labels using `enumerate(unique_labels, start=1)` and `f"Player {idx}"`

## 2. Backend: Wire diarization into recording flow

- [x] 2.1 In `recording.py` WebSocket handler `finally` block, after `merge_chunk_files`, convert WebM to WAV using `webm_to_wav()`
- [x] 2.2 Call `run_final_diarization(session_id, wav_path)` with try/finally cleanup of the temporary WAV file

## 3. Backend: Wire diarization into retranscription flow

- [x] 3.1 In `transcripts.py` SSE generator, delete old speakers (`DELETE FROM speakers WHERE session_id = ?`) alongside existing segment deletion before retranscription starts
- [x] 3.2 After all transcript segments are inserted and before marking session as completed, convert WebM to WAV and call `run_final_diarization()` with WAV cleanup

## 4. Frontend: Speaker label fallback chain

- [x] 4.1 Update `speakerLabel()` in `TranscriptView.svelte` to use full fallback: character+player > character > player > diarization_label > empty
- [x] 4.2 Update `speakerDisplay()` in `SpeakerPanel.svelte` to use the same fallback chain for consistency

## 5. Frontend: Reload transcript after retranscription

- [x] 5.1 Add `await load()` in the `finally` block of `TranscriptView.retranscribe()` to reload speaker-populated segments from the API after diarization completes
