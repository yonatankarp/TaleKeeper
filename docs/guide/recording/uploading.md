# Uploading Audio

## Recovered Scrolls

Already have a recording from another device? Upload it directly instead of recording live.

### How to Upload (Single File)

1. Go to the **Recording** tab (++1++)
2. Click **Upload Audio**
3. Select your audio file

![Recording tab on a draft session showing the Start Recording, Upload Audio buttons, and Audio Parts section](../images/recording-tab-draft.png)

TaleKeeper accepts common audio formats (m4a, mp3, wav, webm, ogg, flac) and automatically converts them for processing.

### What Happens Next

After upload, TaleKeeper automatically:

1. Prepares the audio for processing
2. Converts speech to text
3. Identifies speakers
4. Suggests a session title

!!! warning "Replacing Audio"
    Uploading new audio to a session that already has a recording will **replace** the previous audio and clear the existing transcript and speaker assignments. Summaries and images are preserved.

---

## Combining Multiple Recordings

Sessions are often captured in parts — a DM mic, a player mic, a phone backup, or a session split across two recording runs. Use the **Audio Parts** section (below the main controls on the Recording tab) to upload all parts, arrange them in the right order, and merge them into a single file before transcription begins.

### How to Upload Multiple Parts

1. Go to the **Recording** tab (++1++)
2. In the **Audio Parts** section, click **Add Parts**
3. Select one or more audio files — you can select multiple files at once
4. Repeat to add more files if needed

Each file appears in the parts list showing its filename.

### Arranging Parts

Use the **↑** and **↓** arrow buttons next to each part to set the playback order. The merged file will concatenate the parts from top to bottom.

To remove a part, click the **✕** button on that row.

### Merging and Transcribing

Once all parts are in the correct order, click **Merge & Transcribe**. TaleKeeper will:

1. Combine all parts into a single audio file in the order shown
2. Run the full transcription and speaker identification pipeline

Progress is shown inline — first a "Merging audio parts..." indicator, then the transcription progress bar.

!!! tip
    If you upload only one part, TaleKeeper skips the merge step and goes straight to transcription.

!!! note "Parts are kept after merging"
    The individual part files remain in the list after merging. You can re-merge with a different order at any time, which will clear and redo the transcript.

Next: [Understanding Your Transcript →](../transcription/index.md)
