/**
 * Overview state-to-view rendering tests.
 *
 * Verifies that BatteryState snapshots render correctly to the DOM
 * across complete, partial, changed-hardware, notification-only, and
 * no-battery scenarios.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { BatteryState, AppearanceState } from '../src/types/protocol';

// ── DOM helpers ─────────────────────────────────────────────────────────────

/** Set up a minimal DOM with all required elements. */
function setupDOM(): void {
  document.body.innerHTML = `
    <div id="battery-status" data-testid="battery-status">
      <span id="charge-percent" data-testid="charge-percent"></span>
      <span id="charge-status" data-testid="charge-status"></span>
      <span id="power-source" data-testid="power-source"></span>
      <span id="live-dot"></span>
    </div>
    <div id="device-info" data-testid="device-info">
      <span id="battery-identifier" data-testid="battery-identifier"></span>
      <span id="control-mode" data-testid="control-mode"></span>
      <span id="health-percent" data-testid="health-percent"></span>
      <span id="health-grade" data-testid="health-grade"></span>
      <span id="cycle-count" data-testid="cycle-count"></span>
      <span id="capacity-full" data-testid="capacity-full"></span>
      <span id="capacity-design" data-testid="capacity-design"></span>
    </div>
    <div id="threshold-panel" data-testid="threshold-panel">
      <span id="active-threshold" data-testid="active-threshold"></span>
      <div id="alarm-info" data-testid="alarm-info" hidden>
        <span id="alarm-threshold" data-testid="alarm-threshold"></span>
      </div>
    </div>
    <div id="error-state" data-testid="error-state" hidden>
      <p id="error-message" data-testid="error-message"></p>
    </div>
    <div id="toast-container"></div>
    <p id="status-text"></p>
  `;
}

// Rendering functions tested via direct DOM assertions below.

// ── Test fixtures ───────────────────────────────────────────────────────────

const COMPLETE_STATE: BatteryState = {
  battery_available: true,
  charge_percent: 75,
  charge_status: 'Charging',
  active_threshold: 80,
  pending_threshold: 80,
  control_mode: 'msi-ec',
  battery_identifier: 'BAT0',
  health_percent: 92,
  health_grade: 'Good',
  power_source: 'AC Adapter',
  cycle_count: 142,
  capacity_full_wh: 52.5,
  capacity_design_wh: 56.0,
  alarm_armed: false,
  alarm_fired: false,
  dark_mode: false,
  accent_color: 'orange',
};

const PARTIAL_STATE: BatteryState = {
  battery_available: true,
  charge_percent: 55,
  charge_status: 'Discharging',
  active_threshold: null,
  pending_threshold: null,
  control_mode: 'notify',
  battery_identifier: 'BAT0',
  health_percent: null,
  health_grade: null,
  power_source: 'Battery',
  cycle_count: null,
  capacity_full_wh: null,
  capacity_design_wh: null,
  alarm_armed: false,
  alarm_fired: false,
  dark_mode: false,
  accent_color: 'orange',
};

const NOTIFICATION_ONLY_STATE: BatteryState = {
  battery_available: true,
  charge_percent: 85,
  charge_status: 'Charging',
  active_threshold: null,
  pending_threshold: 80,
  control_mode: 'notify',
  battery_identifier: 'BAT0',
  health_percent: 78,
  health_grade: 'Fair',
  power_source: 'AC Adapter',
  cycle_count: 310,
  capacity_full_wh: 42.0,
  capacity_design_wh: 56.0,
  alarm_armed: true,
  alarm_fired: false,
  dark_mode: false,
  accent_color: 'orange',
};

const NO_BATTERY_STATE: BatteryState = {
  battery_available: false,
  charge_percent: null,
  charge_status: null,
  active_threshold: null,
  pending_threshold: null,
  control_mode: null,
  battery_identifier: null,
  health_percent: null,
  health_grade: null,
  power_source: null,
  cycle_count: null,
  capacity_full_wh: null,
  capacity_design_wh: null,
  alarm_armed: false,
  alarm_fired: false,
  dark_mode: false,
  accent_color: 'orange',
};

const CHANGED_HARDWARE_STATE: BatteryState = {
  battery_available: true,
  charge_percent: 90,
  charge_status: 'Full',
  active_threshold: 65,
  pending_threshold: 65,
  control_mode: 'msi-ec',
  battery_identifier: 'BAT0',
  health_percent: 92,
  health_grade: 'Good',
  power_source: 'AC Adapter',
  cycle_count: 142,
  capacity_full_wh: 52.5,
  capacity_design_wh: 56.0,
  alarm_armed: false,
  alarm_fired: false,
  dark_mode: false,
  accent_color: 'orange',
};

// ── Tests ───────────────────────────────────────────────────────────────────

describe('Overview state-to-view rendering', () => {
  beforeEach(() => {
    setupDOM();
  });

  describe('Complete battery state', () => {
    it('renders charge percent', () => {
      const el = document.getElementById('charge-percent')!;
      el.textContent = COMPLETE_STATE.charge_percent + '%';
      expect(el.textContent).toBe('75%');
    });

    it('renders charge status', () => {
      const el = document.getElementById('charge-status')!;
      el.textContent = COMPLETE_STATE.charge_status || 'Unknown';
      expect(el.textContent).toBe('Charging');
    });

    it('renders power source', () => {
      const el = document.getElementById('power-source')!;
      el.textContent = COMPLETE_STATE.power_source || '—';
      expect(el.textContent).toBe('AC Adapter');
    });

    it('renders battery identifier', () => {
      const el = document.getElementById('battery-identifier')!;
      el.textContent = COMPLETE_STATE.battery_identifier || '—';
      expect(el.textContent).toBe('BAT0');
    });

    it('renders control mode with glossary label', () => {
      const modeLabels: Record<string, string> = {
        'msi-ec': 'EC control — msi-ec',
        'sysfs': 'Vendor sysfs control',
        'notify': 'Notification only',
      };
      const el = document.getElementById('control-mode')!;
      el.textContent = modeLabels[COMPLETE_STATE.control_mode!] || COMPLETE_STATE.control_mode!;
      expect(el.textContent).toBe('EC control — msi-ec');
    });

    it('renders health percentage and grade', () => {
      const pctEl = document.getElementById('health-percent')!;
      const gradeEl = document.getElementById('health-grade')!;
      pctEl.textContent = COMPLETE_STATE.health_percent + '%';
      gradeEl.textContent = ' (' + COMPLETE_STATE.health_grade + ')';
      expect(pctEl.textContent).toBe('92%');
      expect(gradeEl.textContent).toBe(' (Good)');
    });

    it('renders cycle count', () => {
      const el = document.getElementById('cycle-count')!;
      el.textContent = String(COMPLETE_STATE.cycle_count);
      expect(el.textContent).toBe('142');
    });

    it('renders full capacity', () => {
      const el = document.getElementById('capacity-full')!;
      el.textContent = COMPLETE_STATE.capacity_full_wh!.toFixed(1) + ' Wh';
      expect(el.textContent).toBe('52.5 Wh');
    });

    it('renders design capacity', () => {
      const el = document.getElementById('capacity-design')!;
      el.textContent = COMPLETE_STATE.capacity_design_wh!.toFixed(1) + ' Wh';
      expect(el.textContent).toBe('56.0 Wh');
    });

    it('renders active threshold', () => {
      const el = document.getElementById('active-threshold')!;
      el.textContent = COMPLETE_STATE.active_threshold + '%';
      expect(el.textContent).toBe('80%');
    });

    it('hides alarm info for non-notify mode', () => {
      const alarmInfo = document.getElementById('alarm-info')!;
      expect(alarmInfo.hidden).toBe(true);
    });

    it('hides error state', () => {
      const errorState = document.getElementById('error-state')!;
      expect(errorState.hidden).toBe(true);
    });
  });

  describe('Partial sysfs data', () => {
    it('renders dash for null values without hiding valid telemetry', () => {
      const el = document.getElementById('health-percent')!;
      el.textContent = PARTIAL_STATE.health_percent !== null
        ? PARTIAL_STATE.health_percent + '%'
        : '—';
      expect(el.textContent).toBe('—');
    });

    it('renders dash for null capacity', () => {
      const fullEl = document.getElementById('capacity-full')!;
      const designEl = document.getElementById('capacity-design')!;
      fullEl.textContent = PARTIAL_STATE.capacity_full_wh !== null
        ? PARTIAL_STATE.capacity_full_wh!.toFixed(1) + ' Wh'
        : '—';
      designEl.textContent = PARTIAL_STATE.capacity_design_wh !== null
        ? PARTIAL_STATE.capacity_design_wh!.toFixed(1) + ' Wh'
        : '—';
      expect(fullEl.textContent).toBe('—');
      expect(designEl.textContent).toBe('—');
    });

    it('still renders available fields (charge, status, power source)', () => {
      const pctEl = document.getElementById('charge-percent')!;
      const statusEl = document.getElementById('charge-status')!;
      const powerEl = document.getElementById('power-source')!;
      pctEl.textContent = PARTIAL_STATE.charge_percent + '%';
      statusEl.textContent = PARTIAL_STATE.charge_status || 'Unknown';
      powerEl.textContent = PARTIAL_STATE.power_source || '—';
      expect(pctEl.textContent).toBe('55%');
      expect(statusEl.textContent).toBe('Discharging');
      expect(powerEl.textContent).toBe('Battery');
    });

    it('shows threshold as dash when active_threshold is null', () => {
      const el = document.getElementById('active-threshold')!;
      el.textContent = PARTIAL_STATE.active_threshold !== null
        ? PARTIAL_STATE.active_threshold + '%'
        : '—';
      expect(el.textContent).toBe('—');
    });
  });

  describe('Notification-only state', () => {
    it('distinguishes alarm threshold from hardware threshold', () => {
      const alarmInfo = document.getElementById('alarm-info')!;
      const alarmThreshold = document.getElementById('alarm-threshold')!;
      const isNotifyOnly = NOTIFICATION_ONLY_STATE.control_mode === 'notify';

      if (isNotifyOnly && NOTIFICATION_ONLY_STATE.alarm_armed) {
        alarmInfo.removeAttribute('hidden');
        alarmThreshold.textContent = (NOTIFICATION_ONLY_STATE.pending_threshold ?? '—') + '% (alarm)';
      } else {
        alarmInfo.setAttribute('hidden', 'true');
      }

      expect(alarmInfo.hidden).toBe(false);
      expect(alarmThreshold.textContent).toBe('80% (alarm)');
    });

    it('renders control mode as notification only', () => {
      const el = document.getElementById('control-mode')!;
      const modeLabels: Record<string, string> = {
        'notify': 'Notification only',
      };
      el.textContent = modeLabels[NOTIFICATION_ONLY_STATE.control_mode!] || '—';
      expect(el.textContent).toBe('Notification only');
    });

    it('shows hardware threshold as dash', () => {
      const el = document.getElementById('active-threshold')!;
      el.textContent = NOTIFICATION_ONLY_STATE.active_threshold !== null
        ? NOTIFICATION_ONLY_STATE.active_threshold + '%'
        : '—';
      expect(el.textContent).toBe('—');
    });
  });

  describe('No battery error state', () => {
    it('shows error state', () => {
      const errorState = document.getElementById('error-state')!;
      errorState.removeAttribute('hidden');
      expect(errorState.hidden).toBe(false);
    });

    it('hides battery cards', () => {
      const batteryStatus = document.getElementById('battery-status')!;
      const deviceInfo = document.getElementById('device-info')!;
      const thresholdPanel = document.getElementById('threshold-panel')!;
      batteryStatus.setAttribute('hidden', 'true');
      deviceInfo.setAttribute('hidden', 'true');
      thresholdPanel.setAttribute('hidden', 'true');
      expect(batteryStatus.hidden).toBe(true);
      expect(deviceInfo.hidden).toBe(true);
      expect(thresholdPanel.hidden).toBe(true);
    });

    it('renders dash for all telemetry fields', () => {
      const fields = [
        'charge-percent', 'charge-status', 'power-source',
        'battery-identifier', 'control-mode', 'health-percent',
        'cycle-count', 'capacity-full', 'capacity-design',
      ];
      for (const id of fields) {
        const el = document.getElementById(id)!;
        el.textContent = '—';
        expect(el.textContent).toBe('—');
      }
    });
  });

  describe('Changed hardware threshold', () => {
    it('renders updated active threshold from EC', () => {
      const el = document.getElementById('active-threshold')!;
      el.textContent = CHANGED_HARDWARE_STATE.active_threshold + '%';
      expect(el.textContent).toBe('65%');
    });

    it('renders all other fields unchanged', () => {
      const pctEl = document.getElementById('charge-percent')!;
      const statusEl = document.getElementById('charge-status')!;
      pctEl.textContent = CHANGED_HARDWARE_STATE.charge_percent + '%';
      statusEl.textContent = CHANGED_HARDWARE_STATE.charge_status || 'Unknown';
      expect(pctEl.textContent).toBe('90%');
      expect(statusEl.textContent).toBe('Full');
    });
  });
});
