function getInitialTheme(): 'dark' | 'light' {
  try {
    const stored = localStorage.getItem('theme');
    if (stored === 'dark' || stored === 'light') return stored;
  } catch {
    // localStorage unavailable
  }
  return 'dark';
}

export const theme = $state({ current: getInitialTheme() });

$effect.root(() => {
  $effect(() => {
    document.documentElement.dataset.theme = theme.current;
    try {
      localStorage.setItem('theme', theme.current);
    } catch {
      // localStorage unavailable
    }
  });
});

export function toggleTheme() {
  theme.current = theme.current === 'dark' ? 'light' : 'dark';
}
