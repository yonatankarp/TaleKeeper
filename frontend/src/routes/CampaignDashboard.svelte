<script lang="ts">
  import { api } from '../lib/api';
  import { navigate } from '../lib/router.svelte';
  import LanguageSelect from '../components/LanguageSelect.svelte';
  import Spinner from '../components/Spinner.svelte';
  import ConfirmDialog from '../components/ConfirmDialog.svelte';

  type Props = { campaignId: number };
  let { campaignId }: Props = $props();

  type Campaign = { id: number; name: string; description: string; language: string };
  type Session = { id: number; name: string; date: string; status: string; audio_path: string | null };
  type Dashboard = { session_count: number; total_recorded_time: number; most_recent_session_date: string | null };

  let campaign = $state<Campaign | null>(null);
  let sessions = $state<Session[]>([]);
  let dashboard = $state<Dashboard | null>(null);
  let pageLoading = $state(true);
  let showNewSession = $state(false);
  let newSessionName = $state('');
  let newSessionDate = $state(new Date().toISOString().split('T')[0]);
  let newSessionLang = $state('en');
  let confirmDeleteSessionId = $state<number | null>(null);
  let confirmDeleteCampaign = $state(false);
  let sessionNameError = $state(false);

  async function load() {
    [campaign, sessions, dashboard] = await Promise.all([
      api.get<Campaign>(`/campaigns/${campaignId}`),
      api.get<Session[]>(`/campaigns/${campaignId}/sessions`),
      api.get<Dashboard>(`/campaigns/${campaignId}/dashboard`),
    ]);
    pageLoading = false;
  }

  async function createSession() {
    if (!newSessionName.trim()) {
      sessionNameError = true;
      return;
    }
    sessionNameError = false;
    await api.post(`/campaigns/${campaignId}/sessions`, {
      name: newSessionName,
      date: newSessionDate,
      language: newSessionLang,
    });
    newSessionName = '';
    showNewSession = false;
    await load();
  }

  async function deleteSession(id: number) {
    await api.del(`/sessions/${id}`);
    confirmDeleteSessionId = null;
    await load();
  }

  async function deleteCampaign() {
    await api.del(`/campaigns/${campaignId}`);
    confirmDeleteCampaign = false;
    navigate('/');
  }

  function formatTime(seconds: number): string {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    if (h > 0) return `${h}h ${m}m`;
    return `${m}m`;
  }

  function statusBadgeClass(status: string): string {
    const classes: Record<string, string> = {
      draft: 'badge-draft',
      recording: 'badge-recording',
      transcribing: 'badge-transcribing',
      completed: 'badge-completed',
    };
    return classes[status] ?? '';
  }

  $effect(() => { load(); });

  $effect(() => {
    if (campaign) {
      newSessionLang = campaign.language;
    }
  });
</script>

{#if pageLoading}
  <div class="loading"><Spinner /> Loading campaign...</div>
{:else}
<div class="page">
  {#if campaign}
    <div class="page-header">
      <div>
        <h2>{campaign.name}</h2>
        {#if campaign.description}
          <p class="desc">{campaign.description}</p>
        {/if}
      </div>
      <div class="btn-group">
        <button class="btn btn-icon" onclick={() => navigate(`/campaigns/${campaignId}/roster`)}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 17.5L3 6V3h3l11.5 11.5"/><path d="M13 19l6-6"/><path d="M16 16l4 4"/><path d="M9.5 6.5L21 18v3h-3L6.5 9.5"/><path d="M11 5l-6 6"/><path d="M8 8L4 4"/></svg> Party</button>
        {#if sessions.length > 0}
          <button class="btn" onclick={() => navigate(`/sessions/${sessions[0].id}`)}>Continue Last Session</button>
        {/if}
        <button class="btn btn-primary" onclick={() => (showNewSession = true)}>
          {sessions.length === 0 ? 'Start First Session' : 'New Session'}
        </button>
        <button class="btn btn-danger" onclick={() => (confirmDeleteCampaign = true)}>Delete Campaign</button>
      </div>
    </div>

    {#if dashboard}
      <div class="stats">
        <div class="stat-card">
          <span class="stat-value">{dashboard.session_count}</span>
          <span class="stat-label">Sessions</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{formatTime(dashboard.total_recorded_time)}</span>
          <span class="stat-label">Recorded</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{dashboard.most_recent_session_date ?? 'N/A'}</span>
          <span class="stat-label">Last Session</span>
        </div>
      </div>
    {/if}

    {#if showNewSession}
      <div class="card form-card">
        <input type="text" placeholder="Session name" bind:value={newSessionName} class:input-error={sessionNameError} oninput={() => (sessionNameError = false)} />
        {#if sessionNameError}<p class="field-error">Session name is required</p>{/if}
        <input type="date" bind:value={newSessionDate} />
        <label class="field-label">Language</label>
        <LanguageSelect value={newSessionLang} onchange={(code) => (newSessionLang = code)} />
        <div class="btn-group">
          <button class="btn btn-primary" onclick={createSession}>Create</button>
          <button class="btn" onclick={() => (showNewSession = false)}>Cancel</button>
        </div>
      </div>
    {/if}

    <h3>Sessions</h3>
    <div class="session-list">
      {#each sessions as s}
        <div class="card session-card">
          <button class="session-info" onclick={() => navigate(`/sessions/${s.id}`)}>
            <strong>{s.name}</strong>
            <span class="session-date">{s.date}</span>
          </button>
          <div class="session-actions">
            <span class="badge {statusBadgeClass(s.status)}">{s.status}</span>
            {#if s.audio_path}
              <span class="badge badge-audio">Audio</span>
            {/if}
            <button class="btn btn-sm btn-danger" onclick={() => (confirmDeleteSessionId = s.id)}>Delete</button>
          </div>
        </div>
      {/each}
    </div>

    {#if sessions.length === 0}
      <p class="empty">No sessions yet. Create a session to begin recording your next game.</p>
    {/if}
  {/if}
</div>
{/if}

{#if confirmDeleteSessionId !== null}
  <ConfirmDialog
    title="Delete Session"
    message="This will delete this session and all its audio, transcript, and summaries."
    confirmLabel="Delete"
    onconfirm={() => deleteSession(confirmDeleteSessionId!)}
    oncancel={() => (confirmDeleteSessionId = null)}
  />
{/if}

{#if confirmDeleteCampaign}
  <ConfirmDialog
    title="Delete Campaign"
    message="This will permanently delete this campaign and all its sessions, transcripts, and audio. This cannot be undone."
    confirmLabel="Delete"
    onconfirm={deleteCampaign}
    oncancel={() => (confirmDeleteCampaign = false)}
  />
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
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.5rem;
  }

  .desc { color: var(--text-secondary); margin: 0.25rem 0 0; }

  .stats {
    display: flex;
    gap: 1rem;
    margin-bottom: 2rem;
  }

  .stat-card {
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 1rem 1.5rem;
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 120px;
  }

  .stat-value { font-size: 1.5rem; font-weight: bold; color: var(--accent); }
  .stat-label { font-size: 0.75rem; color: var(--text-muted); text-transform: uppercase; }

  .session-list { display: flex; flex-direction: column; gap: 0.5rem; }

  .session-card {
    display: flex;
    justify-content: space-between;
    align-items: center;
    background: var(--bg-surface);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem 1rem;
  }

  .session-info {
    cursor: pointer;
    background: none;
    border: none;
    color: inherit;
    font: inherit;
    text-align: left;
    padding: 0;
    display: flex;
    align-items: center;
  }

  .session-info:hover strong { color: var(--accent); }
  .session-date { color: var(--text-muted); margin-left: 1rem; font-size: 0.85rem; }

  .session-actions { display: flex; align-items: center; gap: 0.75rem; }

  .badge {
    font-size: 0.7rem;
    padding: 0.2rem 0.5rem;
    border-radius: 12px;
    text-transform: uppercase;
    font-weight: 600;
  }

  .badge-draft { background: var(--badge-dark); color: var(--text-muted); }
  .badge-recording { background: var(--accent); color: #fff; }
  .badge-transcribing { background: var(--warning); color: var(--bg-body); }
  .badge-completed { background: var(--success); color: #fff; }
  .badge-audio { background: var(--btn-blue); color: #fff; }

  .card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; transition: box-shadow 0.2s ease; }
  .card:hover { box-shadow: 0 0 8px rgba(212, 164, 56, 0.15); }
  .form-card { margin-bottom: 1.5rem; }

  input {
    width: 100%;
    padding: 0.5rem;
    margin-bottom: 0.5rem;
    background: var(--bg-input);
    border: 1px solid var(--border);
    border-radius: 4px;
    color: var(--text);
    font-family: inherit;
    box-sizing: border-box;
  }

  .btn {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border);
    border-radius: 4px;
    background: var(--bg-surface);
    color: var(--text);
    cursor: pointer;
    font-size: 0.85rem;
  }

  .btn:hover { background: var(--bg-hover); }
  .btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; }
  .btn-primary:hover { background: var(--accent-hover); }
  .btn-danger { color: var(--danger); }
  .btn-sm { padding: 0.25rem 0.75rem; font-size: 0.8rem; }
  .btn-icon { display: inline-flex; align-items: center; gap: 0.35rem; }
  .btn-group { display: flex; gap: 0.5rem; }

  .field-label {
    display: block;
    font-size: 0.8rem;
    color: var(--text-muted);
    margin-bottom: 0.25rem;
  }

  .input-error { border-color: var(--danger) !important; }
  .field-error { color: var(--danger); font-size: 0.8rem; margin: -0.25rem 0 0.5rem; }

  .empty { text-align: center; color: var(--text-muted); margin-top: 2rem; }
</style>
