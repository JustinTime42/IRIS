import React from 'react';
import { ScrollView, View } from 'react-native';
import { useTheme, Card, Text } from 'react-native-paper';
import { useDoorState, useDoorCommand, useGarageWeather, useGarageFreezer, useLightToggle, useLightState, useDevices, useAlerts } from '../hooks/useGarage';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import GarageDoorGlyph from '../shared/GarageDoorGlyph';
import AppButton from '../components/AppButton';
import JarvisActionTile from '../components/JarvisActionTile';
import { useNavigation } from '@react-navigation/native';

const Tile: React.FC<{ title: string; subtitle?: string; actions?: React.ReactElement[]; status?: React.ReactNode; onPress?: () => void }> = ({ title, subtitle, actions, status, onPress }) => {
  const theme = useTheme();
  return (
    <Card style={{ margin: 8, backgroundColor: theme.colors.surface }} onPress={onPress}>
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
  const nav = useNavigation<any>();
  const { data: door, isLoading: doorLoading } = useDoorState();
  const doorCmd = useDoorCommand();
  const { data: weather, isLoading: weatherLoading } = useGarageWeather();
  const { data: freezer, isLoading: freezerLoading } = useGarageFreezer();
  const toggleLight = useLightToggle();
  const { data: light, isLoading: lightLoading } = useLightState();
  const { data: devices } = useDevices();
  const { data: alerts } = useAlerts();

  // Helpers
  const isNum = (v: unknown): v is number => typeof v === 'number' && Number.isFinite(v);
  const fmt = (v: unknown, digits = 1) => (isNum(v) ? (v as number).toFixed(digits) : '—');

  const doorPending = doorCmd.isPending || doorLoading || (door?.state === 'opening') || (door?.state === 'closing');
  const lightPending = toggleLight.isPending || lightLoading;

  // Structured SOS items from server (already deduped per device/code)
  const sosItems = alerts || [];

  return (
    <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }} contentContainerStyle={{ padding: 8 }}>
      {/* Alert Row placeholder */}
      {/* Header text removed per Jarvish theme polish */}

      {/* Compact Controls Row: Garage Door + Flood Light (Jarvis angular tiles) */}
      <View style={{ flexDirection: 'row' }}>
        {/* Garage Door Tile (use JarvisActionTile to match Flood Light styling) */}
        <View style={{ flex: 1 }}>
          <JarvisActionTile
            title="Garage Door"
            subtitle={doorLoading ? 'Loading…' : undefined}
            status={'idle'}
            onPress={() => { if (!doorCmd.isPending && !doorLoading) doorCmd.mutate('toggle'); }}
            disabled={doorCmd.isPending || doorLoading}
            renderIcon={() => (
              <GarageDoorGlyph state={door?.state as any} size={28} />
            )}
          />
        </View>

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
        onPress={() => nav.navigate('Weather')}
      />

      {/* Freezer (Garage) and House Freezer side-by-side */}
      <View style={{ flexDirection: 'row' }}>
        <View style={{ flex: 1 }}>
          <Tile
            title="Freezer (Garage)"
            subtitle={freezerLoading || !freezer ? '—' : `${fmt((freezer as any).temperature_f, 1)} °F`}
          />
        </View>
        <View style={{ flex: 1 }}>
          <Tile
            title="House Freezer"
            subtitle="-- °F | Door: closed"
          />
        </View>
      </View>

      {/* SOS (only visible when there is a problem) */}
      {sosItems.length > 0 ? (
        <Card style={{ margin: 8, backgroundColor: theme.colors.surface }}>
          <Card.Title title="SOS" subtitle={`Active: ${sosItems.length}`} />
          <Card.Content>
            {sosItems.map((it, idx) => (
              <View key={`${it.device_id}-${it.code}-${idx}`} style={{ paddingVertical: 4 }}>
                <Text>{`${it.device_id}: ${it.code}`}</Text>
                {it.message && it.message !== it.code ? (
                  <Text style={{ opacity: 0.7, fontSize: 12 }}>{it.message}</Text>
                ) : null}
              </View>
            ))}
          </Card.Content>
        </Card>
      ) : null}

      {/* Devices */}
      <Tile
        title="Devices"
        subtitle={devices ? `Total: ${Object.keys(devices).length}` : 'Total: —'}
      />
    </ScrollView>
  );
}
