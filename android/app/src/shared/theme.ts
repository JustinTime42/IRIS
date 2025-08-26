// Theme tokens for React Native Paper (MD3) with JARVIS vibe
import { MD3DarkTheme as PaperDarkTheme, configureFonts, MD3Theme } from 'react-native-paper';

const orbitron = {
  fontFamily: 'Orbitron_600SemiBold',
  fontWeight: '600' as const,
};
const inter = {
  fontFamily: 'Inter_400Regular',
  fontWeight: '400' as const,
};

const fonts = configureFonts({
  config: {
    displayLarge: orbitron,
    displayMedium: orbitron,
    displaySmall: orbitron,
    headlineLarge: orbitron,
    headlineMedium: orbitron,
    headlineSmall: orbitron,
    titleLarge: orbitron,
    titleMedium: orbitron,
    titleSmall: orbitron,
    labelLarge: inter,
    labelMedium: inter,
    labelSmall: inter,
    bodyLarge: inter,
    bodyMedium: inter,
    bodySmall: inter,
  },
});

export const IRISDarkTheme: MD3Theme = {
  ...PaperDarkTheme,
  version: 3,
  isV3: true,
  fonts,
  colors: {
    ...PaperDarkTheme.colors,
    primary: '#00E5FF',
    secondary: '#7C4DFF',
    tertiary: '#00FF8E',
    error: '#FF4D4D',
    surface: '#0F1524',
    background: '#0A0F1A',
    surfaceVariant: '#151B2C',
    outline: 'rgba(255,255,255,0.08)',
    onPrimary: '#00141A',
    onSecondary: '#10091F',
    onSurface: '#E6F7FF',
    onBackground: '#A9C1CC',
  },
};
