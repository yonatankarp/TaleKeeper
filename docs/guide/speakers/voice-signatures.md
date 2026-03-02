# Voice Signatures

## A Familiar Voice

!!! tip "Hidden Feature"
    TaleKeeper can create **voice signatures** — audio fingerprints for each speaker that persist across sessions within a campaign.

### What Are Voice Signatures?

A voice signature is a mathematical representation of someone's voice, generated from labeled audio in your sessions. Once created, these signatures are stored with the character roster and can be used to improve speaker identification in future sessions.

### How It Works

1. **Record a session** and assign speaker names as usual
2. **Generate voice signatures** — TaleKeeper extracts speaker embeddings from the labeled audio
3. The signatures are stored with the corresponding **roster entry**

### Voice Signature Details

Each signature stores:

- The audio embedding (speaker "fingerprint")
- Which session it was generated from
- The number of audio samples used

!!! info "Campaign-Wide"
    Voice signatures are tied to **roster entries**, meaning they persist across all sessions in a campaign. The more sessions you label, the more data TaleKeeper has to work with.

Next: [Generate Summaries →](../summaries/index.md)
