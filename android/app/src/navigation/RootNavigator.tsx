import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useTheme, Card, Text } from 'react-native-paper';
import HomeScreen from '../screens/HomeScreen';
import SettingsScreen from '../screens/SettingsScreen';
import DevicesScreen from '../screens/DevicesScreen';
import { View, ScrollView, Dimensions } from 'react-native';
import { useWeatherHistory, useGarageWeather } from '../hooks/useGarage';
import Svg, { Path, G, Line, Text as SvgText } from 'react-native-svg';
import { Ionicons } from '@expo/vector-icons';

const Tab = createBottomTabNavigator();

const Placeholder: React.FC<{ title: string }> = ({ title }) => {
  const theme = useTheme();
  return <View style={{ flex: 1, backgroundColor: theme.colors.background }} />;
};

const WeatherHistoryScreen: React.FC = () => {
  const theme = useTheme();
  const { data: currentWeather, isLoading: isCurrentLoading } = useGarageWeather();
  const { data, isLoading } = useWeatherHistory({ range: '7d', bucket: 'hour' });

  const width = Dimensions.get('window').width - 32; // padding
  const height = 200;
  const pad = 35; // Balanced padding - tight but with proper label spacing

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

  // Helper functions for generating scale labels
  const generateYTicks = (min: number, max: number, count: number = 5) => {
    if (min === max) return [min];
    const range = max - min;
    const step = range / (count - 1);
    return Array.from({ length: count }, (_, i) => min + step * i);
  };

  const generateXTicks = (minTime: number, maxTime: number, count: number = 4) => {
    if (minTime === maxTime) return [minTime];
    const range = maxTime - minTime;
    const step = range / (count - 1);
    return Array.from({ length: count }, (_, i) => minTime + step * i);
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const daysDiff = Math.floor((now.getTime() - timestamp) / (1000 * 60 * 60 * 24));
    
    if (daysDiff === 0) return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (daysDiff < 7) return date.toLocaleDateString([], { weekday: 'short' });
    return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  const tempPath = buildPath(temps, Math.floor(tMin), Math.ceil(tMax));
  const pressPath = buildPath(presses, Math.floor(pMin), Math.ceil(pMax));

  // Generate tick marks and labels
  const tempYTicks = generateYTicks(Math.floor(tMin), Math.ceil(tMax));
  const pressYTicks = generateYTicks(Math.floor(pMin), Math.ceil(pMax));
  const xTicks = xs.length > 0 ? generateXTicks(xMin, xMax) : [];

  return (
    <ScrollView style={{ flex: 1, backgroundColor: theme.colors.background }} contentContainerStyle={{ padding: 8 }}>
      {/* Current Weather Card */}
      <Card style={{ margin: 8, backgroundColor: theme.colors.surface }}>

        <Card.Content>
          <View style={{ 
            flexDirection: 'row', 
            justifyContent: 'space-around',
            alignItems: 'center',
            paddingVertical: 16
          }}>
            {/* Temperature Display */}
            <View style={{ alignItems: 'center', flex: 1 }}>
              <Ionicons 
                name="thermometer-outline" 
                size={24} 
                color={theme.colors.primary} 
                style={{ marginBottom: 8 }}
              />
              <Text variant="headlineLarge" style={{ 
                color: theme.colors.primary,
                fontWeight: 'bold',
                marginBottom: 4
              }}>
                {isCurrentLoading ? '--' : currentWeather?.temperature_f?.toFixed(1) ?? '--'}°F
              </Text>
              <Text variant="bodyMedium" style={{ 
                color: theme.colors.onSurface,
                opacity: 0.7
              }}>
                Temperature
              </Text>
            </View>

            {/* Divider */}
            <View style={{
              width: 1,
              height: 60,
              backgroundColor: theme.colors.outline,
              opacity: 0.5
            }} />

            {/* Pressure Display */}
            <View style={{ alignItems: 'center', flex: 1 }}>
              <Ionicons 
                name="speedometer-outline" 
                size={24} 
                color={theme.colors.secondary ?? theme.colors.primary} 
                style={{ marginBottom: 8 }}
              />
              <Text variant="headlineLarge" style={{ 
                color: theme.colors.secondary ?? theme.colors.primary,
                fontWeight: 'bold',
                marginBottom: 4
              }}>
                {isCurrentLoading ? '--' : currentWeather?.pressure_inhg?.toFixed(2) ?? '--'}
              </Text>
              <Text variant="bodyMedium" style={{ 
                color: theme.colors.onSurface,
                opacity: 0.7
              }}>
                Pressure (inHg)
              </Text>
            </View>
          </View>
        </Card.Content>
      </Card>

      {/* Historical Weather Card */}
      <Card style={{ margin: 8, backgroundColor: theme.colors.surface }}>
        <Card.Title title="Weather History" subtitle={isLoading ? 'Loading…' : 'Last 7 days • hourly averages'} />
        <Card.Content>
          {/* Temperature Section */}
          <Text variant="titleMedium" style={{
            marginTop: 4,
            marginBottom: 0,
            color: theme.colors.onSurface,
            fontWeight: '600' 
          }}>
            Temperature (°F)
          </Text>
          <Svg width={width} height={height}>
            {/* Y-axis */}
            <Line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke={theme.colors.outline} strokeWidth={1} />
            {/* X-axis */}
            <Line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke={theme.colors.outline} strokeWidth={1} />
            
            {/* Y-axis labels and tick marks */}
            {tempYTicks.map((tick, i) => {
              const y = yScale(tick, Math.floor(tMin), Math.ceil(tMax));
              return (
                <G key={`temp-y-${i}`}>
                  <Line x1={pad - 5} y1={y} x2={pad} y2={y} stroke={theme.colors.outline} strokeWidth={1} />
                  <SvgText x={pad - 8} y={y + 3} fontSize="10" fill={theme.colors.onSurface} textAnchor="end">
                    {tick.toFixed(0)}
                  </SvgText>
                </G>
              );
            })}

            {/* X-axis labels and tick marks */}
            {xTicks.map((tick, i) => {
              const x = xScale(tick);
              return (
                <G key={`temp-x-${i}`}>
                  <Line x1={x} y1={height - pad} x2={x} y2={height - pad + 5} stroke={theme.colors.outline} strokeWidth={1} />
                  <SvgText x={x} y={height - pad + 15} fontSize="10" fill={theme.colors.onSurface} textAnchor="middle">
                    {formatTime(tick)}
                  </SvgText>
                </G>
              );
            })}

            {/* Data series */}
            <Path d={tempPath} stroke={theme.colors.primary} strokeWidth={2} fill="none" />
          </Svg>

          {/* Pressure Section */}
          <Text variant="titleMedium" style={{
            marginTop: 12,
            marginBottom: 0,
            color: theme.colors.onSurface,
            fontWeight: '600' 
          }}>
            Pressure (inHg)
          </Text>
          <Svg width={width} height={height}>
            {/* Y-axis */}
            <Line x1={pad} y1={pad} x2={pad} y2={height - pad} stroke={theme.colors.outline} strokeWidth={1} />
            {/* X-axis */}
            <Line x1={pad} y1={height - pad} x2={width - pad} y2={height - pad} stroke={theme.colors.outline} strokeWidth={1} />
            
            {/* Y-axis labels and tick marks */}
            {pressYTicks.map((tick, i) => {
              const y = yScale(tick, Math.floor(pMin), Math.ceil(pMax));
              return (
                <G key={`press-y-${i}`}>
                  <Line x1={pad - 5} y1={y} x2={pad} y2={y} stroke={theme.colors.outline} strokeWidth={1} />
                  <SvgText x={pad - 8} y={y + 3} fontSize="10" fill={theme.colors.onSurface} textAnchor="end">
                    {tick.toFixed(1)}
                  </SvgText>
                </G>
              );
            })}

            {/* X-axis labels and tick marks */}
            {xTicks.map((tick, i) => {
              const x = xScale(tick);
              return (
                <G key={`press-x-${i}`}>
                  <Line x1={x} y1={height - pad} x2={x} y2={height - pad + 5} stroke={theme.colors.outline} strokeWidth={1} />
                  <SvgText x={x} y={height - pad + 15} fontSize="10" fill={theme.colors.onSurface} textAnchor="middle">
                    {formatTime(tick)}
                  </SvgText>
                </G>
              );
            })}

            {/* Data series */}
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
