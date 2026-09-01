// @ts-expect-error Test runner provides Node built-ins; app tsconfig stays browser-only.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const html = readFileSync('index.html', 'utf8');
const css = readFileSync('src/styles.css', 'utf8');

describe('viewport layout regressions', () => {
  it('shows Bongbetic symbol before first Threshold title', () => {
    const logoIndex = html.indexOf('class="header-logo"');
    const titleIndex = html.indexOf('class="header-name"');
    expect(logoIndex).toBeGreaterThan(-1);
    expect(logoIndex).toBeLessThan(titleIndex);
    expect(html).toContain('src="./bongbetic-icon-dark.png"');
  });

  it('uses native frame controls only', () => {
    expect(html).not.toContain('data-testid="window-controls"');
    expect(html).not.toContain('data-command="minimize"');
    expect(html).not.toContain('data-command="toggle_maximize"');
    expect(html).not.toContain('data-command="close"');
  });

  it('uses third-row control-state card instead of About card', () => {
    expect(html).not.toContain('data-testid="about-tile"');
    expect(html).toContain('data-testid="control-state-card"');
  });

  it('reserves enough height for battery telemetry', () => {
    expect(css).toMatch(/grid-template-rows:\s*160px/);
    expect(css).toMatch(/#battery-status \.card-body\s*\{[^}]*overflow:\s*visible/s);
  });

  it('reserves enough height for all third-row cards', () => {
    expect(css).toMatch(/grid-template-rows:\s*160px\s+minmax\(220px, 1fr\)\s+180px\s+32px/);
    expect(css).toMatch(/#appearance-panel \.card-body,[^}]*#device-info-tile \.card-body,[^}]*#control-state-card \.card-body\s*\{[^}]*overflow:\s*visible/s);
  });

  it('reserves unclipped space for quick-select controls', () => {
    expect(css).toMatch(/grid-template-rows:\s*160px\s+minmax\(220px, 1fr\)\s+180px\s+32px/);
    expect(css).toMatch(/#threshold-panel\s*\{[^}]*overflow:\s*visible/s);
    expect(css).toMatch(/#threshold-panel \.card-body\s*\{[^}]*overflow:\s*visible/s);
  });
});
