import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/svelte';
import AudioPlayer from './AudioPlayer.svelte';

describe('AudioPlayer', () => {
  it('renders an audio element', () => {
    const { container } = render(AudioPlayer, { props: { sessionId: 42 } });
    const audio = container.querySelector('audio');
    expect(audio).toBeInTheDocument();
  });

  it('sets the audio src based on sessionId', () => {
    const { container } = render(AudioPlayer, { props: { sessionId: 42 } });
    const audio = container.querySelector('audio') as HTMLAudioElement;
    expect(audio.getAttribute('src')).toBe('/api/sessions/42/audio');
  });

  it('has controls enabled', () => {
    const { container } = render(AudioPlayer, { props: { sessionId: 1 } });
    const audio = container.querySelector('audio') as HTMLAudioElement;
    expect(audio.hasAttribute('controls')).toBe(true);
  });

  it('has preload set to metadata', () => {
    const { container } = render(AudioPlayer, { props: { sessionId: 1 } });
    const audio = container.querySelector('audio') as HTMLAudioElement;
    expect(audio.getAttribute('preload')).toBe('metadata');
  });

  it('renders within an audio-player container', () => {
    const { container } = render(AudioPlayer, { props: { sessionId: 5 } });
    const wrapper = container.querySelector('.audio-player');
    expect(wrapper).toBeInTheDocument();
    expect(wrapper?.querySelector('audio')).toBeInTheDocument();
  });

  it('updates audio src when sessionId changes', async () => {
    const { container, rerender } = render(AudioPlayer, { props: { sessionId: 1 } });
    let audio = container.querySelector('audio') as HTMLAudioElement;
    expect(audio.getAttribute('src')).toBe('/api/sessions/1/audio');

    await rerender({ sessionId: 99 });
    audio = container.querySelector('audio') as HTMLAudioElement;
    expect(audio.getAttribute('src')).toBe('/api/sessions/99/audio');
  });
});
