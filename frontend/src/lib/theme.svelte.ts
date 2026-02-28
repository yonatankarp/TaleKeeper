export const theme = $state({
  current: (localStorage.getItem('theme') as 'dark' | 'light') ?? 'dark',
});

$effect(() => {
  document.documentElement.dataset.theme = theme.current;
  localStorage.setItem('theme', theme.current);
});

export function toggleTheme() {
  theme.current = theme.current === 'dark' ? 'light' : 'dark';
}
