/**
 * Bridge client tests - contract fixtures and protocol behaviour.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { bridge, sendReady, getState, applyThreshold, restoreThreshold } from '../src/bridge/client';
import fixtures from './fixtures/messages.json';

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

/** Reject the next pending request with an error. */
function rejectPending(error: string): void {
  const pending = (bridge as any)._pending;
  const key = pending.keys().next().value;
  if (!key) return;
  const response = { id: key, ok: false, error };
  bridge._handleMessage(JSON.stringify(response));
}

describe('Bridge protocol', () => {
  beforeEach(() => {
    // Reset the bridge state
    (bridge as any)._pending.clear();
    (bridge as any)._ready = false;
    (bridge as any)._nextId = 0;
    // Clear all listeners
    for (const listeners of (bridge as any)._listeners.values()) {
      listeners.clear();
    }
  });

  describe('Request/Response', () => {
    it('sends a request with id, cmd, and args', () => {
      const { messages } = mockWebKit();
      bridge.request('apply_threshold', { threshold: 80 });

      expect(messages).toHaveLength(1);
      const sent = JSON.parse(messages[0]);
      expect(sent.id).toMatch(/^req-\d+-0$/);
      expect(sent.cmd).toBe('apply_threshold');
      expect(sent.args).toEqual({ threshold: 80 });
    });

    it('resolves when Python responds with matching id', async () => {
      mockWebKit();
      const promise = bridge.request('ready');
      resolvePending(fixtures.ready_response.data);

      const result = await promise;
      expect(result).toEqual(fixtures.ready_response.data);
    });

    it('rejects when Python responds with error', async () => {
      mockWebKit();
      const promise = bridge.request('nonexistent');
      rejectPending(fixtures.unknown_command_response.error!);

      await expect(promise).rejects.toThrow('Unknown command: nonexistent_command');
    });

    it('rejects on timeout', async () => {
      mockWebKit();
      vi.useFakeTimers();
      const promise = bridge.request('slow_cmd', undefined, 100);
      vi.advanceTimersByTime(101);

      await expect(promise).rejects.toThrow('Bridge request timed out');
      vi.useRealTimers();
    });

    it('rejects with permission denied error', async () => {
      mockWebKit();
      const promise = bridge.request('apply_threshold', { threshold: 80 });
      rejectPending('Permission denied: need root privileges');

      await expect(promise).rejects.toThrow('Permission denied: need root privileges');
    });
  });

  describe('Push events', () => {
    it('dispatches battery events to listeners', () => {
      mockWebKit();
      const callback = vi.fn();
      bridge.on('battery', callback);

      bridge._handleMessage(JSON.stringify(fixtures.battery_push_event));

      expect(callback).toHaveBeenCalledWith(fixtures.battery_push_event.data);
    });

    it('dispatches appearance events to listeners', () => {
      mockWebKit();
      const callback = vi.fn();
      bridge.on('appearance', callback);

      bridge._handleMessage(JSON.stringify(fixtures.appearance_push_event));

      expect(callback).toHaveBeenCalledWith(fixtures.appearance_push_event.data);
    });

    it('unsubscribes correctly', () => {
      mockWebKit();
      const callback = vi.fn();
      const unsub = bridge.on('battery', callback);

      bridge._handleMessage(JSON.stringify(fixtures.battery_push_event));
      expect(callback).toHaveBeenCalledTimes(1);

      unsub();
      bridge._handleMessage(JSON.stringify(fixtures.battery_push_event));
      expect(callback).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error handling', () => {
    it('handles malformed JSON gracefully', () => {
      mockWebKit();
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
      bridge._handleMessage(fixtures.malformed_request);
      expect(consoleSpy).toHaveBeenCalledWith('Bridge: malformed message', fixtures.malformed_request);
      consoleSpy.mockRestore();
    });

    it('ignores unknown message shapes', () => {
      mockWebKit();
      const consoleSpy = vi.spyOn(console, 'warn').mockImplementation(() => {});
      bridge._handleMessage(JSON.stringify({ unknown: true }));
      expect(consoleSpy).toHaveBeenCalled();
      consoleSpy.mockRestore();
    });
  });
});

describe('sendReady', () => {
  it('sends ready command and marks bridge as ready', async () => {
    mockWebKit();
    const promise = sendReady();
    resolvePending(fixtures.ready_response.data);

    await promise;
    expect(bridge.isReady).toBe(true);
  });
});

describe('getState', () => {
  it('returns the state data from Python', async () => {
    mockWebKit();
    const promise = getState();
    resolvePending(fixtures.get_state_response.data);

    const result = await promise as any;
    expect(result.state).toBeDefined();
    expect(result.state.battery_available).toBe(true);
    expect(result.state.charge_percent).toBe(75);
  });
});

describe('applyThreshold', () => {
  it('sends apply_threshold with correct args', async () => {
    const { messages } = mockWebKit();
    const promise = applyThreshold(80);
    resolvePending(fixtures.set_threshold_response.data);

    const result = await promise;
    expect(messages).toHaveLength(1);
    const sent = JSON.parse(messages[0]);
    expect(sent.cmd).toBe('apply_threshold');
    expect(sent.args).toEqual({ threshold: 80 });
    expect(result.threshold).toBe(80);
  });

  it('handles EC mismatch response', async () => {
    mockWebKit();
    const promise = applyThreshold(80);
    resolvePending(fixtures.ec_mismatch_response.data);

    const result = await promise as any;
    expect(result.threshold).toBe(80);
    expect(result.ec_mismatch).toBe(true);
    expect(result.ec_actual).toBe(85);
  });

  it('handles notification-only mode', async () => {
    mockWebKit();
    const promise = applyThreshold(80);
    resolvePending(fixtures.notification_only_response.data);

    const result = await promise as any;
    expect(result.threshold).toBe(80);
    expect(result.method).toBe('alarm');
    expect(result.ec_mismatch).toBe(false);
  });
});

describe('restoreThreshold', () => {
  it('sends restore_threshold command', async () => {
    const { messages } = mockWebKit();
    const promise = restoreThreshold();
    resolvePending(fixtures.restore_threshold_response.data);

    const result = await promise;
    expect(messages).toHaveLength(1);
    const sent = JSON.parse(messages[0]);
    expect(sent.cmd).toBe('restore_threshold');
    expect(sent.args).toBeUndefined();
    expect(result.threshold).toBe(100);
  });
});