import React from 'react';
import { NavigationContainer, DefaultTheme as NavDefaultTheme, Theme as NavTheme } from '@react-navigation/native';
import { PaperProvider } from 'react-native-paper';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts as useOrbitron, Orbitron_600SemiBold } from '@expo-google-fonts/orbitron';
import { useFonts as useInter, Inter_400Regular } from '@expo-google-fonts/inter';
import * as SplashScreen from 'expo-splash-screen';
import { IRISDarkTheme } from '../shared/theme';

SplashScreen.preventAutoHideAsync().catch(() => {});

const queryClient = new QueryClient();

const navTheme: NavTheme = {
  ...NavDefaultTheme,
  dark: true,
  colors: {
    ...NavDefaultTheme.colors,
    primary: IRISDarkTheme.colors.primary,
    background: IRISDarkTheme.colors.background,
    card: IRISDarkTheme.colors.surface,
    text: IRISDarkTheme.colors.onSurface,
    border: IRISDarkTheme.colors.outline,
    notification: IRISDarkTheme.colors.secondary,
  },
};

export const AppProviders: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [orbitronLoaded] = useOrbitron({ Orbitron_600SemiBold });
  const [interLoaded] = useInter({ Inter_400Regular });

  const ready = orbitronLoaded && interLoaded;

  React.useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => {});
  }, [ready]);

  if (!ready) return null;

  return (
    <QueryClientProvider client={queryClient}>
      <PaperProvider theme={IRISDarkTheme}>
        <NavigationContainer theme={navTheme}>{children}</NavigationContainer>
      </PaperProvider>
    </QueryClientProvider>
  );
};
