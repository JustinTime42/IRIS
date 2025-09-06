import React from 'react';
import { ScrollView, View } from 'react-native';
import { useTheme, Text, List, RadioButton, Divider, Card } from 'react-native-paper';
import { useAppTheme } from '../theme/ThemeProvider';
import { BlurView } from 'expo-blur';

/**
 * SettingsScreen
 *
 * Allows switching between app themes at runtime. Persists selection via ThemeProvider.
 */
export default function SettingsScreen() {
  const paperTheme = useTheme();
  const { themeKey, setThemeKey, tokens, allThemes } = useAppTheme();

  return (
    <ScrollView style={{ flex: 1, backgroundColor: paperTheme.colors.background }} contentContainerStyle={{ padding: 8 }}>
      <Text variant="titleLarge" style={{ margin: 8 }}>Appearance</Text>
      <List.Section>
        <RadioButton.Group onValueChange={(v) => setThemeKey(v as any)} value={themeKey}>
          <List.Item
            title="System (Auto)"
            description="Follow device light/dark, mapped to themed styles"
            left={(props) => <List.Icon {...props} icon="theme-light-dark" />}
            right={() => <RadioButton value="system" />}
            onPress={() => setThemeKey('system')}
          />
          <Divider />
          {allThemes.map((t) => (
            <List.Item
              key={t.key}
              title={t.name}
              description={t.key}
              left={(props) => <List.Icon {...props} icon={t.key.includes('retro') ? 'monitor-shimmer' : 'blur'} />}
              right={() => <RadioButton value={t.key} />}
              onPress={() => setThemeKey(t.key)}
            />
          ))}
        </RadioButton.Group>
      </List.Section>

      {/* Simple preview card with optional blur/glow hint */}
      <Card style={{ margin: 8, overflow: 'hidden', backgroundColor: tokens.colors.surface }}>
        {tokens.effects.glass ? (
          <BlurView intensity={tokens.effects.blurIntensity ?? 20} tint={tokens.dark ? 'dark' : 'light'} style={{ ...StyleSheet.absoluteFillObject }} />
        ) : null}
        <Card.Title title="Preview" subtitle={tokens.name} />
        <Card.Content>
          <Text style={{ opacity: 0.8 }}>Primary: {tokens.colors.primary}</Text>
          <Text style={{ opacity: 0.8 }}>Surface: {tokens.colors.surface}</Text>
          <Text style={{ opacity: 0.8 }}>Background: {tokens.colors.background}</Text>
        </Card.Content>
      </Card>
    </ScrollView>
  );
}

import { StyleSheet } from 'react-native';
