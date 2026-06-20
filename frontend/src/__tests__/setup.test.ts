import { describe, it, expect } from 'vitest';

describe('Project Setup', () => {
  it('vitest is configured correctly', () => {
    expect(true).toBe(true);
  });

  it('jsdom environment is available', () => {
    expect(document).toBeDefined();
    expect(window).toBeDefined();
  });
});
