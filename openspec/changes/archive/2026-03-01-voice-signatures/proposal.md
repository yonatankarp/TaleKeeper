## Why

The current speaker diarization uses unsupervised clustering (SpeechBrain ECAPA-TDNN embeddings + agglomerative clustering) which guesses how many speakers exist and which windows belong to whom. In practice, this produces 10+ phantom speakers from a 2-person recording because the cosine distance threshold cannot reliably separate speakers from a single microphone. Voice signatures solve this by letting the system match audio against known speaker profiles instead of guessing — turning an unsupervised problem into a supervised one.

## What Changes

- Add the ability to generate per-speaker voice embeddings from manually-labeled sessions (bootstrap from existing recordings — no separate enrollment step needed)
- Store voice signature embeddings at the campaign level so they persist across sessions
- During diarization, when voice signatures exist for a campaign, match audio windows against stored signatures using cosine similarity instead of blind clustering
- Fall back to improved threshold-based clustering when no signatures are available (tune existing parameters for better cold-start behavior)
- Add UI controls to generate and manage voice signatures from the speaker panel
- Tune clustering parameters (window size, distance threshold) for better cold-start diarization

## Capabilities

### New Capabilities
- `voice-signatures`: Enrollment, storage, and retrieval of per-speaker voice embeddings at the campaign level, including extraction from labeled sessions and cosine-similarity-based speaker matching during diarization

### Modified Capabilities
- `speaker-diarization`: Add signature-based matching as the primary diarization strategy when signatures exist; improve clustering fallback parameters for cold-start sessions

## Impact

- **Backend**: `services/diarization.py` gains signature extraction and matching code paths; new API endpoints for generating/managing signatures
- **Database**: New `voice_signatures` table (or `embedding` column on `speakers`) to store serialized embedding vectors at the campaign level
- **Frontend**: Speaker panel gets a "Generate Voice Signatures" action; visual indicator showing which speakers have signatures
- **Dependencies**: No new ML dependencies — reuses existing ECAPA-TDNN encoder and numpy/scikit-learn
