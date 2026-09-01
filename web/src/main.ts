/**
 * Threshold Carbon shell - entry point.
 *
 * Sends ready handshake, requests state, renders battery overview.
 */

import { bridge, sendReady, getState } from './bridge/client';
import type { BatteryState, AppearanceState } from './types/protocol';
import { t } from './i18n/t';

/** Render battery state to the DOM. */
function renderBattery(state: BatteryState): void {
  const pctEl = document.getElementById('charge-percent');
  const statusEl = document.getElementById('charge-status');
  const thresholdEl = document.getElementById('active-threshold');
  const statusText = document.getElementById('status-text');

  if (pctEl) {
    pctEl.textContent = state.charge_percent !== null
      ? state.charge_percent + '%'
      : '--%';
  }

  if (statusEl) {
    statusEl.textContent = state.charge_status || t('Unknown');
  }

  if (thresholdEl) {
    thresholdEl.textContent = state.active_threshold !== null
      ? state.active_threshold + '%'
      : '--%';
  }

  if (statusText) {
    statusText.textContent = state.battery_available
      ? t('Connected')
      : t('No battery detected');
  }
}

/** Apply theme scheme to the document root. */
function applyAppearance(appearance: AppearanceState): void {
  const root = document.documentElement;
  root.classList.remove('cds--g100', 'cds--white');
  root.classList.add(
    appearance.scheme === 'dark' ? 'cds--g100' : 'cds--white',
  );
}

/** Main initialization. */
async function init(): Promise<void> {
  try {
    await sendReady();

    const stateData = await getState() as { state?: BatteryState; appearance?: AppearanceState };

    if (stateData.state) {
      renderBattery(stateData.state);
    }

    if (stateData.appearance) {
      applyAppearance(stateData.appearance);
    }

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
