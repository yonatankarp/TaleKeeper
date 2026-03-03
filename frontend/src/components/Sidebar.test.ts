import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue([]),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
}));

vi.mock('../lib/router.svelte', () => ({
  navigate: vi.fn(),
  parseHash: vi.fn(() => ({ path: '/', params: {} })),
  matchRoute: vi.fn(),
}));

vi.mock('../lib/theme.svelte', () => ({
  theme: { current: 'dark' },
  toggleTheme: vi.fn(),
}));

import { api } from '../lib/api';
import { navigate } from '../lib/router.svelte';
import Sidebar from './Sidebar.svelte';

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('Sidebar', () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders the TaleKeeper logo/title', async () => {
    render(Sidebar);
    await flush();
    expect(screen.getByText('TaleKeeper')).toBeInTheDocument();
  });

  it('renders campaign list after loading', async () => {
    vi.mocked(api.get).mockResolvedValue([
      { id: 1, name: 'Dragon Campaign' },
      { id: 2, name: 'Pirate Campaign' },
    ]);
    render(Sidebar);
    await flush();
    expect(screen.getByText('Dragon Campaign')).toBeInTheDocument();
    expect(screen.getByText('Pirate Campaign')).toBeInTheDocument();
  });

  it('renders theme toggle button', async () => {
    render(Sidebar);
    await flush();
    const themeBtn = screen.getByText(/Light mode|Dark mode/);
    expect(themeBtn).toBeInTheDocument();
  });

  it('renders settings link', async () => {
    render(Sidebar);
    await flush();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('clicking logo navigates to root', async () => {
    render(Sidebar);
    await flush();
    const logo = screen.getByText('TaleKeeper');
    await fireEvent.click(logo);
    expect(navigate).toHaveBeenCalledWith('/');
  });
});
