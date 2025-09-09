// Shared API types aligned with server/api/main.py

export type DoorState = 'open' | 'closed' | 'opening' | 'closing' | 'error';

export interface LightState {
  /** Current light state */
  state: 'on' | 'off';
  /** ISO datetime string when last updated (if available) */
  last_updated?: string;
}

export interface WeatherState {
  /** Temperature in Fahrenheit */
  temperature_f: number;
  /** Pressure in inches of mercury */
  pressure_inhg: number;
}

export interface FreezerState {
  /** Temperature in Fahrenheit */
  temperature_f: number;
}

export type DeviceStatus = 'online' | 'offline' | 'needs_help' | 'updating' | 'error';

export interface DeviceInfo {
  device_id: string;
  status: DeviceStatus;
  last_seen?: string; // ISO datetime
  version?: string;
  last_error?: string;
  last_boot?: string; // ISO datetime
  ip_address?: string;
  rssi?: number;
  last_error_code?: string;
}

export type DevicesResponse = Record<string, DeviceInfo>;

export interface AlertItem {
  device_id: string;
  code: string;
  message?: string;
  last_seen: string; // ISO datetime
}

export interface WeatherHistoryPoint {
  /** ISO timestamp for the bucket */
  ts: string;
  /** Average temperature in Fahrenheit for the bucket */
  temperature_f?: number | null;
  /** Average pressure in inHg for the bucket */
  pressure_inhg?: number | null;
}
