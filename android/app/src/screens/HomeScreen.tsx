import React from 'react';
import { ScrollView, View } from 'react-native';
import { useTheme, Text, Card, Button, Chip, ActivityIndicator } from 'react-native-paper';
import { useDoorState, useDoorCommand, useGarageWeather, useGarageFreezer, useLightSet, useLightToggle, useDevices } from '../hooks/useGarage';

const Tile: React.FC<{ title: string; subtitle?: string; actions?: React.ReactElement[]; status?: string }> = ({ title, subtitle, actions, status }) => {
  const theme = useTheme();
  return (
    <Card style={{ margin: 8, backgroundColor: theme.colors.surface }}>
      <Card.Title title={title} subtitle={subtitle} right={() => status ? <Chip style={{ marginRight: 8 }}>{status}</Chip> : null} />
      {actions ? <Card.Actions>{actions.map((el, idx) => React.cloneElement(el, { key: el.key ?? idx }))}</Card.Actions> : null}
    </Card>
  );
};

export default function HomeScreen() {
  const theme = useTheme();
  const { data: door, isLoading: doorLoading } = useDoorState();
  const doorCmd = useDoorCommand();
  const { data: weather, isLoading: weatherLoading } = useGarageWeather();
  const { data: freezer, isLoading: freezerLoading } = useGarageFreezer();
  const toggleLight = useLightToggle();
  const setLight = useLightSet();
  const { data: devices } = useDevices();

  // Helpers
  const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
  const fmt = (v: unknown, digits = 1) => (isNum(v) ? (v as number).toFixed(digits) : '—');

  return (
    <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }} contentContainerStyle={{ padding: 8 }}>
      {/* Alert Row placeholder */}
      <View style={{ margin: 8 }}>
        <Text variant="titleMedium">Command Center</Text>
      </View>

      {/* Garage Door */}
      <Tile
        title="Garage Door"
        status={doorLoading ? '...' : door?.state}
        actions={[
          <Button mode="contained" onPress={() => doorCmd.mutate('open')} loading={doorCmd.isPending} disabled={doorCmd.isPending}>Open</Button>,
          <Button onPress={() => doorCmd.mutate('close')} disabled={doorCmd.isPending}>Close</Button>,
          <Button mode="outlined" onPress={() => doorCmd.mutate('toggle')} disabled={doorCmd.isPending}>Toggle</Button>,
        ]}
      />

      {/* Flood Light */}
      <Tile
        title="Flood Light"
        status={toggleLight.isPending || setLight.isPending ? '...' : undefined}
        actions={[
          <Button mode="contained" onPress={() => setLight.mutate('on')} loading={setLight.isPending} disabled={setLight.isPending}>On</Button>,
          <Button mode="outlined" onPress={() => toggleLight.mutate()} disabled={toggleLight.isPending}>Toggle</Button>,
          <Button onPress={() => setLight.mutate('off')} disabled={setLight.isPending}>Off</Button>,
        ]}
      />

      {/* Weather */}
      <Tile
        title="Weather"
        subtitle={
          weatherLoading || !weather
            ? '—'
            : `${fmt((weather as any).temperature_f, 1)} °F | ${fmt((weather as any).pressure_inhg, 2)} inHg`
        }
      />

      {/* Freezer (Garage) */}
      <Tile
        title="Freezer (Garage)"
        subtitle={freezerLoading || !freezer ? '—' : `${fmt((freezer as any).temperature_f, 1)} °F`}
        actions={[<Button>Thresholds</Button>]}
      />

      {/* House Freezer */}
      <Tile title="House Freezer" subtitle="-- °F | Door: closed" actions={[<Button>Thresholds</Button>]} />

      {/* SOS */}
      <Tile title="SOS" subtitle="Active: 0" actions={[<Button>Acknowledge</Button>]} />

      {/* Devices */}
      <Tile
        title="Devices"
        subtitle={devices ? `Total: ${Object.keys(devices).length}` : 'Total: —'}
      />

      {/* Updates */}
      <Tile title="Updates" subtitle="Last: --" actions={[<Button mode="contained">Trigger OTA</Button>]} />
    </ScrollView>
  );
}
