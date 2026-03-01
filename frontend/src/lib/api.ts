/**  Thin wrapper around fetch for the TaleKeeper API. */

const BASE = '/api';

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const opts: RequestInit = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(`${BASE}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    const message = typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : res.statusText;
    throw new Error(message);
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>('GET', path),
  post: <T>(path: string, body?: unknown) => request<T>('POST', path, body),
  put: <T>(path: string, body?: unknown) => request<T>('PUT', path, body),
  del: <T>(path: string) => request<T>('DELETE', path),
};

export async function uploadAudio(sessionId: number, file: File): Promise<{ audio_path: string }> {
  const form = new FormData();
  form.append('file', file);
  const res = await fetch(`${BASE}/sessions/${sessionId}/upload-audio`, {
    method: 'POST',
    body: form,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = err.detail;
    throw new Error(typeof detail === 'string' ? detail : detail ? JSON.stringify(detail) : res.statusText);
  }
  return res.json();
}

export function processAudio(
  sessionId: number,
  onProgress: (chunk: number, total: number) => void,
  onSegment: (seg: { text: string; start_time: number; end_time: number }) => void,
  onDone: (segmentsCount: number) => void,
  onError: (message: string) => void,
  numSpeakers?: number,
): { cancel: () => void } {
  let cancelled = false;
  let reader: ReadableStreamDefaultReader<Uint8Array> | null = null;

  (async () => {
    try {
      const params = numSpeakers != null ? `?num_speakers=${numSpeakers}` : '';
      const res = await fetch(`${BASE}/sessions/${sessionId}/process-audio${params}`, {
        method: 'POST',
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        onError(typeof err.detail === 'string' ? err.detail : res.statusText);
        return;
      }

      reader = res.body?.getReader() ?? null;
      if (!reader) { onError('No response body'); return; }

      const decoder = new TextDecoder();
      let buffer = '';
      let currentEvent = '';
      let gotDoneOrError = false;

      function processLines(lines: string[]) {
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith('data: ') && currentEvent) {
            const data = JSON.parse(line.slice(6));
            if (currentEvent === 'progress') onProgress(data.chunk, data.total_chunks);
            else if (currentEvent === 'segment') onSegment(data);
            else if (currentEvent === 'done') { gotDoneOrError = true; onDone(data.segments_count); }
            else if (currentEvent === 'error') { gotDoneOrError = true; onError(data.message || 'Processing failed'); }
            currentEvent = '';
          } else if (line.trim() === '') {
            currentEvent = '';
          }
        }
      }

      while (!cancelled) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() ?? '';
        processLines(lines);
      }

      // Flush any remaining buffered content
      if (buffer.trim()) {
        processLines(buffer.split('\n'));
      }

      // If stream ended without a done/error event, signal completion
      if (!cancelled && !gotDoneOrError) {
        onDone(0);
      }
    } catch (e) {
      if (!cancelled) onError(e instanceof Error ? e.message : 'Processing failed');
    }
  })();

  return {
    cancel() {
      cancelled = true;
      reader?.cancel();
    },
  };
}
