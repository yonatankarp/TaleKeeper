<script lang="ts">
  import { api, uploadAudio, processAudio, processAll, type ProcessAllResult } from '../lib/api';

  type Props = {
    sessionId: number;
    campaignId?: number;
    status: string;
    onStatusChange: () => void;
    onRecordingStateChange?: (state: 'idle' | 'recording' | 'paused', elapsed: number) => void;
    onTranscriptSegment?: (seg: { text: string; start_time: number; end_time: number }) => void;
  };
  let { sessionId, campaignId, status, onStatusChange, onRecordingStateChange, onTranscriptSegment }: Props = $props();

  let recordingState = $state<'idle' | 'recording' | 'paused'>('idle');
  let elapsed = $state(0);
  let error = $state<string | null>(null);
  let mediaRecorder: MediaRecorder | null = null;
  let ws: WebSocket | null = null;
  let timerInterval: ReturnType<typeof setInterval> | null = null;

  // Speaker count override
  let numSpeakers = $state(5);

  $effect(() => {
    if (campaignId) {
      api.get<{ num_speakers: number }>(`/campaigns/${campaignId}`).then(c => {
        numSpeakers = c.num_speakers;
      });
    }
  });

  // Upload state
  let uploading = $state(false);
  let processing = $state(false);
  let chunkProgress = $state<{ chunk: number; total: number } | null>(null);
  let fileInput: HTMLInputElement | undefined = $state();
  let processCanceller: { cancel: () => void } | null = null;

  // Processing progress state
  let processingStartTime = $state<number | null>(null);
  let phase = $state<'transcribing' | 'diarization' | null>(null);
  let now = $state(Date.now());
  let etaInterval: ReturnType<typeof setInterval> | null = null;

  // Pipeline (Process All) state
  let pipelineRunning = $state(false);
  let pipelinePhase = $state<string | null>(null);
  let pipelineResult = $state<ProcessAllResult | null>(null);
  let pipelineCanceller: { cancel: () => void } | null = null;

  const phaseLabels: Record<string, string> = {
    transcription: 'Transcribing audio...',
    diarization: 'Assigning speakers...',
    summaries: 'Generating summaries...',
    image_generation: 'Creating session art...',
  };

  // Tick `now` every second while processing for live ETA updates
  $effect(() => {
    if ((processing || pipelineRunning) && (chunkProgress || pipelinePhase)) {
      etaInterval = setInterval(() => { now = Date.now(); }, 1000);
      return () => { if (etaInterval) { clearInterval(etaInterval); etaInterval = null; } };
    }
  });

  let progressPercent = $derived(
    chunkProgress ? Math.round((chunkProgress.chunk / chunkProgress.total) * 100) : 0
  );

  let etaText = $derived.by(() => {
    if (!processingStartTime || !chunkProgress || chunkProgress.chunk <= 0) return '';
    const elapsed = now - processingStartTime;
    const avgPerChunk = elapsed / chunkProgress.chunk;
    const remainingMs = avgPerChunk * (chunkProgress.total - chunkProgress.chunk);
    const mins = Math.ceil(remainingMs / 60000);
    if (mins < 1) return '< 1 min remaining';
    return `~${mins} min remaining`;
  });

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
      ws.send(JSON.stringify({ type: 'stop', num_speakers: numSpeakers }));
      ws.close();
    }
    cleanup();
    waitForAudioReadyAndProcess();
  }

  async function waitForAudioReadyAndProcess() {
    processStarted = true;
    processing = true;
    try {
      // Poll until backend finishes merging chunks and sets status
      while (true) {
        const session = await api.get<{ status: string }>(`/sessions/${sessionId}`);
        if (session.status === 'audio_ready') break;
        if (session.status !== 'recording') {
          // draft (empty recording), completed, or transcribing — nothing to wait for
          processing = false;
          onStatusChange();
          return;
        }
        await new Promise(r => setTimeout(r, 1000));
      }

      onStatusChange();

      processingStartTime = Date.now();
      phase = null;

      processCanceller = processAudio(
        sessionId,
        (chunk, total) => {
          if (!phase) phase = 'transcribing';
          chunkProgress = { chunk, total };
        },
        (seg) => { onTranscriptSegment?.(seg); },
        (_count) => {
          processing = false;
          chunkProgress = null;
          processingStartTime = null;
          phase = null;
          processCanceller = null;
          onStatusChange();
        },
        (message) => {
          error = message;
          processing = false;
          chunkProgress = null;
          processingStartTime = null;
          phase = null;
          processCanceller = null;
          onStatusChange();
        },
        numSpeakers,
        (p) => { phase = p as 'diarization'; },
      );
    } catch (e) {
      error = e instanceof Error ? e.message : 'Processing failed';
      processing = false;
      processingStartTime = null;
      phase = null;
      onStatusChange();
    }
  }

  // Auto-resume processing if component mounts with audio_ready status (e.g. page refresh mid-process).
  // processStarted prevents the effect from re-triggering after processAudio completes, when
  // the status prop is still stale 'audio_ready' but the backend has already moved to 'completed'.
  let processStarted = false;
  $effect(() => {
    if (!processStarted && status === 'audio_ready' && !processing && !uploading && recordingState === 'idle') {
      waitForAudioReadyAndProcess();
    }
  });

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

  function triggerFileInput() {
    fileInput?.click();
  }

  async function handleFileSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    // Reset so the same file can be re-selected
    input.value = '';

    error = null;
    uploading = true;

    try {
      await uploadAudio(sessionId, file);
      uploading = false;
      processing = true;
      processingStartTime = Date.now();
      phase = null;

      processCanceller = processAudio(
        sessionId,
        (chunk, total) => {
          if (!phase) phase = 'transcribing';
          chunkProgress = { chunk, total };
        },
        (seg) => { onTranscriptSegment?.(seg); },
        (_count) => {
          processing = false;
          chunkProgress = null;
          processingStartTime = null;
          phase = null;
          processCanceller = null;
          onStatusChange();
        },
        (message) => {
          error = message;
          processing = false;
          chunkProgress = null;
          processingStartTime = null;
          phase = null;
          processCanceller = null;
          onStatusChange();
        },
        numSpeakers,
        (p) => { phase = p as 'diarization'; },
      );
    } catch (e) {
      error = e instanceof Error ? e.message : 'Upload failed';
      uploading = false;
    }
  }

  // Process All pipeline
  function startProcessAll() {
    error = null;
    pipelineRunning = true;
    pipelinePhase = null;
    pipelineResult = null;
    chunkProgress = null;
    processingStartTime = Date.now();

    pipelineCanceller = processAll(
      sessionId,
      {
        onPhase: (p) => {
          pipelinePhase = p;
          // Reset chunk progress when entering a new phase
          if (p !== 'transcription') {
            chunkProgress = null;
          }
        },
        onProgress: (chunk, total) => {
          chunkProgress = { chunk, total };
        },
        onDone: (result) => {
          pipelineRunning = false;
          pipelinePhase = null;
          chunkProgress = null;
          processingStartTime = null;
          pipelineResult = result;
          pipelineCanceller = null;
          onStatusChange();
        },
        onError: (message) => {
          error = message;
          pipelineRunning = false;
          pipelinePhase = null;
          chunkProgress = null;
          processingStartTime = null;
          pipelineCanceller = null;
          onStatusChange();
        },
      },
      numSpeakers,
    );
  }

  function dismissPipelineResult() {
    pipelineResult = null;
  }

  let busy = $derived(uploading || processing || pipelineRunning);
  let canRecord = $derived((status === 'draft' || status === 'recording') && !busy);
  let canUpload = $derived((status === 'draft' || status === 'completed') && !busy && recordingState === 'idle');
  let canProcessAll = $derived(
    (status === 'audio_ready' || status === 'completed') && !busy && recordingState === 'idle'
  );
  let isLocked = $derived(isRecordingLocked());
  let hasAudio = $derived(status !== 'draft');
</script>

<div class="recording-controls">
  {#if error}
    <div class="error">{error}</div>
  {/if}

  {#if recordingState !== 'idle' && !busy}
    <div class="recording-indicator">
      <span class="dot" class:pulsing={recordingState === 'recording'}></span>
      <span class="time">{formatElapsed(elapsed)}</span>
      <span class="state-label">
        {recordingState === 'recording' ? 'Recording' : 'Paused'}
      </span>
    </div>
  {/if}

  {#if uploading}
    <div class="processing-banner">
      <span class="processing-dot"></span>
      Uploading...
    </div>
  {/if}

  {#if processing}
    <div class="processing-banner">
      {#if phase === 'diarization'}
        <span class="processing-dot"></span>
        Assigning speakers...
      {:else if chunkProgress}
        <div class="progress-section">
          <div class="progress-bar">
            <div class="progress-fill" style="width: {progressPercent}%"></div>
          </div>
          <span class="progress-label">
            Transcribing {chunkProgress.chunk} / {chunkProgress.total} chunks{etaText ? ` — ${etaText}` : ''}
          </span>
        </div>
      {:else}
        <span class="processing-dot"></span>
        Processing audio...
      {/if}
    </div>
  {/if}

  {#if pipelineRunning}
    <div class="processing-banner pipeline-banner">
      <div class="pipeline-header">
        <span class="processing-dot"></span>
        <strong>Processing All</strong> — {phaseLabels[pipelinePhase ?? ''] ?? 'Starting...'}
      </div>
      {#if pipelinePhase === 'transcription' && chunkProgress}
        <div class="progress-section">
          <div class="progress-bar">
            <div class="progress-fill" style="width: {progressPercent}%"></div>
          </div>
          <span class="progress-label">
            {chunkProgress.chunk} / {chunkProgress.total} chunks{etaText ? ` — ${etaText}` : ''}
          </span>
        </div>
      {/if}
      <div class="pipeline-phases">
        {#each ['transcription', 'diarization', 'summaries', 'image_generation'] as p}
          <span class="phase-indicator" class:active={pipelinePhase === p} class:done={
            pipelinePhase != null && ['transcription', 'diarization', 'summaries', 'image_generation'].indexOf(p) < ['transcription', 'diarization', 'summaries', 'image_generation'].indexOf(pipelinePhase)
          }>
            {phaseLabels[p]?.replace('...', '') ?? p}
          </span>
        {/each}
      </div>
    </div>
  {/if}

  {#if pipelineResult}
    <div class="pipeline-summary">
      <strong>Pipeline Complete</strong>
      <div class="summary-stats">
        <span>{pipelineResult.segments_count} transcript segments</span>
        <span>{pipelineResult.summaries_count} summaries generated</span>
        <span>{pipelineResult.image ? 'Session art created' : 'No image generated'}</span>
      </div>
      <button class="btn btn-sm" onclick={dismissPipelineResult}>Dismiss</button>
    </div>
  {/if}

  <input
    type="file"
    accept="audio/*"
    class="hidden-input"
    bind:this={fileInput}
    onchange={handleFileSelected}
  />

  <label class="speakers-label">Speakers
    <input type="number" min="1" max="10" bind:value={numSpeakers} class="speakers-input" disabled={busy} />
  </label>

  <div class="controls">
    {#if recordingState === 'idle' && !busy}
      <button class="btn btn-record" onclick={startRecording} disabled={!canRecord || isLocked}>
        Start Recording
      </button>
      <button class="btn" onclick={triggerFileInput} disabled={!canUpload || isLocked}>
        Upload Audio
      </button>
      {#if hasAudio && canProcessAll}
        <button class="btn btn-process-all" onclick={startProcessAll}>
          Process All
        </button>
      {/if}
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
  .btn-sm { padding: 0.3rem 0.75rem; font-size: 0.8rem; }

  .btn-process-all {
    background: var(--success);
    border-color: var(--success);
    color: #fff;
  }

  .btn-process-all:hover:not(:disabled) {
    filter: brightness(1.1);
  }

  .lock-msg {
    color: var(--text-muted);
    font-size: 0.8rem;
    font-style: italic;
  }

  .hidden-input {
    display: none;
  }

  .processing-banner {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    padding: 0.6rem 1rem;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 6px;
    margin-bottom: 1rem;
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .pipeline-banner {
    flex-direction: column;
    align-items: stretch;
    gap: 0.75rem;
  }

  .pipeline-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
  }

  .pipeline-phases {
    display: flex;
    gap: 0.5rem;
    flex-wrap: wrap;
  }

  .phase-indicator {
    font-size: 0.75rem;
    padding: 0.2rem 0.5rem;
    border-radius: 12px;
    background: var(--bg-hover);
    color: var(--text-muted);
  }

  .phase-indicator.active {
    background: var(--accent);
    color: #fff;
    font-weight: 600;
  }

  .phase-indicator.done {
    background: var(--success);
    color: #fff;
  }

  .processing-dot {
    width: 8px;
    height: 8px;
    background: var(--accent);
    border-radius: 50%;
    flex-shrink: 0;
    animation: processingPulse 1s ease-in-out infinite;
  }

  @keyframes processingPulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .progress-section {
    width: 100%;
  }

  .progress-bar {
    width: 100%;
    height: 12px;
    background: var(--bg-hover);
    border: 1px solid var(--border);
    border-radius: 6px;
    overflow: hidden;
    margin-bottom: 0.5rem;
  }

  .progress-fill {
    height: 100%;
    background: var(--accent);
    border-radius: 5px;
    transition: width 0.4s ease;
    min-width: 4px;
  }

  .progress-label {
    font-size: 0.85rem;
    color: var(--text-muted);
  }

  .speakers-label {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-size: 0.85rem;
    color: var(--text-muted);
    margin-bottom: 1rem;
  }

  .speakers-input {
    width: 3.5rem;
    padding: 0.4rem 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-size: 0.85rem;
    text-align: center;
  }

  .pipeline-summary {
    background: var(--bg-surface);
    border: 1px solid var(--success);
    border-radius: 6px;
    padding: 1rem;
    margin-bottom: 1rem;
  }

  .pipeline-summary strong {
    color: var(--success);
  }

  .summary-stats {
    display: flex;
    gap: 1.5rem;
    margin: 0.5rem 0;
    font-size: 0.85rem;
    color: var(--text-secondary);
  }
</style>
