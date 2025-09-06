// Theme token definitions for the IRIS app
// Reason: Provide an app-level theme model allowing radically different looks (Retro, Jarvis)

export type AppThemeKey = 'system' | 'dark' | 'light' | 'retro-green' | 'retro-amber' | 'jarvis';

export type ColorPalette = {
  background: string;
  surface: string;
  surfaceVariant?: string;
  primary: string;
  secondary?: string;
  tertiary?: string;
  outline?: string;
  error?: string;
  onBackground: string;
  onSurface: string;
  onPrimary?: string;
  onSecondary?: string;
};

export type Typography = {
  headingFamily: string;
  bodyFamily: string;
};

export type Spacing = {
  xs: number;
  sm: number;
  md: number;
  lg: number;
  xl: number;
};

export type Effects = {
  // Retro
  scanlines?: boolean;
  // Jarvis
  glass?: boolean;
  blurIntensity?: number; // 0-100
  glow?: boolean;
};

export type AppThemeTokens = {
  key: AppThemeKey;
  name: string;
  dark: boolean;
  colors: ColorPalette;
  typography: Typography;
  spacing: Spacing;
  radius: number;
  effects: Effects;
};

export const defaultSpacing: Spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 };
