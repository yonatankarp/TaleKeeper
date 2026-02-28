<script lang="ts">
  import { api } from '../lib/api';
  import RecordingControls from '../components/RecordingControls.svelte';
  import TranscriptView from '../components/TranscriptView.svelte';
  import AudioPlayer from '../components/AudioPlayer.svelte';
  import SummarySection from '../components/SummarySection.svelte';
  import ExportSection from '../components/ExportSection.svelte';

  type Props = { sessionId: number };
  let { sessionId }: Props = $props();

  type Session = { id: number; campaign_id: number; name: string; date: string; status: string; audio_path: string | null };

  let session = $state<Session | null>(null);
  let activeTab = $state('recording');
  let audioPlayer: AudioPlayer | undefined = $state();

  async function load() {
    session = await api.get<Session>(`/sessions/${sessionId}`);
  }

  function handleSegmentClick(startTime: number) {
    audioPlayer?.seekTo(startTime);
  }

  $effect(() => { load(); });

  const tabs = ['recording', 'transcript', 'summaries', 'export'] as const;

  let hasAudio = $derived(session?.audio_path != null);
</script>

<div class="page">
  {#if session}
    <div class="page-header">
      <div>
        <h2>{session.name}</h2>
        <span class="meta">{session.date} &middot; {session.status}</span>
      </div>
    </div>

    <div class="tab-bar">
      {#each tabs as tab}
        <button
          class="tab"
          class:active={activeTab === tab}
          onclick={() => (activeTab = tab)}
        >
          {tab[0].toUpperCase() + tab.slice(1)}
        </button>
      {/each}
    </div>

    <div class="tab-content">
      {#if activeTab === 'recording'}
        <RecordingControls sessionId={sessionId} status={session.status} onStatusChange={load} />
      {:else if activeTab === 'transcript'}
        {#if hasAudio}
          <AudioPlayer bind:this={audioPlayer} sessionId={sessionId} />
        {/if}
        <TranscriptView
          sessionId={sessionId}
          isRecording={session.status === 'recording'}
          onSegmentClick={handleSegmentClick}
        />
      {:else if activeTab === 'summaries'}
        <SummarySection sessionId={sessionId} />
      {:else if activeTab === 'export'}
        <ExportSection sessionId={sessionId} />
      {/if}
    </div>
  {/if}
</div>

<style>
  .page-header {
    margin-bottom: 1.5rem;
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
  }

  .tab:hover { color: var(--text); }
  .tab.active {
    color: var(--accent);
    border-bottom-color: var(--accent);
  }

</style>
