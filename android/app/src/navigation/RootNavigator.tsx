import React from 'react';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import { useTheme } from 'react-native-paper';
import HomeScreen from '../screens/HomeScreen';
import { View } from 'react-native';

const Tab = createBottomTabNavigator();

const Placeholder: React.FC<{ title: string }> = ({ title }) => {
  const theme = useTheme();
  return <View style={{ flex: 1, backgroundColor: theme.colors.background }} />;
};

export default function RootNavigator() {
  const theme = useTheme();

  return (
    <Tab.Navigator
      screenOptions={{
        headerShown: false,
        tabBarActiveTintColor: theme.colors.primary,
        tabBarStyle: { backgroundColor: theme.colors.surface },
      }}
    >
      <Tab.Screen name="Home" component={HomeScreen} />
      <Tab.Screen name="Devices" children={() => <Placeholder title="Devices" />} />
      <Tab.Screen name="SOS" children={() => <Placeholder title="SOS" />} />
      <Tab.Screen name="History" children={() => <Placeholder title="History" />} />
      <Tab.Screen name="Settings" children={() => <Placeholder title="Settings" />} />
    </Tab.Navigator>
  );
}
