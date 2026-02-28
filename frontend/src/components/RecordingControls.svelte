<script lang="ts">
  type Props = {
    sessionId: number;
    status: string;
    onStatusChange: () => void;
    onRecordingStateChange?: (state: 'idle' | 'recording' | 'paused', elapsed: number) => void;
    onTranscriptSegment?: (seg: { text: string; start_time: number; end_time: number }) => void;
  };
  let { sessionId, status, onStatusChange, onRecordingStateChange, onTranscriptSegment }: Props = $props();

  let recordingState = $state<'idle' | 'recording' | 'paused'>('idle');
  let elapsed = $state(0);
  let error = $state<string | null>(null);
  let mediaRecorder: MediaRecorder | null = null;
  let ws: WebSocket | null = null;
  let timerInterval: ReturnType<typeof setInterval> | null = null;

  // Global recording lock — only one session can record at a time
  const RECORDING_LOCK_KEY = 'talekeeper_recording_session';

  function isRecordingLocked(): boolean {
    const locked = sessionStorage.getItem(RECORDING_LOCK_KEY);
    return locked !== null && locked !== String(sessionId);
  }

  function lockRecording() {
    sessionStorage.setItem(RECORDING_LOCK_KEY, String(sessionId));
  }

  function unlockRecording() {
    sessionStorage.removeItem(RECORDING_LOCK_KEY);
  }

  async function startRecording() {
    error = null;

    if (isRecordingLocked()) {
      error = 'Another session is currently recording. Stop it first.';
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 44100,
          autoGainControl: true,
          noiseSuppression: true,
          echoCancellation: false,
        },
      });

      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      mediaRecorder = new MediaRecorder(stream, { mimeType });

      const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(`${protocol}//${location.host}/ws/recording/${sessionId}`);

      ws.onopen = () => {
        mediaRecorder!.start(1000); // send chunks every second
        recordingState = 'recording';
        lockRecording();
        startTimer();
      };

      ws.onerror = () => {
        error = 'WebSocket connection failed.';
        cleanup();
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'transcript' && onTranscriptSegment) {
            onTranscriptSegment({ text: msg.text, start_time: msg.start_time, end_time: msg.end_time });
          }
        } catch {
          // ignore non-JSON messages
        }
      };

      ws.onclose = () => {
        if (recordingState === 'recording') {
          cleanup();
        }
      };

      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0 && ws?.readyState === WebSocket.OPEN) {
          ws.send(e.data);
        }
      };

      mediaRecorder.onstop = () => {
        stream.getTracks().forEach((t) => t.stop());
      };
    } catch (err: any) {
      if (err.name === 'NotAllowedError') {
        error = 'Microphone permission denied. Please enable it in your browser settings.';
      } else if (err.name === 'NotFoundError') {
        error = 'No microphone found. Please connect a microphone.';
      } else {
        error = `Failed to start recording: ${err.message}`;
      }
    }
  }

  function pauseRecording() {
    if (mediaRecorder?.state === 'recording') {
      mediaRecorder.pause();
      recordingState = 'paused';
      stopTimer();
    }
  }

  function resumeRecording() {
    if (mediaRecorder?.state === 'paused') {
      mediaRecorder.resume();
      recordingState = 'recording';
      startTimer();
    }
  }

  async function stopRecording() {
    if (mediaRecorder) {
      mediaRecorder.stop();
    }
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'stop' }));
      ws.close();
    }
    cleanup();
    onStatusChange();
  }

  function cleanup() {
    stopTimer();
    recordingState = 'idle';
    unlockRecording();
    mediaRecorder = null;
    ws = null;
  }

  function startTimer() {
    timerInterval = setInterval(() => { elapsed += 1; }, 1000);
  }

  function stopTimer() {
    if (timerInterval) {
      clearInterval(timerInterval);
      timerInterval = null;
    }
  }

  function formatElapsed(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return [h, m, sec].map((v) => String(v).padStart(2, '0')).join(':');
  }

  // Notify parent of recording state changes
  $effect(() => {
    onRecordingStateChange?.(recordingState, elapsed);
  });

  let canRecord = $derived(status === 'draft' || status === 'recording');
  let isLocked = $derived(isRecordingLocked());
</script>

<div class="recording-controls">
  {#if error}
    <div class="error">{error}</div>
  {/if}

  {#if recordingState !== 'idle'}
    <div class="recording-indicator">
      <span class="dot" class:pulsing={recordingState === 'recording'}></span>
      <span class="time">{formatElapsed(elapsed)}</span>
      <span class="state-label">
        {recordingState === 'recording' ? 'Recording' : 'Paused'}
      </span>
    </div>
  {/if}

  <div class="controls">
    {#if recordingState === 'idle'}
      <button class="btn btn-record" onclick={startRecording} disabled={!canRecord || isLocked}>
        Start Recording
      </button>
      {#if isLocked}
        <span class="lock-msg">Another session is recording</span>
      {/if}
    {:else if recordingState === 'recording'}
      <button class="btn" onclick={pauseRecording}>Pause</button>
      <button class="btn btn-stop" onclick={stopRecording}>Stop</button>
    {:else if recordingState === 'paused'}
      <button class="btn btn-record" onclick={resumeRecording}>Resume</button>
      <button class="btn btn-stop" onclick={stopRecording}>Stop</button>
    {/if}
  </div>
</div>

<style>
  .recording-controls {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1.5rem;
  }

  .error {
    background: var(--error-bg);
    border: 1px solid var(--accent);
    color: var(--accent);
    padding: 0.75rem;
    border-radius: 4px;
    margin-bottom: 1rem;
    font-size: 0.9rem;
  }

  .recording-indicator {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    margin-bottom: 1rem;
    font-size: 1.1rem;
  }

  .dot {
    width: 12px;
    height: 12px;
    background: var(--accent);
    border-radius: 50%;
  }

  .dot.pulsing {
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .time {
    font-family: 'SF Mono', monospace;
    font-size: 1.5rem;
    color: var(--text);
  }

  .state-label {
    color: var(--text-muted);
    font-size: 0.85rem;
    text-transform: uppercase;
  }

  .controls {
    display: flex;
    gap: 0.75rem;
    align-items: center;
  }

  .btn {
    padding: 0.6rem 1.25rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-surface);
    color: var(--text);
    cursor: pointer;
    font-size: 0.9rem;
  }

  .btn:hover { background: var(--bg-hover); }
  .btn:disabled { opacity: 0.4; cursor: not-allowed; }
  .btn-record { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-record:hover:not(:disabled) { background: var(--accent-hover); }
  .btn-stop { background: var(--badge-dark); }

  .lock-msg {
    color: var(--text-muted);
    font-size: 0.8rem;
    font-style: italic;
  }
</style>
