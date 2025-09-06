import { AppThemeTokens, defaultSpacing } from './tokens';

export const RetroGreenTheme: AppThemeTokens = {
  key: 'retro-green',
  name: 'Retro (Green)',
  dark: true,
  colors: {
    background: '#001100',
    surface: '#001A00',
    surfaceVariant: '#002200',
    primary: '#00FF66',
    secondary: '#00CC44',
    outline: 'rgba(0,255,102,0.25)',
    error: '#FF4D4D',
    onBackground: '#6BFFB3',
    onSurface: '#6BFFB3',
    onPrimary: '#001100',
  },
  typography: {
    headingFamily: 'Orbitron_600SemiBold', // placeholder; will swap to pixel font later if desired
    bodyFamily: 'Inter_400Regular',
  },
  spacing: defaultSpacing,
  radius: 0,
  effects: {
    scanlines: true,
    glass: false,
    blurIntensity: 0,
    glow: false,
  },
};

export const RetroAmberTheme: AppThemeTokens = {
  key: 'retro-amber',
  name: 'Retro (Amber)',
  dark: true,
  colors: {
    background: '#110800',
    surface: '#190B00',
    surfaceVariant: '#1F0D00',
    primary: '#FFB000',
    secondary: '#FF9900',
    outline: 'rgba(255,176,0,0.25)',
    error: '#FF4D4D',
    onBackground: '#FFD699',
    onSurface: '#FFD699',
    onPrimary: '#190B00',
  },
  typography: {
    headingFamily: 'Orbitron_600SemiBold',
    bodyFamily: 'Inter_400Regular',
  },
  spacing: defaultSpacing,
  radius: 0,
  effects: {
    scanlines: true,
    glass: false,
    blurIntensity: 0,
    glow: false,
  },
};

export const JarvisTheme: AppThemeTokens = {
  key: 'jarvis',
  name: 'JARVIS',
  dark: true,
  colors: {
    background: '#0A0F1A',
    surface: '#0F1524',
    surfaceVariant: '#151B2C',
    primary: '#00E5FF',
    secondary: '#00FFC6',
    tertiary: '#7C4DFF',
    outline: 'rgba(255,255,255,0.08)',
    error: '#FF4D4D',
    onBackground: '#A9C1CC',
    onSurface: '#E6F7FF',
    onPrimary: '#00141A',
    onSecondary: '#001A16',
  },
  typography: {
    headingFamily: 'Orbitron_600SemiBold',
    bodyFamily: 'Inter_400Regular',
  },
  spacing: defaultSpacing,
  radius: 14,
  effects: {
    scanlines: false,
    glass: true,
    blurIntensity: 25,
    glow: true,
  },
};

export const ThemeRegistry = [RetroGreenTheme, RetroAmberTheme, JarvisTheme] as const;
export type ThemeRegistryKey = typeof ThemeRegistry[number]['key'];
