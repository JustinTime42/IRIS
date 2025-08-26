// Shared API types aligned with server/api/main.py

export type DoorState = 'open' | 'closed' | 'opening' | 'closing' | 'error';

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
}

export type DevicesResponse = Record<string, DeviceInfo>;
