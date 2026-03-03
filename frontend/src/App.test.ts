import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';

vi.mock('./lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
}));

vi.mock('./lib/router.svelte', () => ({
  navigate: vi.fn(),
  parseHash: vi.fn(() => ({ path: '/', params: {} })),
  matchRoute: vi.fn((path: string, routes: Array<{ pattern: string; name: string }>) => {
    for (const route of routes) {
      if (route.pattern === path) return { name: route.name, params: {} };
    }
    return null;
  }),
}));

vi.mock('./lib/wizard.svelte', () => ({
  wizard: {
    get open() { return false; },
    show: vi.fn(),
    hide: vi.fn(),
  },
}));

vi.mock('./lib/theme.svelte', () => ({
  theme: { current: 'dark' },
  toggleTheme: vi.fn(),
}));

import { api } from './lib/api';
import App from './App.svelte';

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('App', () => {
  afterEach(() => {
    cleanup();
    vi.mocked(api.get).mockReset();
  });

  it('renders the app layout', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    window.location.hash = '#/';
    const { container } = render(App);
    await flush();
    const layout = container.querySelector('.app-layout');
    expect(layout).toBeInTheDocument();
  });

  it('renders the sidebar', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    window.location.hash = '#/';
    render(App);
    await flush();
    expect(screen.getByText('TaleKeeper')).toBeInTheDocument();
  });

  it('renders main content area', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    window.location.hash = '#/';
    const { container } = render(App);
    await flush();
    const main = container.querySelector('.main-content');
    expect(main).toBeInTheDocument();
  });

  it('shows campaigns route by default', async () => {
    vi.mocked(api.get).mockResolvedValue([]);
    window.location.hash = '#/';
    render(App);
    await flush();
    // "Campaigns" appears in sidebar nav header and in the CampaignList page heading
    const campaignElements = screen.getAllByText('Campaigns');
    expect(campaignElements).toHaveLength(2);
  });
});
