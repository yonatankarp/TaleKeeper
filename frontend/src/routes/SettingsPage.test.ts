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
  whisper_model: 'distil-large-v3',
  llm_base_url: 'http://localhost:11434/v1',
  llm_api_key: '',
  llm_model: 'llama3.1:8b',
  image_model: '',
  image_steps: '4',
  image_guidance_scale: '0',
  hf_token: '',
  whisper_batch_size: '',
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

  it('shows Transcription section with whisper model and batch size', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Transcription')).toBeInTheDocument();
    expect(screen.getByText('Whisper Model')).toBeInTheDocument();
    expect(screen.getByText('Batch Size')).toBeInTheDocument();
  });

  it('shows Providers section with HuggingFace and LLM Provider', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Providers')).toBeInTheDocument();
    expect(screen.getByText('HuggingFace')).toBeInTheDocument();
    expect(screen.getByText('LLM Provider')).toBeInTheDocument();
  });

  it('shows HuggingFace token field with link to pyannote license', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Access Token')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('hf_...')).toBeInTheDocument();
    expect(screen.getByText('pyannote model license')).toBeInTheDocument();
  });

  it('shows Image Generation section with steps and guidance scale', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Image Generation')).toBeInTheDocument();
    expect(screen.getByText('Steps')).toBeInTheDocument();
    expect(screen.getByText('Guidance Scale')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('FLUX.2-Klein-4B-Distilled')).toBeInTheDocument();
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

  it('shows Test Connection for LLM and Check Availability for image', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Test Connection')).toBeInTheDocument();
    expect(screen.getByText('Check Availability')).toBeInTheDocument();
  });

  it('shows whisper model select with distil-large-v3 option', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    const { container } = render(SettingsPage);
    await flush();
    const select = container.querySelector('select') as HTMLSelectElement;
    expect(select).toBeInTheDocument();
    expect(select.value).toBe('distil-large-v3');
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
    expect(screen.getByPlaceholderText('http://localhost:11434/v1')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('llama3.1:8b')).toBeInTheDocument();
  });

  it('shows LLM model recommendations', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText(/Recommended models/)).toBeInTheDocument();
  });

  it('shows SMTP fields', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByPlaceholderText('smtp.gmail.com')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('587')).toBeInTheDocument();
    const emailInputs = screen.getAllByPlaceholderText('you@example.com');
    expect(emailInputs).toHaveLength(2);
  });

  it('shows Data section with browse button', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText('Browse')).toBeInTheDocument();
  });

  it('shows batch size hint about auto-detection', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText(/automatic detection based on your Apple Silicon/)).toBeInTheDocument();
  });

  it('shows hint about data directory', async () => {
    vi.mocked(api.get).mockResolvedValue(mockSettings);
    render(SettingsPage);
    await flush();
    expect(screen.getByText(/Where session recordings/)).toBeInTheDocument();
  });
});
