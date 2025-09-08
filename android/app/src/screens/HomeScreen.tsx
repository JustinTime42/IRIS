import React from 'react';
import { ScrollView, View, Pressable } from 'react-native';
import { useTheme, Card, Text } from 'react-native-paper';
import { useDoorState, useDoorCommand, useGarageWeather, useGarageFreezer, useLightToggle, useLightState, useDevices } from '../hooks/useGarage';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import GarageDoorGlyph from '../shared/GarageDoorGlyph';
import AppButton from '../components/AppButton';
import JarvisActionTile from '../components/JarvisActionTile';

const Tile: React.FC<{ title: string; subtitle?: string; actions?: React.ReactElement[]; status?: React.ReactNode }> = ({ title, subtitle, actions, status }) => {
  const theme = useTheme();
  return (
    <Card style={{ margin: 8, backgroundColor: theme.colors.surface }}>
      <Card.Title
        title={title}
        subtitle={subtitle}
        right={() => status ? (
          <View style={{ marginRight: 8 }}>
            {typeof status === 'string' ? <Text>{status}</Text> : status}
          </View>
        ) : null}
      />
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
  const { data: light, isLoading: lightLoading } = useLightState();
  const { data: devices } = useDevices();

  // Helpers
  const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
  const fmt = (v: unknown, digits = 1) => (isNum(v) ? (v as number).toFixed(digits) : '—');

  const doorPending = doorCmd.isPending || doorLoading || (door?.state === 'opening') || (door?.state === 'closing');
  const lightPending = toggleLight.isPending || lightLoading;

  return (
    <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }} contentContainerStyle={{ padding: 8 }}>
      {/* Alert Row placeholder */}
      {/* Header text removed per Jarvish theme polish */}

      {/* Compact Controls Row: Garage Door + Flood Light (Jarvis angular tiles) */}
      <View style={{ flexDirection: 'row' }}>
        {/* Garage Door Card (reverted to previous animated icon + Card) */}
        <Pressable
          style={({ pressed }) => ({ flex: 1, margin: 8, transform: [{ scale: pressed ? 0.98 : 1 }] })}
          onPress={() => { if (!doorCmd.isPending && !doorLoading) doorCmd.mutate('toggle'); }}
          disabled={doorCmd.isPending || doorLoading}
        >
          <Card
            style={{
              flex: 1,
              backgroundColor: theme.colors.surface,
              borderRadius: 12,
              borderWidth: 1,
              borderColor: theme.colors.outlineVariant ?? '#4a4a4a',
              elevation: 4,
              shadowColor: '#000',
              shadowOpacity: 0.25,
              shadowRadius: 6,
              shadowOffset: { width: 0, height: 3 },
              overflow: 'hidden',
              opacity: (doorCmd.isPending || doorLoading) ? 0.7 : 1,
            }}
          >
            <Card.Content>
              <View style={{ alignItems: 'center', paddingVertical: 6 }}>
                <GarageDoorGlyph state={door?.state as any} size={28} />
                <Text style={{ marginTop: 8, opacity: 0.8 }}>Garage Door</Text>
              </View>
            </Card.Content>
          </Card>
        </Pressable>

        {/* Flood Light Tile */}
        <View style={{ flex: 1 }}>
          <JarvisActionTile
            title="Flood Light"
            subtitle={lightLoading ? 'Loading…' : undefined}
            status={lightPending ? 'pending' : 'idle'}
            onPress={() => { if (!toggleLight.isPending && !lightLoading) toggleLight.mutate(); }}
            disabled={toggleLight.isPending || lightLoading}
            renderIcon={() => (
              <MaterialCommunityIcons
                name={light?.state === 'on' ? 'lightbulb-on' : 'lightbulb-outline'}
                size={26}
                color={light?.state === 'on' ? '#FFD54F' : theme.colors.onSurfaceDisabled}
              />
            )}
          />
        </View>
      </View>

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
        actions={[<AppButton label="Thresholds" compact />]}
      />

      {/* House Freezer */}
      <Tile title="House Freezer" subtitle="-- °F | Door: closed" actions={[<AppButton label="Thresholds" compact />]} />

      {/* SOS */}
      <Tile title="SOS" subtitle="Active: 0" actions={[<AppButton label="Acknowledge" compact />]} />

      {/* Devices */}
      <Tile
        title="Devices"
        subtitle={devices ? `Total: ${Object.keys(devices).length}` : 'Total: —'}
      />

      {/* Updates */}
      <Tile title="Updates" subtitle="Last: --" actions={[<AppButton label="Trigger OTA" compact />]} />
    </ScrollView>
  );
}
