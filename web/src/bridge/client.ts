/**
 * Bridge client - promise-based JS to Python communication.
 *
 * Hides webkit.messageHandlers from application modules.
 * Injected as a document-start UserScript shim.
 */

import type { BridgeRequest, BridgeResponse, BridgeEvent } from '../types/protocol';

/** Event listener callback type. */
type EventCallback = (data?: Record<string, unknown>) => void;

/** Pending request tracker. */
interface PendingRequest {
  resolve: (response: BridgeResponse) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

/** Default timeout for bridge requests (ms). */
const REQUEST_TIMEOUT_MS = 30_000;

/** Bridge client singleton. */
class BridgeClient {
  private _pending = new Map<string, PendingRequest>();
  private _listeners = new Map<string, Set<EventCallback>>();
  private _nextId = 0;
  private _ready = false;

  /** Generate a unique request ID. */
  private _generateId(): string {
    return 'req-' + Date.now() + '-' + this._nextId++;
  }

  /**
   * Send a request to Python and wait for response.
   * Returns the response data or throws on error.
   */
  async request<T = Record<string, unknown>>(
    cmd: string,
    args?: Record<string, unknown>,
    timeoutMs = REQUEST_TIMEOUT_MS,
  ): Promise<T> {
    const id = this._generateId();
    const request: BridgeRequest = { id, cmd, args };

    return new Promise<T>((resolve, reject) => {
      const timer = setTimeout(() => {
        this._pending.delete(id);
        reject(new Error('Bridge request timed out: ' + cmd + ' (' + id + ')'));
      }, timeoutMs);

      this._pending.set(id, {
        resolve: (response: BridgeResponse) => {
          clearTimeout(timer);
          if (response.ok) {
            resolve(response.data as T);
          } else {
            reject(new Error(response.error || 'Unknown bridge error'));
          }
        },
        reject: (error: Error) => {
          clearTimeout(timer);
          reject(error);
        },
        timer,
      });

      this._postMessage(request);
    });
  }

  /**
   * Register an event listener for push events from Python.
   * Returns an unsubscribe function.
   */
  on(event: string, callback: EventCallback): () => void {
    if (!this._listeners.has(event)) {
      this._listeners.set(event, new Set());
    }
    this._listeners.get(event)!.add(callback);

    return () => {
      this._listeners.get(event)?.delete(callback);
    };
  }

  /**
   * Handle an incoming message from Python.
   * Called by the document-start shim when webkit.messageHandlers fires.
   */
  _handleMessage(raw: string): void {
    let msg: unknown;
    try {
      msg = JSON.parse(raw);
    } catch {
      console.error('Bridge: malformed message', raw);
      return;
    }

    // Response to a pending request
    if (this._isResponse(msg)) {
      const pending = this._pending.get(msg.id);
      if (pending) {
        this._pending.delete(msg.id);
        pending.resolve(msg);
      }
      return;
    }

    // Push event
    if (this._isEvent(msg)) {
      const listeners = this._listeners.get(msg.event);
      if (listeners) {
        for (const cb of listeners) {
          try {
            cb(msg.data);
          } catch (err) {
            console.error('Bridge: error in event listener for ' + msg.event, err);
          }
        }
      }
      return;
    }

    console.warn('Bridge: unknown message shape', msg);
  }

  /** Mark bridge as ready after handshake. */
  _setReady(): void {
    this._ready = true;
  }

  /** Whether the bridge has completed the ready handshake. */
  get isReady(): boolean {
    return this._ready;
  }

  /** Post a message to Python via WebKit message handler. */
  private _postMessage(msg: BridgeRequest): void {
    const handler = (window as any).webkit?.messageHandlers?.threshold;
    if (!handler) {
      console.error('Bridge: webkit.messageHandlers.threshold not available');
      return;
    }
    handler.postMessage(JSON.stringify(msg));
  }

  /** Type guard: is this a BridgeResponse? */
  private _isResponse(msg: unknown): msg is BridgeResponse {
    return (
      typeof msg === 'object' &&
      msg !== null &&
      'id' in msg &&
      'ok' in msg
    );
  }

  /** Type guard: is this a BridgeEvent? */
  private _isEvent(msg: unknown): msg is BridgeEvent {
    return (
      typeof msg === 'object' &&
      msg !== null &&
      'event' in msg &&
      !('id' in msg)
    );
  }
}

/** Singleton bridge client instance. */
export const bridge = new BridgeClient();

/**
 * Send a ready handshake to Python.
 * Python responds with initial state after receiving this.
 */
export async function sendReady(): Promise<void> {
  await bridge.request('ready');
  bridge._setReady();
}

/**
 * Request the current application state from Python.
 */
export async function getState(): Promise<Record<string, unknown>> {
  return bridge.request('get_state');
}

/**
 * Apply a charge threshold via the bridge.
 */
export async function applyThreshold(threshold: number): Promise<Record<string, unknown>> {
  return bridge.request('apply_threshold', { threshold });
}

/**
 * Restore threshold to 100% via the bridge.
 */
export async function restoreThreshold(): Promise<Record<string, unknown>> {
  return bridge.request('restore_threshold');
}

/**
 * Set dark mode preference via the bridge.
 */
export async function setDarkMode(value: boolean): Promise<Record<string, unknown>> {
  return bridge.request('set_dark_mode', { value });
}

/**
 * Set accent color preference via the bridge.
 */
export async function setAccentColor(value: string): Promise<Record<string, unknown>> {
  return bridge.request('set_accent_color', { value });
}

/**
 * Set compact mode preference via the bridge.
 */
export async function setCompactMode(value: boolean): Promise<Record<string, unknown>> {
  return bridge.request('set_compact_mode', { value });
}

/**
 * Set title percentage preference via the bridge.
 */
export async function setTitlePercentage(value: boolean): Promise<Record<string, unknown>> {
  return bridge.request('set_title_percentage', { value });
}
