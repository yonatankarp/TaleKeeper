# Retranscription

## A Second Reading

!!! tip "Hidden Feature"
    Not satisfied with the transcript? You can **re-run transcription** with different settings — no need to re-record.

### When to Retranscribe

- The transcript has errors and you want to try a **larger model**
- You initially used the wrong **language** setting
- The **speaker count** was off and diarization suffered
- You want to try a different combination of settings

### How to Retranscribe

![Chronicle tab with the Retranscribe and Re-diarize buttons visible above the transcript, along with language and speaker count controls](../images/chronicle-tab.png)

1. Select a different **Whisper model**
2. Optionally change the **language**
3. Optionally adjust the **speaker count**
4. Click **Retranscribe**

!!! warning "This Replaces the Existing Transcript"
    Retranscription clears the current transcript and speaker assignments, then generates new ones. Summaries and images are not affected.

### Progress Tracking

Retranscription streams progress via the same phases:

- Transcription chunk progress with ETA
- Speaker diarization
- Auto session naming (if the name was still generic)

Next: [Assign Speaker Names →](../speakers/index.md)
