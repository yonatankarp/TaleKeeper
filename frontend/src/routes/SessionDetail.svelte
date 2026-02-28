<script lang="ts">
  import { api } from '../lib/api';
  import RecordingControls from '../components/RecordingControls.svelte';
  import TranscriptView from '../components/TranscriptView.svelte';
  import AudioPlayer from '../components/AudioPlayer.svelte';
  import SummarySection from '../components/SummarySection.svelte';
  import ExportSection from '../components/ExportSection.svelte';
  import Spinner from '../components/Spinner.svelte';

  type Props = { sessionId: number };
  let { sessionId }: Props = $props();

  type Session = { id: number; campaign_id: number; name: string; date: string; status: string; audio_path: string | null; language: string };

  let session = $state<Session | null>(null);
  let pageLoading = $state(true);
  let activeTab = $state('recording');
  let audioPlayer: AudioPlayer | undefined = $state();

  // Recording badge state
  type RecordingBadgeState = { state: 'idle' | 'recording' | 'paused'; elapsed: number };
  let recordingBadge = $state<RecordingBadgeState>({ state: 'idle', elapsed: 0 });

  async function load() {
    session = await api.get<Session>(`/sessions/${sessionId}`);
    pageLoading = false;
  }

  function handleSegmentClick(startTime: number) {
    audioPlayer?.seekTo(startTime);
  }

  function handleRecordingStateChange(state: 'idle' | 'recording' | 'paused', elapsed: number) {
    recordingBadge = { state, elapsed };
    if (state === 'idle') load();
  }

  function handleKeydown(e: KeyboardEvent) {
    // Suppress shortcuts when focus is in input/textarea/select
    const tag = (e.target as HTMLElement)?.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;

    const tabIndex = Number(e.key) - 1;
    if (tabIndex >= 0 && tabIndex < tabs.length) {
      activeTab = tabs[tabIndex];
    }
  }

  function formatElapsed(s: number): string {
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return [h, m, sec].map((v) => String(v).padStart(2, '0')).join(':');
  }

  $effect(() => { load(); });

  const tabs = ['recording', 'transcript', 'summaries', 'export'] as const;
  const tabLabels: Record<string, string> = {
    recording: 'Recording',
    transcript: 'Transcript',
    summaries: 'Summaries',
    export: 'Export',
  };

  let hasAudio = $derived(session?.audio_path != null);
  let transcriptView: TranscriptView | undefined = $state();

  function handleTranscriptSegment(seg: { text: string; start_time: number; end_time: number }) {
    transcriptView?.addLiveSegment(seg);
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if pageLoading}
  <div class="loading"><Spinner /> Loading session...</div>
{:else}
<div class="page">
  {#if session}
    <div class="page-header">
      <div>
        <div class="header-row">
          <h2>{session.name}</h2>
          {#if recordingBadge.state !== 'idle'}
            <div class="rec-badge">
              <span class="rec-dot" class:pulsing={recordingBadge.state === 'recording'}></span>
              <span class="rec-time">{formatElapsed(recordingBadge.elapsed)}</span>
              <span class="rec-label">{recordingBadge.state === 'recording' ? 'REC' : 'PAUSED'}</span>
            </div>
          {/if}
        </div>
        <span class="meta">{session.date} &middot; {session.status} &middot; {session.language.toUpperCase()}</span>
      </div>
    </div>

    <div class="tab-bar">
      {#each tabs as tab, i}
        <button
          class="tab"
          class:active={activeTab === tab}
          onclick={() => (activeTab = tab)}
        >
          {tabLabels[tab]} <span class="tab-hint">{i + 1}</span>
        </button>
      {/each}
    </div>

    <div class="tab-content">
      <div class:hidden={activeTab !== 'recording'}>
        <RecordingControls sessionId={sessionId} status={session.status} onStatusChange={load} onRecordingStateChange={handleRecordingStateChange} onTranscriptSegment={handleTranscriptSegment} />
      </div>
      <div class:hidden={activeTab !== 'transcript'}>
        {#if hasAudio}
          <AudioPlayer bind:this={audioPlayer} sessionId={sessionId} />
        {/if}
        <TranscriptView
          bind:this={transcriptView}
          sessionId={sessionId}
          isRecording={session.status === 'recording'}
          {hasAudio}
          language={session.language}
          onSegmentClick={handleSegmentClick}
        />
      </div>
      <div class:hidden={activeTab !== 'summaries'}>
        <SummarySection sessionId={sessionId} />
      </div>
      <div class:hidden={activeTab !== 'export'}>
        <ExportSection sessionId={sessionId} />
      </div>
    </div>
  {/if}
</div>
{/if}

<style>
  .loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 0.75rem;
    padding: 3rem;
    color: var(--text-muted);
  }

  .page-header {
    margin-bottom: 1.5rem;
  }

  .header-row {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .rec-badge {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.25rem 0.75rem;
    background: var(--bg-surface);
    border: 1px solid var(--accent);
    border-radius: 16px;
    font-size: 0.8rem;
  }

  .rec-dot {
    width: 8px;
    height: 8px;
    background: var(--accent);
    border-radius: 50%;
  }

  .rec-dot.pulsing {
    animation: pulse 1s ease-in-out infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }

  .rec-time {
    font-family: 'SF Mono', monospace;
    font-weight: 600;
  }

  .rec-label {
    color: var(--accent);
    font-weight: 700;
    text-transform: uppercase;
  }

  .meta { color: var(--text-muted); font-size: 0.85rem; }

  .tab-bar {
    display: flex;
    border-bottom: 2px solid var(--border);
    margin-bottom: 1.5rem;
  }

  .tab {
    padding: 0.75rem 1.25rem;
    background: none;
    border: none;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 0.9rem;
    border-bottom: 2px solid transparent;
    margin-bottom: -2px;
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .tab:hover { color: var(--text); }
  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

  .tab-hint {
    font-size: 0.65rem;
    color: var(--text-faint);
    background: var(--bg-input);
    padding: 0.1rem 0.35rem;
    border-radius: 3px;
    font-weight: 600;
  }

  .hidden { display: none; }
</style>
