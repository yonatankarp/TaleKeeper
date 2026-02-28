/** Simple hash-based router for Svelte 5. */

export type Route = {
  pattern: RegExp;
  params: string[];
};

export function parseHash(): { path: string; params: Record<string, string> } {
  const hash = window.location.hash.slice(1) || '/';
  return { path: hash, params: {} };
}

export function navigate(path: string) {
  window.location.hash = path;
}

export function matchRoute(
  path: string,
  routes: Array<{ pattern: string; name: string }>
): { name: string; params: Record<string, string> } | null {
  for (const route of routes) {
    const paramNames: string[] = [];
    const regexStr = route.pattern.replace(/:(\w+)/g, (_match, name) => {
      paramNames.push(name);
      return '([^/]+)';
    });
    const regex = new RegExp(`^${regexStr}$`);
    const match = path.match(regex);
    if (match) {
      const params: Record<string, string> = {};
      paramNames.forEach((name, i) => {
        params[name] = match[i + 1];
      });
      return { name: route.name, params };
    }
  }
  return null;
}
