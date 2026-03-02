# Transcription

## The Scribe's Art

TaleKeeper uses **Whisper**, an on-device speech recognition model, to transcribe your recordings. Everything runs locally — your audio never leaves your machine.

### Viewing the Transcript

Switch to the **Chronicle** tab (++2++) to see your full transcript.

![Chronicle tab showing timestamped transcript segments with color-coded speaker names, audio player, and search bar](../images/chronicle-tab.png)

Each segment shows:

- **Timestamp** — when the words were spoken
- **Speaker** — who said it (assigned by diarization)
- **Text** — what was said

!!! tip "Click to Seek"
    Click any transcript segment to jump to that moment in the audio player. Useful for reviewing specific moments.

### Whisper Model Sizes

The model size affects speed and accuracy. Configure it in **Settings**.

| Model | Speed | Accuracy | Best For |
|-------|-------|----------|----------|
| `tiny` | Fastest | Lower | Quick previews, testing |
| `base` | Fast | Fair | Short sessions |
| `small` | Moderate | Good | Most sessions |
| **`medium`** | Slower | **Very Good** | **Recommended default** |
| `large-v3` | Slowest | Best | Critical recordings, accented speech |

!!! info "Long Sessions"
    For recordings over 5 minutes, TaleKeeper automatically splits audio into chunks with overlapping segments to ensure nothing is missed at boundaries. You don't need to do anything — it's handled transparently.

### Language Support

TaleKeeper supports **98 languages** out of the box. Set the language at the campaign or session level, and transcription, summaries, and session names will all respect it.

Common languages: English, Spanish, French, German, Japanese, Korean, Chinese, Hebrew, Arabic, Portuguese, Italian, Russian, and [many more](../tips-and-tricks.md).

Next: [Re-run Transcription →](retranscription.md)
