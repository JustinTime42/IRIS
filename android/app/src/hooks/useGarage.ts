import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import type { WeatherState, FreezerState, DoorState, DevicesResponse } from '../types/api';

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
export function useLightToggle() {
  return useMutation({ mutationFn: api.lightToggle });
}

export function useLightSet() {
  return useMutation({ mutationFn: (state: 'on' | 'off') => api.lightSet(state) });
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
