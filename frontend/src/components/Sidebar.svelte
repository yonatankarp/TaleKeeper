<script lang="ts">
  import { api } from '../lib/api';
  import { navigate } from '../lib/router.svelte';
  import { theme, toggleTheme } from '../lib/theme.svelte';

  type Campaign = { id: number; name: string };

  let campaigns = $state<Campaign[]>([]);

  async function load() {
    campaigns = await api.get<Campaign[]>('/campaigns');
  }

  // Reload campaigns on every route change so sidebar stays in sync
  $effect(() => {
    const onHashChange = () => load();
    window.addEventListener('hashchange', onHashChange);
    load();
    return () => window.removeEventListener('hashchange', onHashChange);
  });

  function go(path: string) {
    navigate(path);
  }
</script>

<aside class="sidebar">
  <div class="sidebar-header">
    <button class="logo" onclick={() => go('/')}>TaleKeeper</button>
  </div>

  <nav>
    <h3>Campaigns</h3>
    <ul>
      {#each campaigns as c}
        <li>
          <button class="nav-link" onclick={() => go(`/campaigns/${c.id}`)}>
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
    <button class="nav-link" onclick={() => go('/settings')}>Settings</button>
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
    color: var(--accent);
    cursor: pointer;
    background: none;
    border: none;
    padding: 0;
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

  .sidebar-footer {
    padding: 1rem;
    border-top: 1px solid var(--border);
  }
</style>
