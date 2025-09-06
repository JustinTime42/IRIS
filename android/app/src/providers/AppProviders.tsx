import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useFonts as useOrbitron, Orbitron_600SemiBold } from '@expo-google-fonts/orbitron';
import { useFonts as useInter, Inter_400Regular } from '@expo-google-fonts/inter';
import * as SplashScreen from 'expo-splash-screen';
import { ThemeProvider } from '../theme/ThemeProvider';

SplashScreen.preventAutoHideAsync().catch(() => {});

const queryClient = new QueryClient();

// Navigation and Paper theming are now handled inside ThemeProvider

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
      <ThemeProvider>
        {children}
      </ThemeProvider>
    </QueryClientProvider>
  );
};
