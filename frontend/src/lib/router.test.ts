import { describe, it, expect, beforeEach } from 'vitest';
import { parseHash, navigate, matchRoute } from './router.svelte';

describe('parseHash', () => {
  beforeEach(() => {
    window.location.hash = '';
  });

  it('returns "/" when hash is empty', () => {
    window.location.hash = '';
    const result = parseHash();
    expect(result.path).toBe('/');
    expect(result.params).toEqual({});
  });

  it('returns the hash path without the # prefix', () => {
    window.location.hash = '#/campaigns/1';
    const result = parseHash();
    expect(result.path).toBe('/campaigns/1');
  });

  it('returns "/" when hash is just "#"', () => {
    window.location.hash = '#';
    const result = parseHash();
    expect(result.path).toBe('/');
  });
});

describe('navigate', () => {
  it('sets the window.location.hash', () => {
    navigate('/campaigns/42');
    expect(window.location.hash).toBe('#/campaigns/42');
  });

  it('navigates to root path', () => {
    navigate('/');
    expect(window.location.hash).toBe('#/');
  });
});

describe('matchRoute', () => {
  const routes = [
    { pattern: '/', name: 'campaigns' },
    { pattern: '/campaigns/:id', name: 'campaign' },
    { pattern: '/campaigns/:id/roster', name: 'roster' },
    { pattern: '/sessions/:id', name: 'session' },
    { pattern: '/settings', name: 'settings' },
  ];

  it('matches root path', () => {
    const result = matchRoute('/', routes);
    expect(result).toEqual({ name: 'campaigns', params: {} });
  });

  it('matches campaign path and extracts id param', () => {
    const result = matchRoute('/campaigns/42', routes);
    expect(result).toEqual({ name: 'campaign', params: { id: '42' } });
  });

  it('matches roster path and extracts id param', () => {
    const result = matchRoute('/campaigns/7/roster', routes);
    expect(result).toEqual({ name: 'roster', params: { id: '7' } });
  });

  it('matches session path and extracts id param', () => {
    const result = matchRoute('/sessions/123', routes);
    expect(result).toEqual({ name: 'session', params: { id: '123' } });
  });

  it('matches settings path with no params', () => {
    const result = matchRoute('/settings', routes);
    expect(result).toEqual({ name: 'settings', params: {} });
  });

  it('returns null for unmatched paths', () => {
    const result = matchRoute('/unknown/path', routes);
    expect(result).toBeNull();
  });

  it('returns null for partial matches', () => {
    const result = matchRoute('/campaigns', routes);
    expect(result).toBeNull();
  });

  it('does not match extra path segments', () => {
    const result = matchRoute('/settings/extra', routes);
    expect(result).toBeNull();
  });

  it('handles multiple params in a single route', () => {
    const multiParamRoutes = [
      { pattern: '/campaigns/:cid/sessions/:sid', name: 'campaign-session' },
    ];
    const result = matchRoute('/campaigns/1/sessions/2', multiParamRoutes);
    expect(result).toEqual({
      name: 'campaign-session',
      params: { cid: '1', sid: '2' },
    });
  });

  it('matches the first matching route', () => {
    const overlappingRoutes = [
      { pattern: '/a/:id', name: 'first' },
      { pattern: '/a/:id', name: 'second' },
    ];
    const result = matchRoute('/a/1', overlappingRoutes);
    expect(result?.name).toBe('first');
  });
});
