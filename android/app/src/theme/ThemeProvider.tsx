import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { Appearance, ColorSchemeName } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { PaperProvider } from 'react-native-paper';
import { NavigationContainer } from '@react-navigation/native';
import { AppThemeTokens, AppThemeKey } from './tokens';
import { ThemeRegistry } from './themes';
import { toPaperTheme } from './paper';
import { toNavigationTheme } from './navigation';

const STORAGE_KEY = 'iris.theme.selection';

export type ThemeContextValue = {
  themeKey: AppThemeKey;
  setThemeKey: (k: AppThemeKey) => void;
  tokens: AppThemeTokens;
  allThemes: readonly AppThemeTokens[];
};

const ThemeContext = createContext<ThemeContextValue | undefined>(undefined);

function pickSystemTheme(scheme: ColorSchemeName): AppThemeTokens {
  // Default system mapping: use Jarvis for dark, Retro Amber for light (fun!)
  if (scheme === 'dark') return ThemeRegistry.find(t => t.key === 'jarvis')!;
  return ThemeRegistry.find(t => t.key === 'retro-amber')!;
}

export const ThemeProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [themeKey, setThemeKey] = useState<AppThemeKey>('system');
  const [systemScheme, setSystemScheme] = useState<ColorSchemeName>(Appearance.getColorScheme());

  useEffect(() => {
    const sub = Appearance.addChangeListener(({ colorScheme }) => setSystemScheme(colorScheme));
    return () => sub.remove();
  }, []);

  // Load persisted selection
  useEffect(() => {
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(STORAGE_KEY);
        if (saved) setThemeKey(saved as AppThemeKey);
      } catch {}
    })();
  }, []);

  // Persist selection
  useEffect(() => {
    AsyncStorage.setItem(STORAGE_KEY, themeKey).catch(() => {});
  }, [themeKey]);

  const tokens = useMemo<AppThemeTokens>(() => {
    if (themeKey === 'system') return pickSystemTheme(systemScheme);
    const found = ThemeRegistry.find(t => t.key === themeKey);
    return found ?? ThemeRegistry[0];
  }, [themeKey, systemScheme]);

  const paperTheme = useMemo(() => toPaperTheme(tokens), [tokens]);
  const navTheme = useMemo(() => toNavigationTheme(tokens), [tokens]);

  const value: ThemeContextValue = useMemo(() => ({ themeKey, setThemeKey, tokens, allThemes: ThemeRegistry }), [themeKey, tokens]);

  return (
    <ThemeContext.Provider value={value}>
      <PaperProvider theme={paperTheme}>
        <NavigationContainer theme={navTheme}>{children}</NavigationContainer>
      </PaperProvider>
    </ThemeContext.Provider>
  );
};

export function useAppTheme(): ThemeContextValue {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error('useAppTheme must be used within ThemeProvider');
  return ctx;
}
