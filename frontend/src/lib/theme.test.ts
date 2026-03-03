import { describe, it, expect, beforeEach, vi } from 'vitest';

// We need to mock localStorage and matchMedia before importing the module
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] ?? null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get length() {
      return Object.keys(store).length;
    },
    key: vi.fn((_index: number) => null),
  };
})();

Object.defineProperty(window, 'localStorage', { value: localStorageMock });

describe('theme', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.resetModules();
    // Reset matchMedia to prefer dark
    window.matchMedia = vi.fn().mockReturnValue({ matches: false });
  });

  it('defaults to dark when no stored theme and no OS preference', async () => {
    const { theme } = await import('./theme.svelte');
    expect(theme.current).toBe('dark');
  });

  it('reads stored theme from localStorage', async () => {
    localStorageMock.setItem('theme', 'light');
    const { theme } = await import('./theme.svelte');
    expect(theme.current).toBe('light');
  });

  it('detects OS light preference when no stored theme', async () => {
    window.matchMedia = vi.fn().mockReturnValue({ matches: true });
    const { theme } = await import('./theme.svelte');
    expect(theme.current).toBe('light');
  });

  it('toggleTheme switches from dark to light', async () => {
    const { theme, toggleTheme } = await import('./theme.svelte');
    expect(theme.current).toBe('dark');
    toggleTheme();
    expect(theme.current).toBe('light');
  });

  it('toggleTheme switches from light to dark', async () => {
    localStorageMock.setItem('theme', 'light');
    const { theme, toggleTheme } = await import('./theme.svelte');
    expect(theme.current).toBe('light');
    toggleTheme();
    expect(theme.current).toBe('dark');
  });

  it('ignores invalid stored values', async () => {
    localStorageMock.setItem('theme', 'invalid');
    const { theme } = await import('./theme.svelte');
    expect(theme.current).toBe('dark');
  });
});
