import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useTheme, Card, Text } from 'react-native-paper';
import HomeScreen from '../screens/HomeScreen';
import SettingsScreen from '../screens/SettingsScreen';
import DevicesScreen from '../screens/DevicesScreen';
import { View, ScrollView, Dimensions } from 'react-native';
import { useWeatherHistory } from '../hooks/useGarage';
import Svg, { Path, G, Line } from 'react-native-svg';
import { Ionicons } from '@expo/vector-icons';

const Tab = createBottomTabNavigator();

const Placeholder: React.FC<{ title: string }> = ({ title }) => {
  const theme = useTheme();
  return <View style={{ flex: 1, backgroundColor: theme.colors.background }} />;
};

const WeatherHistoryScreen: React.FC = () => {
  const theme = useTheme();
  const { data, isLoading } = useWeatherHistory({ range: '7d', bucket: 'hour' });

  const width = Dimensions.get('window').width - 32; // padding
  const height = 200;
  const pad = 24;

  const points = data ?? [];
  const xs = points.map(p => new Date(p.ts).getTime());
  const temps = points.map(p => (p.temperature_f ?? NaN));
  const presses = points.map(p => (p.pressure_inhg ?? NaN));

  const xMin = xs.length ? Math.min(...xs) : 0;
  const xMax = xs.length ? Math.max(...xs) : 1;
  const tMin = temps.filter(Number.isFinite).length ? Math.min(...temps.filter(Number.isFinite) as number[]) : 0;
  const tMax = temps.filter(Number.isFinite).length ? Math.max(...temps.filter(Number.isFinite) as number[]) : 1;
  const pMin = presses.filter(Number.isFinite).length ? Math.min(...presses.filter(Number.isFinite) as number[]) : 0;
  const pMax = presses.filter(Number.isFinite).length ? Math.max(...presses.filter(Number.isFinite) as number[]) : 1;

  const xScale = (x: number) => {
    if (xMax === xMin) return pad;
    return pad + ((x - xMin) / (xMax - xMin)) * (width - pad * 2);
  };
  const yScale = (v: number, vmin: number, vmax: number) => {
    if (vmax === vmin) return height - pad;
    const y = pad + (1 - (v - vmin) / (vmax - vmin)) * (height - pad * 2);
    return y;
  };

  const buildPath = (vals: (number | null)[], vmin: number, vmax: number) => {
    if (!xs.length) return '';
    let d = '';
    for (let i = 0; i < xs.length; i++) {
      const v = vals[i];
      if (!Number.isFinite(v as number)) continue;
      const x = xScale(xs[i]);
      const y = yScale(v as number, vmin, vmax);
      d += d ? ` L ${x} ${y}` : `M ${x} ${y}`;
    }
    return d;
  };

  const tempPath = buildPath(temps, Math.floor(tMin), Math.ceil(tMax));
  const pressPath = buildPath(presses, Math.floor(pMin), Math.ceil(pMax));

  return (
    <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }} contentContainerStyle={{ padding: 8 }}>
      <Card style={{ margin: 8, backgroundColor: theme.colors.surface }}>
        <Card.Title title="Weather History" subtitle={isLoading ? 'Loading…' : 'Last 7 days • hourly averages'} />
        <Card.Content>
          <Text style={{ marginBottom: 8 }}>Temperature (°F)</Text>
          <Svg width={width} height={height}>
            {/* X-axis */}
            <Line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke={theme.colors.outline} strokeWidth={1} />
            {/* Series */}
            <Path d={tempPath} stroke={theme.colors.primary} strokeWidth={2} fill="none" />
          </Svg>
        </Card.Content>
      </Card>

      <Card style={{ margin: 8, backgroundColor: theme.colors.surface }}>
        <Card.Title title="Pressure (inHg)" subtitle={isLoading ? 'Loading…' : 'Last 7 days • hourly averages'} />
        <Card.Content>
          <Svg width={width} height={height}>
            <Line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke={theme.colors.outline} strokeWidth={1} />
            <Path d={pressPath} stroke={theme.colors.secondary ?? theme.colors.primary} strokeWidth={2} fill="none" />
          </Svg>
        </Card.Content>
      </Card>
    </ScrollView>
  );
};

export default function RootNavigator() {
  const theme = useTheme();

  return (
    <Tab.Navigator
      screenOptions={({ route }) => ({
        headerShown: false,
        tabBarActiveTintColor: theme.colors.primary,
        tabBarInactiveTintColor: theme.colors.onSurface,
        tabBarStyle: { 
          backgroundColor: theme.colors.surface,
          borderTopColor: theme.colors.outline,
        },
        tabBarIcon: ({ focused, color, size }) => {
          let iconName: keyof typeof Ionicons.glyphMap;

          switch (route.name) {
            case 'Home':
              iconName = focused ? 'home' : 'home-outline';
              break;
            case 'Devices':
              iconName = focused ? 'hardware-chip' : 'hardware-chip-outline';
              break;
            case 'SOS':
              iconName = focused ? 'warning' : 'warning-outline';
              break;
            case 'Weather':
              iconName = focused ? 'partly-sunny' : 'partly-sunny-outline';
              break;
            case 'Settings':
              iconName = focused ? 'settings' : 'settings-outline';
              break;
            default:
              iconName = 'ellipse-outline';
          }

          return <Ionicons name={iconName} size={size} color={color} />;
        },
      })}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Devices" component={DevicesScreen} />
      <Tab.Screen name="SOS" children={() => <Placeholder title="SOS" />} />
      <Tab.Screen name="Weather" component={WeatherHistoryScreen} />
      <Tab.Screen name="Settings" component={SettingsScreen} />
    </Tab.Navigator>
  );
}
