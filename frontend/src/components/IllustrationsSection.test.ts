import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import IllustrationsSection from './IllustrationsSection.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn(),
    del: vi.fn(),
  },
  generateImageStream: vi.fn(),
}));

import { api } from '../lib/api';

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('IllustrationsSection', () => {
  afterEach(() => {
    cleanup();
    vi.mocked(api.get).mockReset();
  });

  function setupMocks(images: unknown[] = []) {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve(images);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'ok' });
      return Promise.resolve({});
    });
  }

  it('renders "Generate Scene" button', async () => {
    setupMocks();
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Generate Scene')).toBeInTheDocument();
  });

  it('renders "Generate Image" button', async () => {
    setupMocks();
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Generate Image')).toBeInTheDocument();
  });

  it('shows "No illustrations generated yet" when empty', async () => {
    setupMocks();
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText(/No illustrations generated yet/)).toBeInTheDocument();
  });

  it('shows image provider warning when not available', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve([]);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'error', message: 'GPU unavailable' });
      return Promise.resolve({});
    });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Image provider not available')).toBeInTheDocument();
  });

  it('renders prompt textarea', async () => {
    setupMocks();
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    const textarea = screen.getByPlaceholderText(/Scene description will appear/);
    expect(textarea).toBeInTheDocument();
  });

  it('shows hint about image generation', async () => {
    setupMocks();
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText(/Click "Generate Scene"/)).toBeInTheDocument();
  });

  it('disables Generate Image when image provider is unavailable', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve([]);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'error' });
      return Promise.resolve({});
    });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    const btn = screen.getByText('Generate Image');
    expect(btn).toBeDisabled();
  });

  it('shows images when they exist', async () => {
    const images = [
      { id: 1, prompt: 'A dragon', model_used: 'flux', generated_at: '2025-01-01' },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve(images);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'ok' });
      return Promise.resolve({});
    });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Generated Images')).toBeInTheDocument();
    expect(screen.getByText('A dragon')).toBeInTheDocument();
    expect(screen.getByText('Model: flux')).toBeInTheDocument();
  });

  it('shows Clear All button when images exist', async () => {
    const images = [
      { id: 1, prompt: 'A dragon', model_used: 'flux', generated_at: '2025-01-01' },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve(images);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'ok' });
      return Promise.resolve({});
    });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Clear All')).toBeInTheDocument();
  });

  it('shows Delete button on each image', async () => {
    const images = [
      { id: 1, prompt: 'A dragon', model_used: 'flux', generated_at: '2025-01-01' },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve(images);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'ok' });
      return Promise.resolve({});
    });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });

  it('shows confirm dialog when Delete is clicked on an image', async () => {
    const images = [
      { id: 1, prompt: 'A dragon', model_used: 'flux', generated_at: '2025-01-01' },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve(images);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'ok' });
      return Promise.resolve({});
    });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Delete'));
    expect(screen.getByText('Delete Image')).toBeInTheDocument();
  });

  it('shows confirm dialog when Clear All is clicked', async () => {
    const images = [
      { id: 1, prompt: 'A dragon', model_used: 'flux', generated_at: '2025-01-01' },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve(images);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'ok' });
      return Promise.resolve({});
    });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Clear All'));
    expect(screen.getByText('Clear All Images')).toBeInTheDocument();
  });

  it('calls api.post when Generate Scene is clicked', async () => {
    setupMocks();
    vi.mocked(api.post).mockResolvedValue({ scene_description: 'A dark cave' });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    await fireEvent.click(screen.getByText('Generate Scene'));
    await flush();
    expect(api.post).toHaveBeenCalledWith('/sessions/1/craft-scene');
  });

  it('shows image provider warning message', async () => {
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve([]);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'error', message: 'GPU out of memory' });
      return Promise.resolve({});
    });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('GPU out of memory')).toBeInTheDocument();
  });

  it('shows generation date on images', async () => {
    const images = [
      { id: 1, prompt: 'A castle', model_used: 'flux', generated_at: '2025-03-01' },
    ];
    vi.mocked(api.get).mockImplementation((path: string) => {
      if (path.includes('/images')) return Promise.resolve(images);
      if (path.includes('/image-health')) return Promise.resolve({ status: 'ok' });
      return Promise.resolve({});
    });
    render(IllustrationsSection, { props: { sessionId: 1 } });
    await flush();
    expect(screen.getByText('Generated: 2025-03-01')).toBeInTheDocument();
  });
});
