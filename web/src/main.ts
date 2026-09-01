/**
 * Threshold Carbon shell - entry point.
 *
 * Sends ready handshake, requests state, renders battery overview.
 * Handles charge limit UI interactions.
 *
 * Overview cards:
 *   - Battery Status: charge percent, charge status, power source
 *   - Device Information: battery identifier, control mode, health, cycles, capacity
 *   - Charge Threshold: active threshold, alarm threshold (notify-only), slider + presets
 *
 * Control mode is read-only detected state — no Automatic/Manual input.
 * Python-owned 5-second poll pushes changed state; no JS battery timer.
 */

import { bridge, sendReady, getState, applyThreshold, restoreThreshold } from './bridge/client';
import type { BatteryState, AppearanceState } from './types/protocol';
import { t } from './i18n/t';

// ── Control mode labels (project glossary) ─────────────────────────────────

const CONTROL_MODE_LABELS: Record<string, string> = {
  'msi-ec': 'EC control — msi-ec',
  'sysfs': 'Vendor sysfs control',
  'notify': 'Notification only',
};

function controlModeLabel(mode: string | null): string {
  if (!mode) return '—';
  return CONTROL_MODE_LABELS[mode] || mode;
}

// ── Format helpers ──────────────────────────────────────────────────────────

function formatValue<T>(value: T | null, suffix: string = ''): string {
  return value !== null ? value + suffix : '—';
}

function formatCapacity(wh: number | null): string {
  return wh !== null ? wh.toFixed(1) + ' Wh' : '—';
}

function formatHealth(percent: number | null, grade: string | null): { percent: string; grade: string } {
  return {
    percent: percent !== null ? percent + '%' : '—',
    grade: grade || '',
  };
}

// ── DOM rendering ───────────────────────────────────────────────────────────

/** Render full battery state to the DOM. */
function renderBattery(state: BatteryState): void {
  const el = (id: string) => document.getElementById(id);

  // Battery Status card
  const pctEl = el('charge-percent');
  const statusEl = el('charge-status');
  const powerEl = el('power-source');
  const statusText = el('status-text');
  const liveDot = el('live-dot');

  if (pctEl) pctEl.textContent = formatValue(state.charge_percent, '%');
  if (statusEl) statusEl.textContent = state.charge_status || t('Unknown');
  if (powerEl) powerEl.textContent = state.power_source || '—';
  if (liveDot) liveDot.textContent = '●';

  // Device Information card
  const idEl = el('battery-identifier');
  const modeEl = el('control-mode');
  const healthPctEl = el('health-percent');
  const healthGradeEl = el('health-grade');
  const cycleEl = el('cycle-count');
  const fullCapEl = el('capacity-full');
  const designCapEl = el('capacity-design');

  if (idEl) idEl.textContent = state.battery_identifier || '—';
  if (modeEl) modeEl.textContent = controlModeLabel(state.control_mode);
  if (healthPctEl && healthGradeEl) {
    const h = formatHealth(state.health_percent, state.health_grade);
    healthPctEl.textContent = h.percent;
    healthGradeEl.textContent = h.grade ? ` (${h.grade})` : '';
  }
  if (cycleEl) cycleEl.textContent = formatValue(state.cycle_count);
  if (fullCapEl) fullCapEl.textContent = formatCapacity(state.capacity_full_wh);
  if (designCapEl) designCapEl.textContent = formatCapacity(state.capacity_design_wh);

  // Threshold card
  const thresholdEl = el('active-threshold');
  const alarmInfo = el('alarm-info');
  const alarmThreshold = el('alarm-threshold');
  const applyButton = el('apply-button');
  const restoreButton = el('restore-button');
  const slider = document.querySelector('[data-testid="threshold-slider"]') as HTMLElement;

  if (thresholdEl) {
    thresholdEl.textContent = formatValue(state.active_threshold, '%');
  }

  // Notification-only: distinguish alarm threshold from hardware threshold
  const isNotifyOnly = state.control_mode === 'notify';
  if (alarmInfo && alarmThreshold) {
    if (isNotifyOnly && state.alarm_armed) {
      alarmInfo.removeAttribute('hidden');
      alarmThreshold.textContent = formatValue(state.pending_threshold, '%') + ' (alarm)';
    } else {
      alarmInfo.setAttribute('hidden', 'true');
    }
  }

  // No-battery error state
  const errorState = el('error-state');
  const errorMessage = el('error-message');
  const batteryStatus = el('battery-status');
  const deviceInfo = el('device-info');
  const thresholdPanel = el('threshold-panel');

  if (!state.battery_available) {
    errorState?.removeAttribute('hidden');
    if (errorMessage) errorMessage.textContent = 'No charge-threshold-capable battery was found on this system.';
    batteryStatus?.setAttribute('hidden', 'true');
    deviceInfo?.setAttribute('hidden', 'true');
    thresholdPanel?.setAttribute('hidden', 'true');
    if (statusText) statusText.textContent = t('No battery detected');
    return;
  }

  // Battery available — hide error, show cards
  errorState?.setAttribute('hidden', 'true');
  batteryStatus?.removeAttribute('hidden');
  deviceInfo?.removeAttribute('hidden');
  thresholdPanel?.removeAttribute('hidden');
  if (statusText) statusText.textContent = t('Connected');
}

/** Apply theme scheme to the document root. */
function applyAppearance(appearance: AppearanceState): void {
  const root = document.documentElement;
  root.classList.remove('cds--g100', 'cds--white');
  root.classList.add(
    appearance.scheme === 'dark' ? 'cds--g100' : 'cds--white',
  );
}

/** Show a Carbon toast notification. */
function showToast(message: string, kind: 'success' | 'error' | 'info' = 'info'): void {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('cds-toast-notification');
  toast.setAttribute('kind', kind);
  toast.setAttribute('title', kind === 'error' ? t('Error') : kind === 'success' ? t('Success') : t('Info'));
  toast.textContent = message;

  container.appendChild(toast);

  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    if (toast.parentNode) {
      toast.parentNode.removeChild(toast);
    }
  }, 5000);
}

/** Sync presets with slider value. */
function syncPresets(value: number, presets: NodeListOf<HTMLElement>): void {
  presets.forEach(preset => {
    const presetValue = parseInt(preset.getAttribute('value') || '0');
    preset.setAttribute('selected', presetValue === value ? 'true' : 'false');
  });
}

/** Set controls enabled/disabled state. */
function setControlsEnabled(enabled: boolean): void {
  const slider = document.querySelector('[data-testid="threshold-slider"]') as HTMLElement;
  const applyButton = document.getElementById('apply-button');
  const restoreButton = document.getElementById('restore-button');

  if (enabled) {
    slider?.removeAttribute('disabled');
    applyButton?.removeAttribute('disabled');
    restoreButton?.removeAttribute('disabled');
  } else {
    slider?.setAttribute('disabled', 'true');
    applyButton?.setAttribute('disabled', 'true');
    restoreButton?.setAttribute('disabled', 'true');
  }
}

// ── Main initialization ─────────────────────────────────────────────────────

async function init(): Promise<void> {
  let isApplying = false;
  let pendingValue = 80;

  try {
    await sendReady();

    const stateData = await getState() as { state?: BatteryState; appearance?: AppearanceState };

    if (stateData.state) {
      renderBattery(stateData.state);

      // Initialize slider and presets from state
      if (stateData.state.active_threshold !== null) {
        pendingValue = stateData.state.active_threshold;
      } else if (stateData.state.pending_threshold !== null) {
        pendingValue = stateData.state.pending_threshold;
      }

      const slider = document.querySelector('[data-testid="threshold-slider"]') as HTMLElement;
      const floatingLabel = document.getElementById('floating-value-label');
      const presets = document.querySelectorAll<HTMLElement>('cds-radio-tile');

      slider?.setAttribute('value', pendingValue.toString());
      syncPresets(pendingValue, presets);
      if (floatingLabel) floatingLabel.textContent = pendingValue + '%';

      // Disable controls if no battery or no threshold capability
      const canWrite = stateData.state.battery_available &&
        stateData.state.control_mode !== 'notify';
      setControlsEnabled(canWrite);
    }

    if (stateData.appearance) {
      applyAppearance(stateData.appearance);
    }

    // ── Slider change handler ──────────────────────────────────────────────
    const slider = document.querySelector('[data-testid="threshold-slider"]') as HTMLElement;
    const floatingLabel = document.getElementById('floating-value-label');
    const presets = document.querySelectorAll<HTMLElement>('cds-radio-tile');
    const applyButton = document.getElementById('apply-button');
    const restoreButton = document.getElementById('restore-button');
    const pendingIndicator = document.getElementById('pending-indicator');

    slider?.addEventListener('cds-slider-input', (e: Event) => {
      const detail = (e as CustomEvent).detail;
      const value = parseInt(detail?.value?.toString() || '80');
      pendingValue = value;
      if (floatingLabel) floatingLabel.textContent = value + '%';
      syncPresets(value, presets);
    });

    // Preset handlers
    presets.forEach(preset => {
      preset.addEventListener('click', () => {
        const value = parseInt(preset.getAttribute('value') || '80');
        pendingValue = value;
        slider?.setAttribute('value', value.toString());
        if (floatingLabel) floatingLabel.textContent = value + '%';
        syncPresets(value, presets);
      });
    });

    // Apply button handler
    applyButton?.addEventListener('click', async () => {
      if (isApplying) return;

      isApplying = true;
      applyButton.setAttribute('disabled', 'true');
      restoreButton?.setAttribute('disabled', 'true');
      pendingIndicator?.removeAttribute('hidden');

      try {
        const result = await applyThreshold(pendingValue) as any;

        if (result.threshold !== undefined) {
          showToast(t('Threshold set to {value}%').replace('{value}', result.threshold.toString()), 'success');

          const thresholdEl = document.getElementById('active-threshold');
          if (thresholdEl) thresholdEl.textContent = result.threshold + '%';
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : t('Unknown error');
        showToast(t('Failed to set threshold: {message}').replace('{message}', message), 'error');
      } finally {
        isApplying = false;
        applyButton.removeAttribute('disabled');
        restoreButton?.removeAttribute('disabled');
        pendingIndicator?.setAttribute('hidden', 'true');
      }
    });

    // Restore button handler
    restoreButton?.addEventListener('click', async () => {
      if (isApplying) return;

      isApplying = true;
      applyButton?.setAttribute('disabled', 'true');
      restoreButton.setAttribute('disabled', 'true');
      pendingIndicator?.removeAttribute('hidden');

      try {
        const result = await restoreThreshold() as any;

        if (result.threshold !== undefined) {
          showToast(t('Threshold restored to 100%'), 'success');

          pendingValue = 100;
          slider?.setAttribute('value', '100');
          if (floatingLabel) floatingLabel.textContent = '100%';
          syncPresets(100, presets);

          const thresholdEl = document.getElementById('active-threshold');
          if (thresholdEl) thresholdEl.textContent = '100%';
        }
      } catch (error) {
        const message = error instanceof Error ? error.message : t('Unknown error');
        showToast(t('Failed to restore threshold: {message}').replace('{message}', message), 'error');
      } finally {
        isApplying = false;
        applyButton?.removeAttribute('disabled');
        restoreButton.removeAttribute('disabled');
        pendingIndicator?.setAttribute('hidden', 'true');
      }
    });

    // ── Listen for state updates from Python poll ──────────────────────────
    bridge.on('battery', (data) => {
      if (data) {
        renderBattery(data as unknown as BatteryState);
      }
    });

    bridge.on('appearance', (data) => {
      if (data) {
        applyAppearance(data as unknown as AppearanceState);
      }
    });

    console.log('Threshold Carbon shell ready');
  } catch (err) {
    console.error('Threshold Carbon shell init failed:', err);
    const statusText = document.getElementById('status-text');
    if (statusText) {
      statusText.textContent = t('Connection failed');
    }
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
