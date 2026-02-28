<script lang="ts">
  import { api } from '../lib/api';
  import { navigate } from '../lib/router.svelte';
  import { theme, toggleTheme } from '../lib/theme.svelte';

  type Campaign = { id: number; name: string };

  let campaigns = $state<Campaign[]>([]);
  let currentPath = $state(window.location.hash.slice(1) || '/');
  let sessionCampaignId = $state<number | null>(null);

  async function load() {
    campaigns = await api.get<Campaign[]>('/campaigns');
    // When viewing a session, resolve its parent campaign for sidebar highlighting
    const sessionMatch = currentPath.match(/^\/sessions\/(\d+)/);
    if (sessionMatch) {
      try {
        const session = await api.get<{ campaign_id: number }>(`/sessions/${sessionMatch[1]}`);
        sessionCampaignId = session.campaign_id;
      } catch {
        sessionCampaignId = null;
      }
    } else {
      sessionCampaignId = null;
    }
  }

  // Reload campaigns on every route change so sidebar stays in sync
  $effect(() => {
    const onHashChange = () => {
      currentPath = window.location.hash.slice(1) || '/';
      load();
    };
    window.addEventListener('hashchange', onHashChange);
    load();
    return () => window.removeEventListener('hashchange', onHashChange);
  });

  function go(path: string) {
    navigate(path);
  }

  function isCampaignActive(campaignId: number): boolean {
    return currentPath === `/campaigns/${campaignId}`
      || currentPath.startsWith(`/campaigns/${campaignId}/`)
      || sessionCampaignId === campaignId;
  }

  let isSettingsActive = $derived(currentPath === '/settings');
</script>

<aside class="sidebar">
  <div class="sidebar-header">
    <button class="logo" onclick={() => go('/')}>
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><polygon points="12 2 22 8.5 22 15.5 12 22 2 15.5 2 8.5"/><line x1="12" y1="2" x2="12" y2="22"/><line x1="22" y1="8.5" x2="2" y2="15.5"/><line x1="2" y1="8.5" x2="22" y2="15.5"/></svg>
      TaleKeeper
    </button>
  </div>

  <nav>
    <h3 class="section-header"><svg width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg> Campaigns</h3>
    <ul>
      {#each campaigns as c}
        <li>
          <button
            class="nav-link"
            class:active={isCampaignActive(c.id)}
            onclick={() => go(`/campaigns/${c.id}`)}
          >
            {c.name}
          </button>
        </li>
      {/each}
    </ul>
  </nav>

  <div class="sidebar-footer">
    <button class="nav-link theme-toggle" onclick={toggleTheme}>
      {theme.current === 'dark' ? '☀️ Light mode' : '🌙 Dark mode'}
    </button>
    <button class="nav-link settings-link" class:active={isSettingsActive} onclick={() => go('/settings')}><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 00.33 1.82l.06.06a2 2 0 010 2.83 2 2 0 01-2.83 0l-.06-.06a1.65 1.65 0 00-1.82-.33 1.65 1.65 0 00-1 1.51V21a2 2 0 01-4 0v-.09A1.65 1.65 0 009 19.4a1.65 1.65 0 00-1.82.33l-.06.06a2 2 0 01-2.83-2.83l.06-.06A1.65 1.65 0 004.68 15a1.65 1.65 0 00-1.51-1H3a2 2 0 010-4h.09A1.65 1.65 0 004.6 9a1.65 1.65 0 00-.33-1.82l-.06-.06a2 2 0 012.83-2.83l.06.06A1.65 1.65 0 009 4.68a1.65 1.65 0 001-1.51V3a2 2 0 014 0v.09a1.65 1.65 0 001 1.51 1.65 1.65 0 001.82-.33l.06-.06a2 2 0 012.83 2.83l-.06.06A1.65 1.65 0 0019.4 9a1.65 1.65 0 001.51 1H21a2 2 0 010 4h-.09a1.65 1.65 0 00-1.51 1z"/></svg> Settings</button>
  </div>
</aside>

<style>
  .sidebar {
    width: 250px;
    background: var(--bg-surface);
    display: flex;
    flex-direction: column;
    border-right: 1px solid var(--border);
  }

  .sidebar-header {
    padding: 1rem;
    border-bottom: 1px solid var(--border);
  }

  .logo {
    margin: 0;
    font-size: 1.4rem;
    font-weight: bold;
    font-family: var(--font-heading);
    color: var(--accent);
    cursor: pointer;
    background: none;
    border: none;
    padding: 0;
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  nav {
    flex: 1;
    padding: 1rem;
    overflow-y: auto;
  }

  nav h3 {
    font-size: 0.75rem;
    text-transform: uppercase;
    color: var(--text-muted);
    margin: 0 0 0.5rem;
  }

  .section-header {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  .section-header svg {
    color: var(--accent);
  }

  .settings-link {
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }

  ul {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .nav-link {
    display: block;
    width: 100%;
    background: none;
    border: none;
    border-left: 3px solid transparent;
    color: var(--text);
    padding: 0.5rem;
    text-align: left;
    cursor: pointer;
    border-radius: 4px;
    font-size: 0.9rem;
  }

  .nav-link:hover {
    background: var(--bg-hover);
  }

  .nav-link.active {
    border-left-color: var(--accent);
    background: var(--bg-hover);
    color: var(--accent);
    font-weight: 600;
  }

  .sidebar-footer {
    padding: 1rem;
    border-top: 1px solid var(--border);
  }
</style>
