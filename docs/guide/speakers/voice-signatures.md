# Voice Signatures

## A Familiar Voice

!!! tip "Hidden Feature"
    TaleKeeper can create **voice signatures** — audio fingerprints for each speaker that persist across sessions within a campaign.

### What Are Voice Signatures?

A voice signature is a mathematical representation of someone's voice, generated from labeled audio in your sessions. Once created, these signatures are stored with the character roster and can be used to improve speaker identification in future sessions.

### How It Works

1. **Record a session** and assign speaker names as usual
2. **Generate voice signatures** — TaleKeeper extracts 192-dimensional speaker embeddings using pyannote.audio
3. The signatures are stored with the corresponding **roster entry**

### Voice Signature Details

Each signature stores:

- The audio embedding (speaker "fingerprint")
- Which session it was generated from
- The number of audio samples used

!!! info "Campaign-Wide"
    Voice signatures are tied to **roster entries**, meaning they persist across all sessions in a campaign. The more sessions you label, the more data TaleKeeper has to work with.

### Similarity Threshold

Each campaign has a configurable **Voice Signature Confidence** slider (found in campaign settings) that controls how strictly voice signatures are matched:

- **Lower values** (e.g., 0.4) — more lenient matching, may produce false positives
- **Higher values** (e.g., 0.8) — stricter matching, may miss some matches
- **Default: 0.65** — a good starting point for most groups

!!! tip "Tuning the Threshold"
    If speakers are being confused with each other, try raising the threshold. If known speakers aren't being recognized, try lowering it.

!!! warning "Upgrading from SpeechBrain"
    If you're upgrading from a previous version of TaleKeeper that used SpeechBrain for diarization, existing voice signatures are incompatible with the new pyannote.audio engine. You'll need to regenerate voice signatures for your roster entries from a labeled session.

Next: [Generate Summaries →](../summaries/index.md)
