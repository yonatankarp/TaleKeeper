# Transcription

## The Scribe's Art

TaleKeeper uses **Whisper**, an on-device speech recognition model running on Apple Silicon via MLX, to transcribe your recordings. Everything runs locally — your audio never leaves your machine.

### Viewing the Transcript

Switch to the **Chronicle** tab (++2++) to see your full transcript.

![Chronicle tab showing timestamped transcript segments with color-coded speaker names, audio player, and search bar](../images/chronicle-tab.png)

Each segment shows:

- **Timestamp** — when the words were spoken
- **Speaker** — who said it (assigned by diarization)
- **Text** — what was said

!!! tip "Click to Seek"
    Click any transcript segment to jump to that moment in the audio player. Useful for reviewing specific moments.

### Whisper Models

The model affects speed and accuracy. Configure it in **Settings**.

| Model | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| `tiny` | ~30 sec / 10 min audio | Lower | Quick previews, testing |
| `base` | ~1 min / 10 min audio | Fair | Short sessions |
| `small` | ~2 min / 10 min audio | Good | Most sessions |
| `medium` | ~3 min / 10 min audio | Very Good | Balanced option |
| **`distil-large-v3`** | ~2 min / 10 min audio | **Excellent** | **Recommended default** |
| `large-v3` | ~5 min / 10 min audio | Best | Critical recordings, accented speech |

!!! info "VAD Pre-Pass"
    Before transcription begins, TaleKeeper runs Voice Activity Detection (VAD) to identify and skip non-speech segments like silence, music, or background noise. This makes transcription faster and more accurate.

!!! info "Long Sessions"
    For recordings over 5 minutes, TaleKeeper automatically splits audio into chunks with overlapping segments to ensure nothing is missed at boundaries. You don't need to do anything — it's handled transparently.

### Language Support

TaleKeeper supports **98 languages** out of the box. Set the language at the campaign or session level, and transcription, summaries, and session names will all respect it.

Common languages: English, Spanish, French, German, Japanese, Korean, Chinese, Hebrew, Arabic, Portuguese, Italian, Russian, and [many more](../tips-and-tricks.md).

Next: [Re-run Transcription →](retranscription.md)
