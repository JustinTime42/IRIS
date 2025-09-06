import { DefaultTheme as NavDefaultTheme, Theme as NavTheme } from '@react-navigation/native';
import { AppThemeTokens } from './tokens';

export function toNavigationTheme(t: AppThemeTokens): NavTheme {
  return {
    ...NavDefaultTheme,
    dark: t.dark,
    colors: {
      ...NavDefaultTheme.colors,
      primary: t.colors.primary,
      background: t.colors.background,
      card: t.colors.surface,
      text: t.colors.onSurface,
      border: t.colors.outline ?? NavDefaultTheme.colors.border,
      notification: t.colors.secondary ?? t.colors.primary,
    },
  };
}
