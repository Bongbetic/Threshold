/**
 * Threshold Carbon shell - entry point.
 *
 * Sends ready handshake, requests state, renders battery overview.
 * Handles charge limit UI interactions.
 */

import { bridge, sendReady, getState, applyThreshold, restoreThreshold } from './bridge/client';
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

/** Show a Carbon toast notification. */
function showToast(message: string, type: 'success' | 'error' | 'info' = 'info'): void {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('cds-toast-notification');
  toast.setAttribute('kind', type === 'error' ? 'error' : type === 'success' ? 'success' : 'info');
  toast.setAttribute('title', type === 'error' ? t('Error') : type === 'success' ? t('Success') : t('Info'));
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

    // Set up charge limit controls
    const slider = document.querySelector('cds-slider') as HTMLElement;
    const floatingLabel = document.getElementById('floating-value-label');
    const applyButton = document.getElementById('apply-button') as HTMLElement;
    const restoreButton = document.getElementById('restore-button') as HTMLElement;
    const pendingIndicator = document.getElementById('pending-indicator');
    const presets = document.querySelectorAll<HTMLElement>('cds-radio-tile');
    
    let isApplying = false;
    let pendingValue = 80;

    // Initialize slider value from state
    if (stateData.state?.active_threshold) {
      pendingValue = stateData.state.active_threshold;
      slider?.setAttribute('value', pendingValue.toString());
      syncPresets(pendingValue, presets);
      if (floatingLabel) {
        floatingLabel.textContent = pendingValue + '%';
      }
    }

    // Slider change handler
    slider?.addEventListener('cds-slider-input', (e: Event) => {
      const detail = (e as CustomEvent).detail;
      const value = parseInt(detail?.value?.toString() || '80');
      pendingValue = value;
      if (floatingLabel) {
        floatingLabel.textContent = value + '%';
      }
      syncPresets(value, presets);
    });

    // Preset handlers
    presets.forEach(preset => {
      preset.addEventListener('click', () => {
        const value = parseInt(preset.getAttribute('value') || '80');
        pendingValue = value;
        slider?.setAttribute('value', value.toString());
        if (floatingLabel) {
          floatingLabel.textContent = value + '%';
        }
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
          
          // Update active threshold display
          const thresholdEl = document.getElementById('active-threshold');
          if (thresholdEl) {
            thresholdEl.textContent = result.threshold + '%';
          }
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
          
          // Update slider and display
          pendingValue = 100;
          slider?.setAttribute('value', '100');
          if (floatingLabel) {
            floatingLabel.textContent = '100%';
          }
          syncPresets(100, presets);
          
          // Update active threshold display
          const thresholdEl = document.getElementById('active-threshold');
          if (thresholdEl) {
            thresholdEl.textContent = '100%';
          }
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

    // Listen for state updates from Python
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
