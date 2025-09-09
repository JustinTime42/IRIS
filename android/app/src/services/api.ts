import { Config } from '../shared/config';
import type { WeatherState, FreezerState, DoorState, DevicesResponse, LightState, AlertItem, WeatherHistoryPoint } from '../types/api';

/**
 * Simple JSON fetch helper with logging and timeout.
 * # Reason: Centralize base URL and JSON handling for consistency and easier error tracing.
 */
async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const url = `${Config.baseUrl}${path}`;
  const method = init?.method || 'GET';

  // 10s timeout
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 10_000);

  console.debug(`[api] ${method} ${url}`);

  try {
    const res = await fetch(url, {
      ...init,
      headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
      signal: controller.signal,
    });

    if (!res.ok) {
      const text = await res.text().catch(() => '');
      const msg = `HTTP ${res.status} ${res.statusText} for ${url}${text ? `: ${text}` : ''}`;
      console.error(`[api] ${method} ${url} → ${msg}`);
      throw new Error(msg);
    }

    const data = (await res.json()) as T;
    console.debug(`[api] ${method} ${url} ✓`);
    return data;
  } catch (err: any) {
    if (err?.name === 'AbortError') {
      console.error(`[api] ${method} ${url} → Timeout after 10s`);
      throw new Error(`Timeout fetching ${url}`);
    }
    console.error(`[api] ${method} ${url} → ${err?.message || String(err)}`);
    throw err;
  } finally {
    clearTimeout(timeout);
  }
}

export const api = {
  // Garage Weather
  getGarageWeather: () => jsonFetch<WeatherState>('/api/garage/weather'),
  getWeatherHistory: (opts?: { range?: string; bucket?: 'minute' | 'hour' | 'day'; start?: string; end?: string }) => {
    const p = new URLSearchParams();
    if (opts?.start) p.set('start', opts.start);
    if (opts?.end) p.set('end', opts.end);
    if (opts?.range) p.set('range', opts.range);
    if (opts?.bucket) p.set('bucket', opts.bucket);
    const qs = p.toString();
    return jsonFetch<WeatherHistoryPoint[]>(`/api/garage/weather/history${qs ? `?${qs}` : ''}`);
  },

  // Garage Freezer
  getGarageFreezer: () => jsonFetch<FreezerState>('/api/garage/freezer'),

  // Garage Door
  getDoorState: () => jsonFetch<{ state: DoorState }>('/api/garage/door/state'),
  doorCommand: (command: 'open' | 'close' | 'toggle') =>
    jsonFetch<unknown>(`/api/garage/door/${command}`, { method: 'POST' }),

  // Flood Light
  getLightState: () => jsonFetch<LightState>('/api/garage/light/state'),
  lightSet: (state: 'on' | 'off') => jsonFetch<unknown>(`/api/garage/light/${state}`, { method: 'POST' }),
  lightToggle: () => jsonFetch<unknown>('/api/garage/light/toggle', { method: 'POST' }),

  // Devices
  getDevices: () => jsonFetch<DevicesResponse>('/api/devices'),
  rebootDevice: (deviceId: string) => jsonFetch<unknown>(`/api/devices/${encodeURIComponent(deviceId)}/reboot`, { method: 'POST' }),
  /**
   * Trigger OTA update for a device. If ref is omitted, the server uses its default (e.g., main).
   *
   * Args:
   *   deviceId (string): The device_id to update.
   *   ref (string | undefined): Optional git ref (branch or commit SHA).
   *
   * Returns:
   *   Promise<unknown>: Server response with publish status.
   */
  triggerUpdate: (deviceId: string, ref?: string) =>
    jsonFetch<unknown>(`/api/devices/${encodeURIComponent(deviceId)}/update`, {
      method: 'POST',
      body: JSON.stringify({ ref }),
    }),

  // Alerts
  getCurrentAlerts: () => jsonFetch<AlertItem[]>('/api/alerts/current'),
};
