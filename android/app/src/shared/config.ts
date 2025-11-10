import { Platform } from 'react-native';
import * as Device from 'expo-device';

/**
 * Returns the base URL for the FastAPI backend depending on runtime.
 * - Android emulator uses the special host 10.0.2.2 to reach the dev machine.
 * - Real devices (phone) use your LAN/VPN host/IP.
 * # Reason: Ensure both emulator and physical device work without juggling configs.
 */
export function getBaseUrl(): string {
  const isAndroid = Platform.OS === 'android';
  const isEmulator = isAndroid && !Device.isDevice;

  if (isEmulator) {
    // Android emulator → host loopback
    return 'http://10.0.2.2:8000';
  }

  // Phone (or non-Android platforms, if applicable) → LAN/VPN host
  return 'http://jarvis:8000';
}

const resolvedBaseUrl = getBaseUrl();
console.debug(`[config] Using baseUrl=${resolvedBaseUrl}`);

export const Config = {
  /** Base URL for the FastAPI backend (resolved at runtime). */
  baseUrl: resolvedBaseUrl,
};
