<script lang="ts">
  import Sidebar from './components/Sidebar.svelte';
  import CampaignList from './routes/CampaignList.svelte';
  import CampaignDashboard from './routes/CampaignDashboard.svelte';
  import SessionDetail from './routes/SessionDetail.svelte';
  import RosterPage from './routes/RosterPage.svelte';
  import SettingsPage from './routes/SettingsPage.svelte';
  import SetupWizard from './components/SetupWizard.svelte';
  import { matchRoute } from './lib/router.svelte';
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

  function onHashChange() {
    currentPath = window.location.hash.slice(1) || '/';
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
