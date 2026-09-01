/**
 * Bridge protocol types - shared between Python and TypeScript.
 *
 * JS to Python: { id: string, cmd: string, args?: Record<string, unknown> }
 * Python to JS: { id: string, ok: boolean, data?: unknown, error?: string }
 */

/** Request from JS to Python bridge. */
export interface BridgeRequest {
  id: string;
  cmd: string;
  args?: Record<string, unknown>;
}

/** Response from Python bridge to JS. */
export interface BridgeResponse {
  id: string;
  ok: boolean;
  data?: Record<string, unknown>;
  error?: string;
}

/** Push event from Python to JS (not request/response). */
export interface BridgeEvent {
  event: string;
  data?: Record<string, unknown>;
}

/** Battery state snapshot pushed by Python. */
export interface BatteryState {
  battery_available: boolean;
  charge_percent: number | null;
  charge_status: string | null;
  active_threshold: number | null;
  pending_threshold: number | null;
  control_mode: string | null;
  battery_identifier: string | null;
  health_percent: number | null;
  health_grade: string | null;
  power_source: string | null;
  cycle_count: number | null;
  capacity_full_wh: number | null;
  capacity_design_wh: number | null;
  alarm_armed: boolean;
  alarm_fired: boolean;
  dark_mode: boolean;
  accent_color: string;
  compact_mode: boolean;
  title_percentage: boolean;
}

/** Theme appearance pushed by Python. */
export interface AppearanceState {
  scheme: 'light' | 'dark';
  accent_color: string;
}

/** Protocol message envelope for JSON serialization. */
export type BridgeMessage = BridgeRequest | BridgeResponse | BridgeEvent;

/** Type guard: is this a request? */
export function isBridgeRequest(msg: BridgeMessage): msg is BridgeRequest {
  return 'cmd' in msg && 'id' in msg;
}

/** Type guard: is this a response? */
export function isBridgeResponse(msg: BridgeMessage): msg is BridgeResponse {
  return 'ok' in msg && 'id' in msg;
}

/** Type guard: is this a push event? */
export function isBridgeEvent(msg: BridgeMessage): msg is BridgeEvent {
  return 'event' in msg && !('id' in msg);
}

/** Threshold application result from Python. */
export interface ThresholdResult {
  threshold: number;
  method: string;
  ec_mismatch: boolean;
}

/** Error codes from Python command dispatcher. */
export type ErrorCode = 
  | 'unknown_command'
  | 'invalid_args'
  | 'threshold_out_of_range'
  | 'no_battery'
  | 'write_failed'
  | 'permission_denied'
  | 'ec_mismatch';
