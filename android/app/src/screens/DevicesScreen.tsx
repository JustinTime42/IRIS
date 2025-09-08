import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { View, FlatList, RefreshControl } from 'react-native';
import { ActivityIndicator, Card, Divider, IconButton, Snackbar, Text, useTheme } from 'react-native-paper';
import AppButton from '../components/AppButton';
import { api } from '../services/api';
import type { DeviceInfo, DevicesResponse } from '../types/api';

interface DeviceRowProps {
  device: DeviceInfo;
  onTrigger: (deviceId: string) => Promise<void>;
  isBusy: boolean;
}

const DeviceRow: React.FC<DeviceRowProps> = ({ device, onTrigger, isBusy }) => {
  return (
    <Card style={{ marginVertical: 8 }}>
      <Card.Title title={device.device_id} subtitle={`Health: ${device.status}`} right={(props) => (
        <IconButton {...props} icon="information-outline" disabled />
      )} />
      <Card.Content>
        {device.version ? <Text>Version: {device.version}</Text> : null}
        {device.last_seen ? <Text>Last Seen: {device.last_seen}</Text> : null}
        {device.last_error ? <Text>Last Error: {device.last_error}</Text> : null}
      </Card.Content>
      <Card.Actions>
        <AppButton
          label="Trigger OTA"
          onPress={() => onTrigger(device.device_id)}
          status={isBusy ? 'pending' : 'idle'}
          disabled={isBusy}
        />
      </Card.Actions>
    </Card>
  );
};

const DevicesScreen: React.FC = () => {
  const theme = useTheme();
  const [devicesMap, setDevicesMap] = useState<DevicesResponse>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [snack, setSnack] = useState<{ visible: boolean; text: string }>({ visible: false, text: '' });

  const devices = useMemo(() => Object.values(devicesMap).sort((a, b) => a.device_id.localeCompare(b.device_id)), [devicesMap]);

  const load = useCallback(async () => {
    try {
      const data = await api.getDevices();
      setDevicesMap(data);
    } catch (e: any) {
      setSnack({ visible: true, text: e?.message || 'Failed to load devices' });
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    load();
  }, [load]);

  const onTrigger = useCallback(async (deviceId: string) => {
    try {
      setBusyId(deviceId);
      await api.triggerUpdate(deviceId);
      setSnack({ visible: true, text: `OTA triggered for ${deviceId}` });
    } catch (e: any) {
      setSnack({ visible: true, text: e?.message || `Failed to trigger OTA for ${deviceId}` });
    } finally {
      setBusyId(null);
    }
  }, []);

  if (loading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: theme.colors.background }}>
        <ActivityIndicator />
        <Text style={{ marginTop: 8 }}>Loading devices…</Text>
      </View>
    );
  }

  return (
    <View style={{ flex: 1, padding: 12, backgroundColor: theme.colors.background }}>
      <FlatList
        data={devices}
        keyExtractor={(item) => item.device_id}
        ItemSeparatorComponent={() => <Divider />}
        renderItem={({ item }) => (
          <DeviceRow device={item} onTrigger={onTrigger} isBusy={busyId === item.device_id} />
        )}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
        ListEmptyComponent={<Text>No devices found.</Text>}
      />
      <Snackbar visible={snack.visible} onDismiss={() => setSnack({ visible: false, text: '' })} duration={3000}>
        {snack.text}
      </Snackbar>
    </View>
  );
};

export default DevicesScreen;
