import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import { render, screen, fireEvent, cleanup } from '@testing-library/svelte';
import { tick } from 'svelte';
import RecordingControls from './RecordingControls.svelte';

vi.mock('../lib/api', () => ({
  api: {
    get: vi.fn().mockResolvedValue({ num_speakers: 5 }),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
  uploadAudio: vi.fn().mockResolvedValue({ audio_path: '/audio.wav' }),
  processAudio: vi.fn().mockReturnValue({ cancel: vi.fn() }),
}));

import { api } from '../lib/api';

async function flush() {
  await tick();
  await new Promise((r) => setTimeout(r, 0));
}

describe('RecordingControls', () => {
  afterEach(() => {
    cleanup();
    sessionStorage.clear();
  });

  beforeEach(() => {
    vi.mocked(api.get).mockResolvedValue({ num_speakers: 5 });
  });

  function makeProps(overrides = {}) {
    return {
      sessionId: 1,
      status: 'draft',
      onStatusChange: vi.fn(),
      ...overrides,
    };
  }

  it('shows "Start Recording" button when status is draft', () => {
    render(RecordingControls, { props: makeProps({ status: 'draft' }) });
    expect(screen.getByText('Start Recording')).toBeInTheDocument();
  });

  it('shows "Upload Audio" button when status is draft', () => {
    render(RecordingControls, { props: makeProps({ status: 'draft' }) });
    expect(screen.getByText('Upload Audio')).toBeInTheDocument();
  });

  it('disables "Start Recording" when status is completed', () => {
    render(RecordingControls, { props: makeProps({ status: 'completed' }) });
    const btn = screen.getByText('Start Recording');
    expect(btn).toBeDisabled();
  });

  it('shows speakers input label', () => {
    render(RecordingControls, { props: makeProps() });
    expect(screen.getByText('Speakers')).toBeInTheDocument();
  });

  it('does not show recording indicator when idle', () => {
    const { container } = render(RecordingControls, { props: makeProps() });
    const indicator = container.querySelector('.recording-indicator');
    expect(indicator).not.toBeInTheDocument();
  });

  it('has a hidden file input for audio upload', () => {
    const { container } = render(RecordingControls, { props: makeProps() });
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    expect(fileInput).toBeInTheDocument();
    expect(fileInput.accept).toBe('audio/*');
  });

  it('fetches campaign num_speakers when campaignId is provided', async () => {
    render(RecordingControls, { props: makeProps({ campaignId: 42 }) });
    await flush();
    expect(api.get).toHaveBeenCalledWith('/campaigns/42');
  });

  it('shows both buttons when status is draft and not locked', () => {
    render(RecordingControls, { props: makeProps({ status: 'draft' }) });
    expect(screen.getByText('Start Recording')).not.toBeDisabled();
    expect(screen.getByText('Upload Audio')).not.toBeDisabled();
  });

  it('disables upload when status is transcribing', () => {
    render(RecordingControls, { props: makeProps({ status: 'transcribing' }) });
    const uploadBtn = screen.getByText('Upload Audio');
    expect(uploadBtn).toBeDisabled();
  });

  it('shows lock message when another session is recording', () => {
    sessionStorage.setItem('talekeeper_recording_session', '999');
    render(RecordingControls, { props: makeProps({ sessionId: 1 }) });
    expect(screen.getByText('Another session is recording')).toBeInTheDocument();
  });

  it('shows error when start recording fails with NotAllowedError', async () => {
    const mockError = new DOMException('Permission denied', 'NotAllowedError');
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: vi.fn().mockRejectedValue(mockError) },
      writable: true,
      configurable: true,
    });
    render(RecordingControls, { props: makeProps({ status: 'draft' }) });
    await fireEvent.click(screen.getByText('Start Recording'));
    await flush();
    expect(screen.getByText(/Microphone permission denied/)).toBeInTheDocument();
  });

  it('shows error when start recording fails with NotFoundError', async () => {
    const mockError = new DOMException('No device', 'NotFoundError');
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: vi.fn().mockRejectedValue(mockError) },
      writable: true,
      configurable: true,
    });
    render(RecordingControls, { props: makeProps({ status: 'draft' }) });
    await fireEvent.click(screen.getByText('Start Recording'));
    await flush();
    expect(screen.getByText(/No microphone found/)).toBeInTheDocument();
  });

  it('shows speakers number input with default value', () => {
    const { container } = render(RecordingControls, { props: makeProps() });
    const speakersInput = container.querySelector('.speakers-input') as HTMLInputElement;
    expect(speakersInput).toBeInTheDocument();
    expect(speakersInput.type).toBe('number');
  });

  it('shows generic error when start recording fails with unknown error', async () => {
    const mockError = new Error('Something went wrong');
    Object.defineProperty(navigator, 'mediaDevices', {
      value: { getUserMedia: vi.fn().mockRejectedValue(mockError) },
      writable: true,
      configurable: true,
    });
    render(RecordingControls, { props: makeProps({ status: 'draft' }) });
    await fireEvent.click(screen.getByText('Start Recording'));
    await flush();
    expect(screen.getByText(/Failed to start recording/)).toBeInTheDocument();
  });

  it('disables buttons when uploading', async () => {
    const { uploadAudio } = await import('../lib/api');
    vi.mocked(uploadAudio).mockReturnValue(new Promise(() => {})); // never resolves
    const { container } = render(RecordingControls, { props: makeProps({ status: 'draft' }) });
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['audio'], 'test.wav', { type: 'audio/wav' });
    Object.defineProperty(fileInput, 'files', { value: [file] });
    await fireEvent.change(fileInput);
    await flush();
    expect(screen.getByText('Uploading...')).toBeInTheDocument();
  });

  it('does not record when another session has the lock', async () => {
    sessionStorage.setItem('talekeeper_recording_session', '999');
    render(RecordingControls, { props: makeProps({ sessionId: 1, status: 'draft' }) });
    const btn = screen.getByText('Start Recording');
    expect(btn).toBeDisabled();
  });

  it('shows processing banner when processing is active', async () => {
    const { uploadAudio, processAudio } = await import('../lib/api');
    vi.mocked(uploadAudio).mockResolvedValue({ audio_path: '/audio.wav' });
    vi.mocked(processAudio).mockReturnValue({ cancel: vi.fn() });
    const { container } = render(RecordingControls, { props: makeProps({ status: 'draft' }) });
    const fileInput = container.querySelector('input[type="file"]') as HTMLInputElement;
    const file = new File(['audio'], 'test.wav', { type: 'audio/wav' });
    Object.defineProperty(fileInput, 'files', { value: [file] });
    await fireEvent.change(fileInput);
    await flush();
    expect(screen.getByText('Processing audio...')).toBeInTheDocument();
  });
});
