<script lang="ts">
  import { api } from '../lib/api';
  import RecordingControls from '../components/RecordingControls.svelte';
  import TranscriptView from '../components/TranscriptView.svelte';
  import AudioPlayer from '../components/AudioPlayer.svelte';
  import SummarySection from '../components/SummarySection.svelte';
  import ExportSection from '../components/ExportSection.svelte';
  import IllustrationsSection from '../components/IllustrationsSection.svelte';
  import SpeakerPanel from '../components/SpeakerPanel.svelte';
  import Spinner from '../components/Spinner.svelte';

  type Props = { sessionId: number };
  let { sessionId }: Props = $props();

  type Session = { id: number; campaign_id: number; name: string; date: string; status: string; audio_path: string | null; language: string; session_number: number | null };

  let session = $state<Session | null>(null);
  let pageLoading = $state(true);
  let activeTab = $state('recording');
  let audioPlayer: AudioPlayer | undefined = $state();
  let editingName = $state(false);
  let editNameValue = $state('');
  let regeneratingName = $state(false);

  // Recording badge state
  type RecordingBadgeState = { state: 'idle' | 'recording' | 'paused'; elapsed: number };
  let recordingBadge = $state<RecordingBadgeState>({ state: 'idle', elapsed: 0 });

  async function load() {
    session = await api.get<Session>(`/sessions/${sessionId}`);
    pageLoading = false;
    transcriptView?.load();
  }

  function handleSegmentClick(startTime: number) {
    audioPlayer?.seekTo(startTime);
  }

  function handleRecordingStateChange(state: 'idle' | 'recording' | 'paused', elapsed: number) {
    recordingBadge = { state, elapsed };
    if (state === 'idle') load();
  }

  function startEditName() {
    editNameValue = session?.name ?? '';
    editingName = true;
  }

  async function saveEditName() {
    if (!session || !editNameValue.trim()) return;
    await api.put(`/sessions/${sessionId}`, { name: editNameValue.trim() });
    session.name = editNameValue.trim();
    editingName = false;
  }

  function cancelEditName() {
    editingName = false;
  }

  function handleNameKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') saveEditName();
    else if (e.key === 'Escape') cancelEditName();
  }

  async function regenerateName() {
    regeneratingName = true;
    try {
      const updated = await api.post<Session>(`/sessions/${sessionId}/generate-name`);
      if (session) session.name = updated.name;
    } catch (err) {
      // silently fail — user can try again
    } finally {
      regeneratingName = false;
    }
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

  const tabs = ['recording', 'transcript', 'summaries', 'illustrations', 'export'] as const;
  const tabLabels: Record<string, string> = {
    recording: 'Recording',
    transcript: 'Chronicle',
    summaries: 'Tales',
    illustrations: 'Visions',
    export: 'Export',
  };

  let hasAudio = $derived(session?.audio_path != null);
  let transcriptView: TranscriptView | undefined = $state();
  let exportSection: ExportSection | undefined = $state();

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
          {#if editingName}
            <input
              class="name-edit-input"
              type="text"
              bind:value={editNameValue}
              onkeydown={handleNameKeydown}
              onblur={saveEditName}
            />
          {:else}
            <button class="editable-name" onclick={startEditName} title="Click to edit"><h2>{session.name}</h2></button>
          {/if}
          {#if session.status === 'completed' && !editingName}
            <button class="btn btn-sm btn-regen" onclick={regenerateName} disabled={regeneratingName}>
              {regeneratingName ? 'Generating...' : 'Regenerate Name'}
            </button>
          {/if}
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
          {#if tab === 'recording'}
            <svg class="tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M12 23a1 1 0 01-1-1v-4h2v4a1 1 0 01-1 1zm0-7c-1.5 0-2.5-1-2.5-2.5 0-1 .5-2.3 1.2-3.7.4-.7.8-1.5 1.3-2.5.5 1 .9 1.8 1.3 2.5.7 1.4 1.2 2.7 1.2 3.7 0 1.5-1 2.5-2.5 2.5zM12 2S7 8.5 7 13.5C7 16.5 9.2 19 12 19s5-2.5 5-5.5C17 8.5 12 2 12 2z"/></svg>
          {:else if tab === 'transcript'}
            <svg class="tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 3a2 2 0 012 2v2a2 2 0 01-2 2H7a2 2 0 00-2 2v6a2 2 0 002 2h10a2 2 0 002-2"/><path d="M8 7V5a2 2 0 00-2-2"/><path d="M16 17v2a2 2 0 002 2"/><line x1="8" y1="11" x2="16" y2="11"/><line x1="8" y1="14" x2="13" y2="14"/></svg>
          {:else if tab === 'summaries'}
            <svg class="tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2 3h6a4 4 0 014 4v14a3 3 0 00-3-3H2z"/><path d="M22 3h-6a4 4 0 00-4 4v14a3 3 0 013-3h7z"/></svg>
          {:else if tab === 'illustrations'}
            <svg class="tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="4"/><line x1="12" y1="2" x2="12" y2="4"/><line x1="12" y1="20" x2="12" y2="22"/><line x1="2" y1="12" x2="4" y2="12"/><line x1="20" y1="12" x2="22" y2="12"/></svg>
          {:else if tab === 'export'}
            <svg class="tab-icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="4" width="20" height="16" rx="2"/><path d="M22 7l-10 7L2 7"/></svg>
          {/if}
          {tabLabels[tab]} <span class="tab-hint">{i + 1}</span>
        </button>
      {/each}
    </div>

    <div class="tab-content">
      <div class:hidden={activeTab !== 'recording'}>
        <RecordingControls sessionId={sessionId} campaignId={session.campaign_id} status={session.status} onStatusChange={load} onRecordingStateChange={handleRecordingStateChange} onTranscriptSegment={handleTranscriptSegment} />
      </div>
      <div class:hidden={activeTab !== 'transcript'}>
        {#if session}
          <SpeakerPanel sessionId={sessionId} campaignId={session.campaign_id} hasAudio={hasAudio} onUpdate={() => transcriptView?.load()} />
        {/if}
        {#if hasAudio}
          <AudioPlayer bind:this={audioPlayer} sessionId={sessionId} />
        {/if}
        <TranscriptView
          bind:this={transcriptView}
          sessionId={sessionId}
          campaignId={session.campaign_id}
          isRecording={session.status === 'recording'}
          {hasAudio}
          language={session.language}
          status={session.status}
          onSegmentClick={handleSegmentClick}
        />
      </div>
      <div class:hidden={activeTab !== 'summaries'}>
        <SummarySection sessionId={sessionId} onSummariesChange={() => exportSection?.load()} />
      </div>
      <div class:hidden={activeTab !== 'illustrations'}>
        <IllustrationsSection sessionId={sessionId} />
      </div>
      <div class:hidden={activeTab !== 'export'}>
        <ExportSection bind:this={exportSection} sessionId={sessionId} />
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
    border: 1px solid var(--danger);
    border-radius: 16px;
    font-size: 0.8rem;
  }

  .rec-dot {
    width: 8px;
    height: 8px;
    background: var(--danger);
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
    color: var(--danger);
    font-weight: 700;
    text-transform: uppercase;
  }

  .editable-name {
    cursor: pointer;
    background: none;
    border: none;
    padding: 0;
    color: inherit;
    font: inherit;
    text-align: left;
    border-bottom: 1px dashed transparent;
  }

  .editable-name h2 { margin: 0; }

  .editable-name:hover {
    border-bottom-color: var(--accent);
  }

  .name-edit-input {
    font-size: 1.5rem;
    font-weight: bold;
    background: var(--bg-input);
    border: 1px solid var(--accent);
    border-radius: 4px;
    color: var(--text);
    padding: 0.25rem 0.5rem;
    font-family: inherit;
  }

  .btn-sm {
    padding: 0.25rem 0.75rem;
    font-size: 0.8rem;
  }

  .btn-regen {
    padding: 0.25rem 0.75rem;
    font-size: 0.75rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-surface);
    color: var(--text-muted);
    cursor: pointer;
  }

  .btn-regen:hover { background: var(--bg-hover); color: var(--text); }
  .btn-regen:disabled { opacity: 0.5; cursor: not-allowed; }

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

  .tab-icon { color: var(--accent); flex-shrink: 0; }
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
