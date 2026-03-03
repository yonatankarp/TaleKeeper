import { describe, it, expect } from 'vitest';
import { WHISPER_LANGUAGES } from './languages';

describe('WHISPER_LANGUAGES', () => {
  it('is a non-empty array', () => {
    expect(WHISPER_LANGUAGES.length).toBeGreaterThan(0);
  });

  it('contains English', () => {
    const english = WHISPER_LANGUAGES.find((l) => l.code === 'en');
    expect(english).toBeDefined();
    expect(english!.name).toBe('English');
  });

  it('each entry has code and name strings', () => {
    for (const lang of WHISPER_LANGUAGES) {
      expect(typeof lang.code).toBe('string');
      expect(typeof lang.name).toBe('string');
      expect(lang.code.length).toBeGreaterThan(0);
      expect(lang.name.length).toBeGreaterThan(0);
    }
  });

  it('has unique codes', () => {
    const codes = WHISPER_LANGUAGES.map((l) => l.code);
    const uniqueCodes = new Set(codes);
    expect(uniqueCodes.size).toBe(codes.length);
  });

  it('contains common languages', () => {
    const codes = WHISPER_LANGUAGES.map((l) => l.code);
    expect(codes).toContain('en');
    expect(codes).toContain('es');
    expect(codes).toContain('fr');
    expect(codes).toContain('de');
    expect(codes).toContain('ja');
    expect(codes).toContain('zh');
  });
});
