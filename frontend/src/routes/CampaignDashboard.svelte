<script lang="ts">
  import { api } from '../lib/api';
  import { navigate } from '../lib/router.svelte';

  type Props = { campaignId: number };
  let { campaignId }: Props = $props();

  type Campaign = { id: number; name: string; description: string };
  type Session = { id: number; name: string; date: string; status: string };
  type Dashboard = { session_count: number; total_recorded_time: number; most_recent_session_date: string | null };

  let campaign = $state<Campaign | null>(null);
  let sessions = $state<Session[]>([]);
  let dashboard = $state<Dashboard | null>(null);
  let showNewSession = $state(false);
  let newSessionName = $state('');
  let newSessionDate = $state(new Date().toISOString().split('T')[0]);

  async function load() {
    [campaign, sessions, dashboard] = await Promise.all([
      api.get<Campaign>(`/campaigns/${campaignId}`),
      api.get<Session[]>(`/campaigns/${campaignId}/sessions`),
      api.get<Dashboard>(`/campaigns/${campaignId}/dashboard`),
    ]);
  }

  async function createSession() {
    if (!newSessionName.trim()) return;
    await api.post(`/campaigns/${campaignId}/sessions`, {
      name: newSessionName,
      date: newSessionDate,
    });
    newSessionName = '';
    showNewSession = false;
    await load();
  }

  async function deleteSession(id: number) {
    if (!confirm('Delete this session and all its data?')) return;
    await api.del(`/sessions/${id}`);
    await load();
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
</script>

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
        <button class="btn" onclick={() => navigate(`/campaigns/${campaignId}/roster`)}>Roster</button>
        <button class="btn btn-primary" onclick={() => (showNewSession = true)}>New Session</button>
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
        <input type="text" placeholder="Session name" bind:value={newSessionName} />
        <input type="date" bind:value={newSessionDate} />
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
            <button class="btn btn-sm btn-danger" onclick={() => deleteSession(s.id)}>Delete</button>
          </div>
        </div>
      {/each}
    </div>

    {#if sessions.length === 0}
      <p class="empty">No sessions yet. Start your first session!</p>
    {/if}
  {/if}
</div>

<style>
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

  .card { background: var(--bg-surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; }
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
  .btn-danger { color: var(--accent); }
  .btn-sm { padding: 0.25rem 0.75rem; font-size: 0.8rem; }
  .btn-group { display: flex; gap: 0.5rem; }

  .empty { text-align: center; color: var(--text-muted); margin-top: 2rem; }
</style>
