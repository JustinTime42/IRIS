import { Config } from '../shared/config';
import type { WeatherState, FreezerState, DoorState, DevicesResponse } from '../types/api';

/**
 * Simple JSON fetch helper.
 * # Reason: Centralize base URL and JSON handling for consistency and easier error tracing.
 */
async function jsonFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${Config.baseUrl}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  if (!res.ok) {
    const text = await res.text().catch(() => '');
    throw new Error(`HTTP ${res.status} ${res.statusText} for ${path}: ${text}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Garage Weather
  getGarageWeather: () => jsonFetch<WeatherState>('/api/garage/weather'),

  // Garage Freezer
  getGarageFreezer: () => jsonFetch<FreezerState>('/api/garage/freezer'),

  // Garage Door
  getDoorState: () => jsonFetch<{ state: DoorState }>('/api/garage/door/state'),
  doorCommand: (command: 'open' | 'close' | 'toggle') =>
    jsonFetch<unknown>(`/api/garage/door/${command}`, { method: 'POST' }),

  // Flood Light
  lightSet: (state: 'on' | 'off') => jsonFetch<unknown>(`/api/garage/light/${state}`, { method: 'POST' }),
  lightToggle: () => jsonFetch<unknown>('/api/garage/light/toggle', { method: 'POST' }),

  // Devices
  getDevices: () => jsonFetch<DevicesResponse>('/api/devices'),
  rebootDevice: (deviceId: string) => jsonFetch<unknown>(`/api/devices/${encodeURIComponent(deviceId)}/reboot`, { method: 'POST' }),
};
