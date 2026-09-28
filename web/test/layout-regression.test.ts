// @ts-expect-error Test runner provides Node built-ins; app tsconfig stays browser-only.
import { readFileSync } from 'node:fs';
import { describe, expect, it } from 'vitest';

const html = readFileSync('index.html', 'utf8');

describe('viewport layout regressions', () => {
  it('shows Bongbetic symbol before first Threshold title', () => {
    const logoIndex = html.indexOf('class="header-logo"');
    const titleIndex = html.indexOf('class="header-name"');
    expect(logoIndex).toBeGreaterThan(-1);
    expect(logoIndex).toBeLessThan(titleIndex);
    expect(html).toContain('src="./bongbetic-icon-dark.png"');
  });

  it('keeps header free of section tabs', () => {
    expect(html).not.toContain('class="header-nav"');
    expect(html).not.toContain('data-region="overview"');
    expect(html).not.toContain('data-region="threshold"');
    expect(html).not.toContain('data-region="settings"');
  });

  it('removes compact mode from Appearance card', () => {
    expect(html).not.toContain('data-testid="compact-mode-toggle"');
    expect(html).not.toContain('Compact mode');
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
});
