import { describe, it, expect, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import SettingsPage from './SettingsPage.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn(),
    post: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    del: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('../lib/wizard.svelte', () => ({
  wizard: {
    get open() { return false; },
    show: vi.fn(),
    hide: vi.fn(),
  },
}));

import { api } from '../lib/api';

const mockSettings: Record<string, string> = {
  whisper_model: 'medium',
  llm_base_url: 'http://localhost:11434/v1',
  llm_api_key: '',
  llm_model: 'llama3.1:8b',
  image_base_url: '',
  image_api_key: '',
  image_model: '',
  live_transcription: 'false',
  data_dir: '',
};

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('SettingsPage', () => {
  afterEach(() => {
    cleanup();
    vi.mocked(api.get).mockReset();
  });

  it('shows loading state initially', () => {
    vi.mocked(api.get).mockReturnValue(new Promise(() => {}));
    render(SettingsPage);
    expect(screen.getByText(/Loading settings/)).toBeInTheDocument();
  });

  it('shows Settings heading after loading', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });

  it('shows Transcription section', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Transcription')).toBeInTheDocument();
    expect(screen.getByText('Whisper Model')).toBeInTheDocument();
  });

  it('shows LLM Provider section', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('LLM Provider')).toBeInTheDocument();
  });

  it('shows Image Generation section', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Image Generation')).toBeInTheDocument();
  });

  it('shows Email (SMTP) section', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Email (SMTP)')).toBeInTheDocument();
  });

  it('shows Data section', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Data')).toBeInTheDocument();
  });

  it('shows Save Settings button', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Save Settings')).toBeInTheDocument();
  });

  it('shows Run Setup Wizard button', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Run Setup Wizard')).toBeInTheDocument();
  });

  it('shows Test Connection buttons for LLM and Image', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    const testButtons = screen.getAllByText('Test Connection');
    expect(testButtons.length).toBe(2);
  });

  it('shows whisper model select with options', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    const { container } = render(SettingsPage);
    await flush();
    const select = container.querySelector('select') as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.value).toBe('medium');
  });

  it('shows live transcription checkbox', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Live transcription during recording')).toBeInTheDocument();
  });

  it('calls api.put when Save Settings is clicked', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    vi.mocked(api.put).mockResolvedValue({});
    render(SettingsPage);
    await flush();
    await fireEvent.click(screen.getByText('Save Settings'));
    await flush();
    expect(api.put).toHaveBeenCalledWith('/settings', { settings: expect.any(Object) });
  });

  it('shows LLM provider fields', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    // "http://localhost:11434/v1" appears for both LLM and Image base URLs
    const baseUrlInputs = screen.getAllByPlaceholderText('http://localhost:11434/v1');
    expect(baseUrlInputs).toHaveLength(2);
    expect(screen.getByPlaceholderText('llama3.1:8b')).toBeInTheDocument();
  });

  it('shows Image Generation fields', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Image Generation')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('x/flux2-klein:9b')).toBeInTheDocument();
  });

  it('shows SMTP fields', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByPlaceholderText('smtp.gmail.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('587')).toBeInTheDocument();
    // "you@example.com" appears for both Username and Sender Address
    const emailInputs = screen.getAllByPlaceholderText('you@example.com');
    expect(emailInputs).toHaveLength(2);
  });

  it('shows Data section with browse button', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Browse')).toBeInTheDocument();
  });

  it('shows hint about live transcription', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText(/When enabled, preview segments appear/)).toBeInTheDocument();
  });

  it('shows hint about data directory', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText(/Where session recordings/)).toBeInTheDocument();
  });
});
