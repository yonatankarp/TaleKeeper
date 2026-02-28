<script lang="ts">
  import Sidebar from './components/Sidebar.svelte';
  import CampaignList from './routes/CampaignList.svelte';
  import CampaignDashboard from './routes/CampaignDashboard.svelte';
  import SessionDetail from './routes/SessionDetail.svelte';
  import RosterPage from './routes/RosterPage.svelte';
  import SettingsPage from './routes/SettingsPage.svelte';
  import SetupWizard from './components/SetupWizard.svelte';
  import { matchRoute, navigate } from './lib/router.svelte';
  import { api } from './lib/api';
  import './lib/theme.svelte';

  const routes = [
    { pattern: '/', name: 'campaigns' },
    { pattern: '/campaigns/:id', name: 'campaign' },
    { pattern: '/campaigns/:id/roster', name: 'roster' },
    { pattern: '/sessions/:id', name: 'session' },
    { pattern: '/settings', name: 'settings' },
  ];

  let currentPath = $state(window.location.hash.slice(1) || '/');
  let matched = $derived(matchRoute(currentPath, routes));
  let showWizard = $state(false);
  let globalError = $state<string | null>(null);

  // Breadcrumb state
  type Crumb = { label: string; path: string | null };
  let breadcrumbs = $state<Crumb[]>([]);

  function onHashChange() {
    currentPath = window.location.hash.slice(1) || '/';
  }

  async function updateBreadcrumbs() {
    if (!matched || matched.name === 'campaigns') {
      breadcrumbs = [];
      return;
    }

    const crumbs: Crumb[] = [{ label: 'Campaigns', path: '/' }];

    if (matched.name === 'settings') {
      crumbs.push({ label: 'Settings', path: null });
    } else if (matched.name === 'campaign') {
      try {
        const campaign = await api.get<{ name: string }>(`/campaigns/${matched.params.id}`);
        crumbs.push({ label: campaign.name, path: null });
      } catch {
        crumbs.push({ label: 'Campaign', path: null });
      }
    } else if (matched.name === 'roster') {
      try {
        const campaign = await api.get<{ name: string }>(`/campaigns/${matched.params.id}`);
        crumbs.push({ label: campaign.name, path: `/campaigns/${matched.params.id}` });
        crumbs.push({ label: 'Roster', path: null });
      } catch {
        crumbs.push({ label: 'Roster', path: null });
      }
    } else if (matched.name === 'session') {
      try {
        const session = await api.get<{ name: string; campaign_id: number }>(`/sessions/${matched.params.id}`);
        const campaign = await api.get<{ name: string }>(`/campaigns/${session.campaign_id}`);
        crumbs.push({ label: campaign.name, path: `/campaigns/${session.campaign_id}` });
        crumbs.push({ label: session.name, path: null });
      } catch {
        crumbs.push({ label: 'Session', path: null });
      }
    }

    breadcrumbs = crumbs;
  }

  async function checkFirstRun() {
    try {
      const status = await api.get<{ is_first_run: boolean }>('/setup-status');
      if (status.is_first_run) {
        showWizard = true;
      }
    } catch {
      // Server not ready yet, ignore
    }
  }

  // Global error handler for unhandled promise rejections
  function handleError(event: PromiseRejectionEvent) {
    globalError = event.reason?.message ?? 'An unexpected error occurred';
    setTimeout(() => { globalError = null; }, 5000);
  }

  $effect(() => { checkFirstRun(); });
  $effect(() => { matched; updateBreadcrumbs(); });
</script>

<svelte:window onhashchange={onHashChange} onunhandledrejection={handleError} />

{#if showWizard}
  <SetupWizard onDismiss={() => (showWizard = false)} />
{/if}

{#if globalError}
  <div class="global-toast error-toast">{globalError}</div>
{/if}

<div class="app-layout">
  <Sidebar />

  <main class="main-content">
    {#if breadcrumbs.length > 0}
      <nav class="breadcrumbs">
        {#each breadcrumbs as crumb, i}
          {#if i > 0}
            <span class="separator">/</span>
          {/if}
          {#if crumb.path !== null}
            <button class="crumb-link" onclick={() => navigate(crumb.path!)}>{crumb.label}</button>
          {:else}
            <span class="crumb-current">{crumb.label}</span>
          {/if}
        {/each}
      </nav>
    {/if}

    {#if !matched || matched.name === 'campaigns'}
      <CampaignList />
    {:else if matched.name === 'campaign'}
      <CampaignDashboard campaignId={Number(matched.params.id)} />
    {:else if matched.name === 'roster'}
      <RosterPage campaignId={Number(matched.params.id)} />
    {:else if matched.name === 'session'}
      <SessionDetail sessionId={Number(matched.params.id)} />
    {:else if matched.name === 'settings'}
      <SettingsPage />
    {/if}
  </main>
</div>

<style>
  :global(body) {
    margin: 0;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg-body);
    color: var(--text);
  }

  .app-layout {
    display: flex;
    height: 100vh;
  }

  .main-content {
    flex: 1;
    padding: 2rem;
    overflow-y: auto;
  }

  .breadcrumbs {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    margin-bottom: 1rem;
    font-size: 0.85rem;
  }

  .crumb-link {
    background: none;
    border: none;
    color: var(--accent);
    cursor: pointer;
    padding: 0;
    font: inherit;
    font-size: 0.85rem;
  }

  .crumb-link:hover {
    text-decoration: underline;
  }

  .separator {
    color: var(--text-muted);
  }

  .crumb-current {
    color: var(--text-muted);
  }

  .global-toast {
    position: fixed;
    top: 1rem;
    right: 1rem;
    padding: 0.75rem 1.5rem;
    border-radius: 8px;
    z-index: 200;
    font-size: 0.9rem;
    animation: slideIn 0.2s ease;
  }

  .error-toast {
    background: var(--error-bg);
    border: 1px solid var(--accent);
    color: var(--accent);
  }

  @keyframes slideIn {
    from { opacity: 0; transform: translateX(20px); }
    to { opacity: 1; transform: translateX(0); }
  }
</style>
