# Live Recording

## Roll for Initiative

The **Recording** tab (keyboard shortcut: ++1++) is where your session begins. TaleKeeper captures audio directly from your microphone and processes it when you stop.

![Recording tab showing the Start Recording button, Upload Audio button, and speaker count selector](../images/recording-tab-idle.png)

### Starting a Recording

1. Navigate to your session's **Recording** tab
2. Set the **Speakers** count (1–10) to match your party size
3. Click **Start Recording** (the red button)

!!! note "Microphone Permissions"
    Your browser will ask for microphone access the first time. TaleKeeper needs this to capture audio — it never leaves your machine.

### During Recording

While recording, you'll see:

- A **pulsing red dot** with elapsed time (HH:MM:SS)
- **Pause** and **Stop** buttons
- A recording badge in the session header visible from any tab

You can:

- **Pause** — temporarily halt recording, then **Resume**
- **Stop** — end the recording and begin processing

### After Stopping

When you stop recording, TaleKeeper automatically:

1. Combines your recording into one complete file
2. Filters out silences and background noise
3. Converts speech to text
4. Identifies which parts belong to which speaker
5. Suggests a session title (if an AI assistant is connected)

A progress bar shows the current phase:

- **"Uploading..."** — finalizing audio
- **"Transcribing X / Y chunks — ~N min remaining"** — speech recognition in progress
- **"Assigning speakers..."** — diarization running

### Process All

!!! tip "Hidden Feature: One-Click Full Pipeline"
    After recording and processing are complete, a **Process All** button appears. Click it to run the entire pipeline in sequence: transcription → diarization → summaries → image generation. Progress phases light up as each step completes, and a final summary shows how many segments, summaries, and images were created.

    Process All is available once a session has been recorded or has audio uploaded, as long as no other processing is currently running.

!!! tip "Hidden Feature: Speaker Count Override"
    You can adjust the speaker count right before stopping — useful if unexpected guests joined or someone left early.

!!! warning "One at a Time"
    Only one session can be recorded at a time. If another session is recording, you'll see a message indicating it's locked.

Next: [Or Upload Pre-Recorded Audio →](uploading.md)
