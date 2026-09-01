import { afterEach, describe, expect, it, vi } from 'vitest';
import { bridge } from '../src/bridge/client';

describe('injected WebKit bridge', () => {
  afterEach(() => {
    delete (window as any).threshold;
    delete (window as any).webkit;
    (bridge as any)._pending.clear();
  });

  it('delegates requests to document-start shim', async () => {
    const request = vi.fn().mockResolvedValue({ state: { battery_available: true } });
    (window as any).threshold = { request, on: vi.fn() };

    const result = await bridge.request('get_state');

    expect(request).toHaveBeenCalledWith('get_state', undefined);
    expect(result).toEqual({ state: { battery_available: true } });
  });
});
