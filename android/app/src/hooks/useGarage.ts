import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { WeatherState, FreezerState, DoorState, DevicesResponse, LightState, AlertItem, WeatherHistoryPoint } from '../types/api';

/**
 * Weather
 */
export function useGarageWeather() {
  return useQuery<WeatherState>({
    queryKey: ['garage', 'weather'],
    queryFn: api.getGarageWeather,
    refetchInterval: 10_000,
  });
}

export function useWeatherHistory(opts?: { range?: string; bucket?: 'minute' | 'hour' | 'day'; start?: string; end?: string }) {
  const key = ['garage', 'weather', 'history', opts?.range ?? opts?.start ?? '24h', opts?.bucket ?? 'hour'] as const;
  return useQuery<WeatherHistoryPoint[]>({
    queryKey: key,
    queryFn: () => api.getWeatherHistory(opts),
    // Hourly history can refresh less frequently
    refetchInterval: 60_000,
  });
}

/**
 * Freezer
 */
export function useGarageFreezer() {
  return useQuery<FreezerState>({
    queryKey: ['garage', 'freezer'],
    queryFn: api.getGarageFreezer,
    refetchInterval: 10_000,
  });
}

/**
 * Door State + Commands
 */
export function useDoorState() {
  return useQuery<{ state: DoorState }>({
    queryKey: ['garage', 'door', 'state'],
    queryFn: api.getDoorState,
    refetchInterval: 3_000,
  });
}

export function useDoorCommand() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (command: 'open' | 'close' | 'toggle') => api.doorCommand(command),
    onSuccess: () => {
      // Refresh door state after command
      qc.invalidateQueries({ queryKey: ['garage', 'door', 'state'] });
    },
  });
}

/**
 * Light Commands
 */
export function useLightState() {
  return useQuery<LightState>({
    queryKey: ['garage', 'light', 'state'],
    queryFn: api.getLightState,
    refetchInterval: 5_000,
  });
}

export function useLightToggle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: api.lightToggle,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['garage', 'light', 'state'] }),
  });
}

export function useLightSet() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (state: 'on' | 'off') => api.lightSet(state),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['garage', 'light', 'state'] }),
  });
}

/**
 * Devices
 */
export function useDevices() {
  return useQuery<DevicesResponse>({
    queryKey: ['devices'],
    queryFn: api.getDevices,
    refetchInterval: 15_000,
  });
}

export function useRebootDevice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (deviceId: string) => api.rebootDevice(deviceId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['devices'] }),
  });
}

/**
 * Alerts (structured SOS)
 */
export function useAlerts() {
  return useQuery<AlertItem[]>({
    queryKey: ['alerts', 'current'],
    queryFn: api.getCurrentAlerts,
    refetchInterval: 5_000,
  });
}
