import React from 'react';
import { StatusBar } from 'expo-status-bar';
import { AppProviders } from './src/providers/AppProviders';
import RootNavigator from './src/navigation/RootNavigator';
import { useDeviceWebSocket } from './src/hooks/useDeviceWebSocket';

/**
 * Inner component that initializes WebSocket after providers are ready.
 */
function AppContent() {
  // Initialize WebSocket for real-time device updates
  useDeviceWebSocket();

  return (
    <>
      <StatusBar style="light" />
      <RootNavigator />
    </>
  );
}

export default function App() {
  return (
    <AppProviders>
      <AppContent />
    </AppProviders>
  );
}
