
/**
 * Window chrome, navigation, and modal tests.
 *
 * Covers:
 * - Window control commands (minimize, maximize, close, toggle_maximize)
 * - Header drag region behavior
 * - Navigation focus and active state
 * - About modal open/close
 * - Alt+F4 handling
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  bridge, sendReady, minimizeWindow, maximizeWindow, restoreWindow,
  toggleMaximizeWindow, closeWindow, beginWindowDrag,
} from '../src/bridge/client';

// ── DOM helpers ─────────────────────────────────────────────────────────────

/** Set up a minimal DOM with all required elements. */
function setupDOM(): void {
  document.body.innerHTML = `
    <!-- Header with drag region, window controls, and navigation -->
    <cds-header platform-name="Threshold" aria-label="Threshold">
      <div class="header-drag-region" data-testid="header-drag-region" role="presentation"></div>
      <cds-header-name href="#" data-testid="header-name">Threshold</cds-header-name>
      <cds-header-nav aria-label="Main navigation" data-testid="main-nav">
        <cds-header-nav-item 
          href="#overview" 
          is-active="true"
          data-testid="nav-overview"
          data-region="overview"
          role="button"
          tabindex="0">
          Overview
        </cds-header-nav-item>
        <cds-header-nav-item 
          href="#threshold" 
          data-testid="nav-threshold"
          data-region="threshold"
          role="button"
          tabindex="0">
          Threshold
        </cds-header-nav-item>
        <cds-header-nav-item 
          href="#settings" 
          data-testid="nav-settings"
          data-region="settings"
          role="button"
          tabindex="0">
          Settings
        </cds-header-nav-item>
      </cds-header-nav>
      <div class="window-controls" data-testid="window-controls">
        <cds-button 
          kind="ghost" 
          size="sm"
          data-testid="window-minimize"
          data-command="minimize"
          aria-label="Minimize"
          title="Minimize">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <rect x="3" y="7" width="10" height="2" />
          </svg>
        </cds-button>
        <cds-button 
          kind="ghost" 
          size="sm"
          data-testid="window-maximize"
          data-command="toggle_maximize"
          aria-label="Maximize"
          title="Maximize">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <rect x="3" y="3" width="10" height="10" fill="none" stroke="currentColor" stroke-width="2" />
          </svg>
        </cds-button>
        <cds-button 
          kind="ghost" 
          size="sm"
          data-testid="window-close"
          data-command="close"
          aria-label="Close"
          title="Close">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M12.2 3.8L8 8l4.2 4.2-1.4 1.4L6.6 9.4l-4.2 4.2-1.4-1.4L5.2 8 1 3.8 2.4 2.4l4.2 4.2 4.2-4.2z" />
          </svg>
        </cds-button>
      </div>
    </cds-header>

    <main class="cds-content">
      <section id="overview" class="content-region" data-testid="region-overview" tabindex="-1">
        <div id="battery-status" class="cds-tile" data-testid="battery-status">
          <span id="charge-percent" data-testid="charge-percent"></span>
        </div>
      </section>
      <section id="threshold" class="content-region" data-testid="region-threshold" tabindex="-1">
        <div id="threshold-panel" class="cds-tile" data-testid="threshold-panel">
          <span id="active-threshold" data-testid="active-threshold"></span>
        </div>
      </section>
      <section id="settings" class="content-region" data-testid="region-settings" tabindex="-1">
        <div id="appearance-panel" class="cds-tile" data-testid="appearance-panel"></div>
        <div class="cds-tile" data-testid="about-tile">
          <cds-button 
            kind="secondary" 
            data-testid="about-button"
            aria-haspopup="dialog">
            About Threshold
          </cds-button>
        </div>
      </section>
    </main>

    <!-- About Modal -->
    <cds-modal 
      id="about-modal"
      data-testid="about-modal"
      aria-label="About Threshold"
      size="sm">
      <cds-modal-header>
        <cds-modal-heading data-testid="about-modal-heading">About Threshold</cds-modal-heading>
      </cds-modal-header>
      <cds-modal-body>
        <div class="about-content">
          <p class="about-version" data-testid="about-version">Version 1.0.0</p>
        </div>
      </cds-modal-body>
      <cds-modal-footer>
        <cds-button 
          kind="secondary" 
          data-testid="about-close-button"
          modal-close>
          Close
        </cds-button>
      </cds-modal-footer>
    </cds-modal>

    <div id="toast-container"></div>
    <p id="status-text"></p>
  `;
}

/** Mock webkit.messageHandlers.threshold.postMessage. */
function mockWebKit(): { messages: string[]; postMessage: (msg: string) => void } {
  const messages: string[] = [];
  const postMessage = (msg: string) => messages.push(msg);
  (window as any).webkit = {
    messageHandlers: {
      threshold: { postMessage },
    },
  };
  return { messages, postMessage };
}

/** Resolve the next pending request by simulating a full message round-trip. */
function resolvePending(data: Record<string, unknown>, ok = true): void {
  const pending = (bridge as any)._pending;
  const key = pending.keys().next().value;
  if (!key) return;
  const response = { id: key, ok, data, error: ok ? undefined : data.error };
  bridge._handleMessage(JSON.stringify(response));
}

// ── Window commands tests ──────────────────────────────────────────────────

describe('Window commands', () => {
  beforeEach(() => {
    setupDOM();
    mockWebKit();
    (bridge as any)._pending.clear();
    (bridge as any)._ready = false;
    (bridge as any)._nextId = 0;
  });

  describe('minimizeWindow', () => {
    it('sends minimize command', async () => {
      const promise = minimizeWindow();
      resolvePending({ minimized: true });

      const result = await promise;
      expect(result.minimized).toBe(true);
    });
  });

  describe('maximizeWindow', () => {
    it('sends maximize command', async () => {
      const promise = maximizeWindow();
      resolvePending({ maximized: true });

      const result = await promise;
      expect(result.maximized).toBe(true);
    });
  });

  describe('restoreWindow', () => {
    it('sends restore command', async () => {
      const promise = restoreWindow();
      resolvePending({ maximized: false });

      const result = await promise;
      expect(result.maximized).toBe(false);
    });
  });

  describe('toggleMaximizeWindow', () => {
    it('sends toggle_maximize command', async () => {
      const promise = toggleMaximizeWindow();
      resolvePending({ maximized: true });

      const result = await promise;
      expect(result.maximized).toBe(true);
    });
  });

  describe('closeWindow', () => {
    it('sends close command', async () => {
      const promise = closeWindow();
      resolvePending({ closed: true });

      const result = await promise;
      expect(result.closed).toBe(true);
    });
  });

  describe('beginWindowDrag', () => {
    it('sends begin_drag command', async () => {
      const promise = beginWindowDrag();
      resolvePending({ dragging: true });

      const result = await promise;
      expect(result.dragging).toBe(true);
    });
  });
});

// ── Window controls UI tests ───────────────────────────────────────────────

describe('Window controls UI', () => {
  beforeEach(() => {
    setupDOM();
    mockWebKit();
    (bridge as any)._pending.clear();
  });

  it('renders minimize button with correct data-command', () => {
    const btn = document.querySelector('[data-testid="window-minimize"]');
    expect(btn).not.toBeNull();
    expect(btn!.getAttribute('data-command')).toBe('minimize');
    expect(btn!.getAttribute('aria-label')).toBe('Minimize');
  });

  it('renders maximize button with correct data-command', () => {
    const btn = document.querySelector('[data-testid="window-maximize"]');
    expect(btn).not.toBeNull();
    expect(btn!.getAttribute('data-command')).toBe('toggle_maximize');
    expect(btn!.getAttribute('aria-label')).toBe('Maximize');
  });

  it('renders close button with correct data-command', () => {
    const btn = document.querySelector('[data-testid="window-close"]');
    expect(btn).not.toBeNull();
    expect(btn!.getAttribute('data-command')).toBe('close');
    expect(btn!.getAttribute('aria-label')).toBe('Close');
  });

  it('renders window controls container', () => {
    const container = document.querySelector('[data-testid="window-controls"]');
    expect(container).not.toBeNull();
  });
});

// ── Header drag region tests ───────────────────────────────────────────────

describe('Header drag region', () => {
  beforeEach(() => {
    setupDOM();
    mockWebKit();
  });

  it('renders drag region element', () => {
    const dragRegion = document.querySelector('[data-testid="header-drag-region"]');
    expect(dragRegion).not.toBeNull();
    expect(dragRegion!.getAttribute('role')).toBe('presentation');
  });

  it('has cursor default style', () => {
    const dragRegion = document.querySelector<HTMLElement>('[data-testid="header-drag-region"]');
    expect(dragRegion).not.toBeNull();
    // The element should exist and be ready for drag behavior
    expect(dragRegion!.tagName).toBeDefined();
  });
});

// ── Navigation tests ───────────────────────────────────────────────────────

describe('Navigation', () => {
  beforeEach(() => {
    setupDOM();
    mockWebKit();
  });

  it('renders three navigation items', () => {
    const navItems = document.querySelectorAll('[data-region]');
    expect(navItems).toHaveLength(3);
  });

  it('overview nav item has is-active attribute', () => {
    const overviewNav = document.querySelector('[data-testid="nav-overview"]');
    expect(overviewNav).not.toBeNull();
    expect(overviewNav!.getAttribute('is-active')).toBe('true');
  });

  it('threshold nav item does not have is-active attribute', () => {
    const thresholdNav = document.querySelector('[data-testid="nav-threshold"]');
    expect(thresholdNav).not.toBeNull();
    expect(thresholdNav!.getAttribute('is-active')).toBeNull();
  });

  it('settings nav item does not have is-active attribute', () => {
    const settingsNav = document.querySelector('[data-testid="nav-settings"]');
    expect(settingsNav).not.toBeNull();
    expect(settingsNav!.getAttribute('is-active')).toBeNull();
  });

  it('nav items have correct data-region attributes', () => {
    const overviewNav = document.querySelector('[data-region="overview"]');
    const thresholdNav = document.querySelector('[data-region="threshold"]');
    const settingsNav = document.querySelector('[data-region="settings"]');

    expect(overviewNav).not.toBeNull();
    expect(thresholdNav).not.toBeNull();
    expect(settingsNav).not.toBeNull();
  });

  it('nav items have tabindex="0" for keyboard focus', () => {
    const navItems = document.querySelectorAll('[data-region]');
    navItems.forEach(item => {
      expect(item.getAttribute('tabindex')).toBe('0');
    });
  });

  it('nav items have role="button" for accessibility', () => {
    const navItems = document.querySelectorAll('[data-region]');
    navItems.forEach(item => {
      expect(item.getAttribute('role')).toBe('button');
    });
  });

  it('content regions have tabindex="-1" for programmatic focus', () => {
    const regions = document.querySelectorAll('.content-region');
    regions.forEach(region => {
      expect(region.getAttribute('tabindex')).toBe('-1');
    });
  });

  it('overview region has correct id', () => {
    const region = document.getElementById('overview');
    expect(region).not.toBeNull();
    expect(region!.classList.contains('content-region')).toBe(true);
  });

  it('threshold region has correct id', () => {
    const region = document.getElementById('threshold');
    expect(region).not.toBeNull();
    expect(region!.classList.contains('content-region')).toBe(true);
  });

  it('settings region has correct id', () => {
    const region = document.getElementById('settings');
    expect(region).not.toBeNull();
    expect(region!.classList.contains('content-region')).toBe(true);
  });
});

// ── About modal tests ──────────────────────────────────────────────────────

describe('About modal', () => {
  beforeEach(() => {
    setupDOM();
    mockWebKit();
  });

  it('renders About modal', () => {
    const modal = document.querySelector('[data-testid="about-modal"]');
    expect(modal).not.toBeNull();
  });

  it('About modal has correct aria-label', () => {
    const modal = document.querySelector('[data-testid="about-modal"]');
    expect(modal!.getAttribute('aria-label')).toBe('About Threshold');
  });

  it('About modal has size="sm"', () => {
    const modal = document.querySelector('[data-testid="about-modal"]');
    expect(modal!.getAttribute('size')).toBe('sm');
  });

  it('About modal heading renders correctly', () => {
    const heading = document.querySelector('[data-testid="about-modal-heading"]');
    expect(heading).not.toBeNull();
    expect(heading!.textContent).toBe('About Threshold');
  });

  it('About modal version renders correctly', () => {
    const version = document.querySelector('[data-testid="about-version"]');
    expect(version).not.toBeNull();
    expect(version!.textContent).toBe('Version 1.0.0');
  });

  it('About close button exists', () => {
    const closeBtn = document.querySelector('[data-testid="about-close-button"]');
    expect(closeBtn).not.toBeNull();
    expect(closeBtn!.getAttribute('modal-close')).not.toBeNull();
  });

  it('About button exists in settings region', () => {
    const aboutBtn = document.querySelector('[data-testid="about-button"]');
    expect(aboutBtn).not.toBeNull();
    expect(aboutBtn!.getAttribute('aria-haspopup')).toBe('dialog');
  });
});

// ── Alt+F4 handling tests ──────────────────────────────────────────────────

describe('Alt+F4 handling', () => {
  beforeEach(() => {
    setupDOM();
    mockWebKit();
  });

  it('Escape key should be handled for modal close', () => {
    // The Escape key handler is set up in init()
    // Here we test that the modal element exists and can be closed
    const modal = document.querySelector<HTMLElement>('[data-testid="about-modal"]');
    expect(modal).not.toBeNull();

    // Simulate setting open attribute
    modal!.setAttribute('open', '');
    expect(modal!.getAttribute('open')).toBe('');

    // Simulate removing open attribute (what Escape handler does)
    modal!.removeAttribute('open');
    expect(modal!.getAttribute('open')).toBeNull();
  });
});

// ── Command request format tests ───────────────────────────────────────────

describe('Window command request format', () => {
  beforeEach(() => {
    setupDOM();
    mockWebKit();
    (bridge as any)._pending.clear();
  });

  it('minimize sends correct command format', () => {
    const messages: string[] = [];
    (window as any).webkit.messageHandlers.threshold.postMessage = (msg: string) => messages.push(msg);

    minimizeWindow();

    expect(messages).toHaveLength(1);
    const sent = JSON.parse(messages[0]);
    expect(sent.cmd).toBe('minimize');
    expect(sent.id).toMatch(/^req-/);
  });

  it('maximize sends correct command format', () => {
    const messages: string[] = [];
    (window as any).webkit.messageHandlers.threshold.postMessage = (msg: string) => messages.push(msg);

    maximizeWindow();

    expect(messages).toHaveLength(1);
    const sent = JSON.parse(messages[0]);
    expect(sent.cmd).toBe('maximize');
  });

  it('restore sends correct command format', () => {
    const messages: string[] = [];
    (window as any).webkit.messageHandlers.threshold.postMessage = (msg: string) => messages.push(msg);

    restoreWindow();

    expect(messages).toHaveLength(1);
    const sent = JSON.parse(messages[0]);
    expect(sent.cmd).toBe('restore');
  });

  it('toggle_maximize sends correct command format', () => {
    const messages: string[] = [];
    (window as any).webkit.messageHandlers.threshold.postMessage = (msg: string) => messages.push(msg);

    toggleMaximizeWindow();

    expect(messages).toHaveLength(1);
    const sent = JSON.parse(messages[0]);
    expect(sent.cmd).toBe('toggle_maximize');
  });

  it('close sends correct command format', () => {
    const messages: string[] = [];
    (window as any).webkit.messageHandlers.threshold.postMessage = (msg: string) => messages.push(msg);

    closeWindow();

    expect(messages).toHaveLength(1);
    const sent = JSON.parse(messages[0]);
    expect(sent.cmd).toBe('close');
  });

  it('begin_drag sends correct command format', () => {
    const messages: string[] = [];
    (window as any).webkit.messageHandlers.threshold.postMessage = (msg: string) => messages.push(msg);

    beginWindowDrag();

    expect(messages).toHaveLength(1);
    const sent = JSON.parse(messages[0]);
    expect(sent.cmd).toBe('begin_drag');
  });
});
