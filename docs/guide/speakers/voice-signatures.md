# Voice Signatures

## A Familiar Voice

!!! tip "Hidden Feature"
    TaleKeeper can learn your players' voices and **automatically recognize them** in future sessions — no manual speaker assignment needed.

### What Are Voice Signatures?

A voice signature is a unique vocal "fingerprint" for each player. Once TaleKeeper has learned someone's voice, it can automatically identify them in future recordings, saving you from manually assigning speaker names every session.

Voice signatures are stored with the [character roster](../campaigns/roster.md), so they persist across all sessions in a campaign.

### Two Ways to Create Voice Signatures

There are two ways to teach TaleKeeper a player's voice:

#### Option A: Upload a Voice Sample (Before You Play)

The fastest way to get started. Have each player record a short audio clip of themselves talking, then upload it from the roster page.

1. Go to your campaign's **Party** page
2. Find the player's roster entry
3. Click **Upload Voice**
4. Select an audio file of that player speaking (any format, ~30 seconds to 2 minutes works well)
5. TaleKeeper processes the clip and creates a voice signature

Once uploaded, a green **Voice ID** badge appears next to the character's name. Hover over it to see how many samples were used.

!!! tip "Quick Start"
    This is the best way to set up voice recognition before your first session. Have your players send you a voice memo, a clip from a previous recording, or even just a quick phone recording of themselves talking for a minute.

#### Option B: Generate from a Labeled Session (After You Play)

If you've already recorded and transcribed a session with speakers properly labeled, TaleKeeper can extract voice signatures from that recording.

1. Open a completed session and go to the **Chronicle** tab (++2++)
2. Make sure all speakers are correctly named and matched to roster entries
3. Expand the **Speakers** panel
4. Click the green **Generate Voice Signatures** button (appears only when speakers are linked to roster entries)
5. TaleKeeper analyzes each speaker's audio segments and builds their voice profile

A success message shows how many signatures were created and the sample count for each character. Speakers with stored signatures display a green **VS** badge.

!!! info "More Sessions = Better Recognition"
    Each time you generate voice signatures from a new session, TaleKeeper has more audio to work with. Recognition improves as it builds a richer profile of each voice.

### Automatic Speaker Recognition

Once voice signatures exist, TaleKeeper uses them automatically:

- When you **record a new session**, speakers are matched to known voices during processing
- When you **re-diarize** an existing session, stored voice profiles are used for matching
- Speakers that can't be confidently matched appear as "Unknown Speaker" rather than being guessed incorrectly

### Similarity Threshold

Each campaign has a **Voice Signature Confidence** slider (found in campaign settings) that controls how strict the matching is:

- **Lower values** — more lenient, recognizes more speakers but may occasionally mix them up
- **Higher values** — stricter, fewer mistakes but may fail to recognize some speakers
- **Default: 0.65** — works well for most groups

!!! tip "Tuning Tips"
    - If two players are being confused for each other, **raise** the threshold
    - If a known player keeps showing up as "Unknown Speaker", **lower** the threshold
    - Groups with very similar-sounding voices may need a higher threshold

### Replacing a Voice Signature

To update a player's voice signature (for example, if the original sample was noisy):

1. Go to the **Party** page
2. Click **Replace Voice** on the roster entry (the button label changes once a signature exists)
3. Upload a new, cleaner audio sample

The new signature replaces the old one.

### Voice Signature Badges

Voice signatures are indicated by badges in two places:

| Badge | Where | Meaning |
|-------|-------|---------|
| **Voice ID** (green) | Party / Roster page | This character has a stored voice signature |
| **VS** (green circle) | Speaker panel in sessions | This session speaker is linked to a roster entry with a voice signature |

Hover over either badge to see the sample count.

!!! warning "Upgrading from an Older Version"
    If you're upgrading from an earlier version of TaleKeeper, existing voice signatures won't work with the updated speaker detection system. You'll need to rebuild them using either method above.

Next: [Generate Summaries →](../summaries/index.md)
