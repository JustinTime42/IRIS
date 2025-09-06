import { MD3DarkTheme, configureFonts, MD3Theme } from 'react-native-paper';
import { AppThemeTokens } from './tokens';

export function toPaperTheme(t: AppThemeTokens): MD3Theme {
  const fonts = configureFonts({
    config: {
      displayLarge: { fontFamily: t.typography.headingFamily, fontWeight: '600' },
      displayMedium: { fontFamily: t.typography.headingFamily, fontWeight: '600' },
      displaySmall: { fontFamily: t.typography.headingFamily, fontWeight: '600' },
      headlineLarge: { fontFamily: t.typography.headingFamily, fontWeight: '600' },
      headlineMedium: { fontFamily: t.typography.headingFamily, fontWeight: '600' },
      headlineSmall: { fontFamily: t.typography.headingFamily, fontWeight: '600' },
      titleLarge: { fontFamily: t.typography.headingFamily, fontWeight: '600' },
      titleMedium: { fontFamily: t.typography.headingFamily, fontWeight: '600' },
      titleSmall: { fontFamily: t.typography.headingFamily, fontWeight: '600' },
      labelLarge: { fontFamily: t.typography.bodyFamily, fontWeight: '400' },
      labelMedium: { fontFamily: t.typography.bodyFamily, fontWeight: '400' },
      labelSmall: { fontFamily: t.typography.bodyFamily, fontWeight: '400' },
      bodyLarge: { fontFamily: t.typography.bodyFamily, fontWeight: '400' },
      bodyMedium: { fontFamily: t.typography.bodyFamily, fontWeight: '400' },
      bodySmall: { fontFamily: t.typography.bodyFamily, fontWeight: '400' },
    },
  });

  return {
    ...MD3DarkTheme,
    isV3: true,
    dark: t.dark,
    fonts,
    colors: {
      ...MD3DarkTheme.colors,
      primary: t.colors.primary,
      secondary: t.colors.secondary ?? MD3DarkTheme.colors.secondary,
      tertiary: t.colors.tertiary ?? MD3DarkTheme.colors.tertiary,
      error: t.colors.error ?? MD3DarkTheme.colors.error,
      surface: t.colors.surface,
      background: t.colors.background,
      surfaceVariant: t.colors.surfaceVariant ?? MD3DarkTheme.colors.surfaceVariant,
      outline: t.colors.outline ?? MD3DarkTheme.colors.outline,
      onPrimary: t.colors.onPrimary ?? MD3DarkTheme.colors.onPrimary,
      onSecondary: t.colors.onSecondary ?? MD3DarkTheme.colors.onSecondary,
      onSurface: t.colors.onSurface,
      onBackground: t.colors.onBackground,
    },
  };
}
