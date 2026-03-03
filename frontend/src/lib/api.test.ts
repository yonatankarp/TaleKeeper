import { describe, it, expect, vi, beforeEach } from 'vitest';
import { api, mergeSpeakers, uploadAudio, generateImageStream, reDiarize, processAudio } from './api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const mockFetch = vi.fn();
globalThis.fetch = mockFetch;

function createSSEStream(events: string): ReadableStream<Uint8Array> {
  return new ReadableStream({
    start(controller) {
      controller.enqueue(new TextEncoder().encode(events));
      controller.close();
    },
  });
}

/** Helper: wait for micro-tasks so the SSE async IIFE inside stream helpers runs to completion. */
function flushAsync(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, 20));
}

beforeEach(() => {
  mockFetch.mockReset();
});

// ---------------------------------------------------------------------------
// 11.1 - api.get / api.post / api.put / api.del
// ---------------------------------------------------------------------------

describe('api', () => {
  it('api.get sends GET request', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve([{ id: 1 }]),
    });

    const result = await api.get('/campaigns');

    expect(mockFetch).toHaveBeenCalledWith('/api/campaigns', {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
    });
    expect(result).toEqual([{ id: 1 }]);
  });

  it('api.post sends POST request with body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: 2, name: 'New Campaign' }),
    });

    const result = await api.post('/campaigns', { name: 'New Campaign' });

    expect(mockFetch).toHaveBeenCalledWith('/api/campaigns', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'New Campaign' }),
    });
    expect(result).toEqual({ id: 2, name: 'New Campaign' });
  });

  it('api.put sends PUT request with body', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ id: 1, name: 'Updated' }),
    });

    const result = await api.put('/campaigns/1', { name: 'Updated' });

    expect(mockFetch).toHaveBeenCalledWith('/api/campaigns/1', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name: 'Updated' }),
    });
    expect(result).toEqual({ id: 1, name: 'Updated' });
  });

  it('api.del sends DELETE request', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ success: true }),
    });

    const result = await api.del('/campaigns/1');

    expect(mockFetch).toHaveBeenCalledWith('/api/campaigns/1', {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
    });
    expect(result).toEqual({ success: true });
  });
});

// ---------------------------------------------------------------------------
// 11.2 - API error handling
// ---------------------------------------------------------------------------

describe('api error handling', () => {
  it('throws with error detail string from response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Not Found',
      json: () => Promise.resolve({ detail: 'Campaign not found' }),
    });

    await expect(api.get('/campaigns/999')).rejects.toThrow('Campaign not found');
  });

  it('throws with JSON-stringified detail when detail is not a string', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: { field: 'name', error: 'required' } }),
    });

    await expect(api.post('/campaigns', {})).rejects.toThrow(
      JSON.stringify({ field: 'name', error: 'required' }),
    );
  });

  it('falls back to statusText when json parse fails', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Internal Server Error',
      json: () => Promise.reject(new Error('not json')),
    });

    await expect(api.get('/broken')).rejects.toThrow('Internal Server Error');
  });
});

// ---------------------------------------------------------------------------
// 11.3 - mergeSpeakers
// ---------------------------------------------------------------------------

describe('mergeSpeakers', () => {
  it('sends POST to correct URL with speaker IDs', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ merged: true }),
    });

    const result = await mergeSpeakers(42, 1, 2);

    expect(mockFetch).toHaveBeenCalledWith('/api/sessions/42/merge-speakers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ source_speaker_id: 1, target_speaker_id: 2 }),
    });
    expect(result).toEqual({ merged: true });
  });
});

// ---------------------------------------------------------------------------
// 11.4 - uploadAudio
// ---------------------------------------------------------------------------

describe('uploadAudio', () => {
  it('sends POST with FormData containing the file', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: () => Promise.resolve({ audio_path: '/uploads/audio.wav' }),
    });

    const file = new File(['audio-data'], 'recording.wav', { type: 'audio/wav' });
    const result = await uploadAudio(10, file);

    expect(mockFetch).toHaveBeenCalledTimes(1);

    const [url, opts] = mockFetch.mock.calls[0];
    expect(url).toBe('/api/sessions/10/upload-audio');
    expect(opts.method).toBe('POST');
    expect(opts.body).toBeInstanceOf(FormData);
    expect((opts.body as FormData).get('file')).toBe(file);
    expect(result).toEqual({ audio_path: '/uploads/audio.wav' });
  });

  it('throws on error response', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: 'No audio file provided' }),
    });

    const file = new File([''], 'empty.wav', { type: 'audio/wav' });
    await expect(uploadAudio(10, file)).rejects.toThrow('No audio file provided');
  });
});

// ---------------------------------------------------------------------------
// 12.1 - generateImageStream
// ---------------------------------------------------------------------------

describe('generateImageStream', () => {
  it('calls onPhase and onDone from SSE events', async () => {
    const ssePayload = [
      'event: phase',
      'data: {"phase":"Generating scene description"}',
      '',
      'event: phase',
      'data: {"phase":"Rendering image"}',
      '',
      'event: done',
      'data: {"image":{"id":1,"session_id":5,"file_path":"/img/1.png","prompt":"a castle","scene_description":null,"model_used":"sdxl","generated_at":"2025-01-01"}}',
      '',
    ].join('\n');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream(ssePayload),
    });

    const onPhase = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    generateImageStream(5, 'a castle', onPhase, onDone, onError);
    await flushAsync();

    expect(onPhase).toHaveBeenCalledTimes(2);
    expect(onPhase).toHaveBeenCalledWith('Generating scene description');
    expect(onPhase).toHaveBeenCalledWith('Rendering image');
    expect(onDone).toHaveBeenCalledTimes(1);
    expect(onDone).toHaveBeenCalledWith({
      id: 1,
      session_id: 5,
      file_path: '/img/1.png',
      prompt: 'a castle',
      scene_description: null,
      model_used: 'sdxl',
      generated_at: '2025-01-01',
    });
    expect(onError).not.toHaveBeenCalled();
  });

  it('calls onError on SSE error event', async () => {
    const ssePayload = [
      'event: error',
      'data: {"message":"Model unavailable"}',
      '',
    ].join('\n');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream(ssePayload),
    });

    const onPhase = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    generateImageStream(5, null, onPhase, onDone, onError);
    await flushAsync();

    expect(onError).toHaveBeenCalledWith('Model unavailable');
    expect(onDone).not.toHaveBeenCalled();
  });

  it('calls onError when fetch response is not ok', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Service Unavailable',
      json: () => Promise.resolve({ detail: 'GPU overloaded' }),
    });

    const onPhase = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    generateImageStream(5, 'a castle', onPhase, onDone, onError);
    await flushAsync();

    expect(onError).toHaveBeenCalledWith('GPU overloaded');
  });
});

// ---------------------------------------------------------------------------
// 12.2 - reDiarize
// ---------------------------------------------------------------------------

describe('reDiarize', () => {
  it('calls onPhase and onDone from SSE events', async () => {
    const ssePayload = [
      'event: phase',
      'data: {"phase":"Re-diarizing audio"}',
      '',
      'event: done',
      'data: {"segments_count":15}',
      '',
    ].join('\n');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream(ssePayload),
    });

    const onPhase = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    reDiarize(7, 3, onPhase, onDone, onError);
    await flushAsync();

    expect(mockFetch).toHaveBeenCalledWith('/api/sessions/7/re-diarize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ num_speakers: 3 }),
    });
    expect(onPhase).toHaveBeenCalledWith('Re-diarizing audio');
    expect(onDone).toHaveBeenCalledWith(15);
    expect(onError).not.toHaveBeenCalled();
  });

  it('calls onError on SSE error event', async () => {
    const ssePayload = [
      'event: error',
      'data: {"message":"Diarization model crashed"}',
      '',
    ].join('\n');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream(ssePayload),
    });

    const onPhase = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    reDiarize(7, 3, onPhase, onDone, onError);
    await flushAsync();

    expect(onError).toHaveBeenCalledWith('Diarization model crashed');
    expect(onDone).not.toHaveBeenCalled();
  });

  it('calls onError when fetch response is not ok', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Bad Request',
      json: () => Promise.resolve({ detail: 'Invalid speaker count' }),
    });

    const onPhase = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    reDiarize(7, -1, onPhase, onDone, onError);
    await flushAsync();

    expect(onError).toHaveBeenCalledWith('Invalid speaker count');
  });
});

// ---------------------------------------------------------------------------
// 12.3 - processAudio
// ---------------------------------------------------------------------------

describe('processAudio', () => {
  it('calls onProgress with chunk/total from SSE events', async () => {
    const ssePayload = [
      'event: progress',
      'data: {"chunk":1,"total_chunks":4}',
      '',
      'event: progress',
      'data: {"chunk":2,"total_chunks":4}',
      '',
      'event: segment',
      'data: {"text":"Hello world","start_time":0.0,"end_time":1.5}',
      '',
      'event: done',
      'data: {"segments_count":1}',
      '',
    ].join('\n');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream(ssePayload),
    });

    const onProgress = vi.fn();
    const onSegment = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    processAudio(3, onProgress, onSegment, onDone, onError);
    await flushAsync();

    expect(mockFetch).toHaveBeenCalledWith('/api/sessions/3/process-audio', {
      method: 'POST',
    });

    expect(onProgress).toHaveBeenCalledTimes(2);
    expect(onProgress).toHaveBeenCalledWith(1, 4);
    expect(onProgress).toHaveBeenCalledWith(2, 4);

    expect(onSegment).toHaveBeenCalledTimes(1);
    expect(onSegment).toHaveBeenCalledWith({
      text: 'Hello world',
      start_time: 0.0,
      end_time: 1.5,
    });

    expect(onDone).toHaveBeenCalledWith(1);
    expect(onError).not.toHaveBeenCalled();
  });

  it('passes numSpeakers as query parameter when provided', async () => {
    const ssePayload = [
      'event: done',
      'data: {"segments_count":0}',
      '',
    ].join('\n');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream(ssePayload),
    });

    const onProgress = vi.fn();
    const onSegment = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    processAudio(3, onProgress, onSegment, onDone, onError, 4);
    await flushAsync();

    expect(mockFetch).toHaveBeenCalledWith('/api/sessions/3/process-audio?num_speakers=4', {
      method: 'POST',
    });
  });

  it('calls onPhase when onPhase callback is provided', async () => {
    const ssePayload = [
      'event: phase',
      'data: {"phase":"Transcribing"}',
      '',
      'event: done',
      'data: {"segments_count":5}',
      '',
    ].join('\n');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream(ssePayload),
    });

    const onProgress = vi.fn();
    const onSegment = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();
    const onPhase = vi.fn();

    processAudio(3, onProgress, onSegment, onDone, onError, undefined, onPhase);
    await flushAsync();

    expect(onPhase).toHaveBeenCalledWith('Transcribing');
    expect(onDone).toHaveBeenCalledWith(5);
  });

  it('calls onError on SSE error event', async () => {
    const ssePayload = [
      'event: error',
      'data: {"message":"Audio file corrupt"}',
      '',
    ].join('\n');

    mockFetch.mockResolvedValueOnce({
      ok: true,
      body: createSSEStream(ssePayload),
    });

    const onProgress = vi.fn();
    const onSegment = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    processAudio(3, onProgress, onSegment, onDone, onError);
    await flushAsync();

    expect(onError).toHaveBeenCalledWith('Audio file corrupt');
  });

  it('calls onError when fetch response is not ok', async () => {
    mockFetch.mockResolvedValueOnce({
      ok: false,
      statusText: 'Not Found',
      json: () => Promise.resolve({ detail: 'Session not found' }),
    });

    const onProgress = vi.fn();
    const onSegment = vi.fn();
    const onDone = vi.fn();
    const onError = vi.fn();

    processAudio(99, onProgress, onSegment, onDone, onError);
    await flushAsync();

    expect(onError).toHaveBeenCalledWith('Session not found');
  });
});
