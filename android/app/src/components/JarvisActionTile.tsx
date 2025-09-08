import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Platform, Pressable, View, Animated, StyleSheet, LayoutChangeEvent } from 'react-native';
import { ActivityIndicator, Card, Text, useTheme } from 'react-native-paper';
import { useAppTheme } from '../theme/ThemeProvider';
import JarvisButtonVisual from './JarvisButtonVisual';

export type TileStatus = 'idle' | 'pending' | 'success' | 'error';

export interface JarvisActionTileProps {
  title: string;
  subtitle?: string;
  onPress?: () => void;
  disabled?: boolean;
  status?: TileStatus;
  height?: number; // default 110
  renderIcon?: () => React.ReactNode;
}

/**
 * JarvisActionTile
 *
 * Large action tile with the same angular Jarvis visual (glow + shade clipped to shape).
 * Falls back to Paper Card for non-Jarvis themes.
 */
const JarvisActionTile: React.FC<JarvisActionTileProps> = ({ title, subtitle, onPress, disabled, status = 'idle', height = 110, renderIcon }) => {
  const paperTheme = useTheme();
  const { tokens } = useAppTheme();
  const isJarvis = tokens.key === 'jarvis';
  const isRetro = tokens.key.startsWith('retro');

  const scale = useRef(new Animated.Value(1)).current;
  const glow = useRef(new Animated.Value(0)).current; // 0..1
  const shade = useRef(new Animated.Value(0)).current; // 0..1

  const [glowLevel, setGlowLevel] = useState(0);
  const [shadeLevel, setShadeLevel] = useState(0);
  useEffect(() => {
    const gId = glow.addListener(({ value }) => setGlowLevel(value));
    const sId = shade.addListener(({ value }) => setShadeLevel(value));
    return () => {
      glow.removeListener(gId);
      shade.removeListener(sId);
    };
  }, [glow, shade]);

  const [size, setSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });
  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height: h } = e.nativeEvent.layout;
    if (width !== size.w || h !== size.h) setSize({ w: width, h });
  };

  const containerBase = { height, margin: 8 } as const;

  const onPressIn = () => {
    Animated.parallel([
      Animated.spring(scale, { toValue: 0.985, useNativeDriver: true, speed: 60, bounciness: 6 }),
      Animated.timing(glow, { toValue: 1, duration: 160, useNativeDriver: false }),
      Animated.timing(shade, { toValue: 1, duration: 110, useNativeDriver: false }),
    ]).start();
  };
  const onPressOut = () => {
    Animated.parallel([
      Animated.spring(scale, { toValue: 1, useNativeDriver: true, speed: 60, bounciness: 6 }),
      Animated.timing(glow, { toValue: 0, duration: 240, useNativeDriver: false }),
      Animated.timing(shade, { toValue: 0, duration: 160, useNativeDriver: false }),
    ]).start();
  };

  // Non-Jarvis: return a Paper Card for consistency
  if (!isJarvis) {
    return (
      <Card style={[containerBase, { backgroundColor: paperTheme.colors.surface }]}> 
        <Pressable disabled={disabled} onPress={onPress} style={{ flex: 1 }}>
          <Card.Content style={{ flex: 1, alignItems: 'center', justifyContent: 'center' }}>
            {status === 'pending' ? (
              <ActivityIndicator />
            ) : renderIcon ? (
              <View style={{ marginBottom: 6 }}>{renderIcon()}</View>
            ) : null}
            <Text variant="titleSmall" style={{ color: paperTheme.colors.onSurface }}>{title}</Text>
            {subtitle ? <Text style={{ opacity: 0.7, marginTop: 2 }}>{subtitle}</Text> : null}
          </Card.Content>
        </Pressable>
      </Card>
    );
  }

  // Jarvis visual
  return (
    <Animated.View style={[containerBase, { transform: [{ scale }], alignSelf: 'stretch', flexGrow: 1 }]}> 
      <Pressable
        disabled={disabled || status === 'pending'}
        onPress={onPress}
        onPressIn={onPressIn}
        onPressOut={onPressOut}
        // No native ripple; custom shade is clipped to the shape
        android_ripple={Platform.OS === 'android' ? undefined : undefined}
        style={{ flex: 1 }}
      >
        <View style={{ flex: 1 }} onLayout={onLayout}>
          {size.w > 0 && size.h > 0 ? (
            <View style={{ position: 'absolute', inset: 0 }} pointerEvents="none">
              <JarvisButtonVisual
                width={size.w}
                height={size.h}
                glowIntensity={glowLevel}
                shade={shadeLevel}
                borderColor={'rgba(0,229,255,0.95)'}
                fillColor={'rgba(15,21,36,0.92)'}
              />
            </View>
          ) : null}

          {/* Content */}
          <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', paddingHorizontal: 8 }}>
            {status === 'pending' ? (
              <ActivityIndicator size={20} color={tokens.colors.primary} />
            ) : renderIcon ? (
              <View style={{ marginBottom: 6 }}>{renderIcon()}</View>
            ) : null}
            <Text style={{ color: tokens.colors.onSurface, fontFamily: tokens.typography.headingFamily, fontSize: 14 }}>{title}</Text>
            {subtitle ? <Text style={{ color: tokens.colors.onSurface, opacity: 0.8, marginTop: 2 }}>{subtitle}</Text> : null}
          </View>

          {/* Retro compatibility (scanlines) if someone uses tile outside Jarvis */}
          {isRetro && tokens.effects.scanlines ? (
            <View pointerEvents="none" style={[StyleSheet.absoluteFill, { opacity: 0.08 }]}> 
              <View style={{ flex: 1, backgroundColor: 'transparent' }} />
            </View>
          ) : null}
        </View>
      </Pressable>
    </Animated.View>
  );
};

export default JarvisActionTile;
