import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ActivityIndicator, Text } from 'react-native-paper';
import { Platform, Pressable, View, Animated, StyleSheet, GestureResponderEvent, LayoutChangeEvent } from 'react-native';
import { useAppTheme } from '../theme/ThemeProvider';
import JarvisButtonVisual from './JarvisButtonVisual';

export type AppButtonStatus = 'idle' | 'pending' | 'success' | 'error';

export interface AppButtonProps {
  label: string;
  onPress?: (event: GestureResponderEvent) => void;
  disabled?: boolean;
  status?: AppButtonStatus;
  /** Optional compact size */
  compact?: boolean;
  /** Optional full width */
  fullWidth?: boolean;
}

/**
 * AppButton
 *
 * A theme-aware button that renders radically different visuals based on the app theme.
 * - Jarvis: angular SVG shape with clipped glow and press shade; sci‑fi press animations
 * - Retro (Green/Amber): flat, pixel-ish borders, no glow, scanline accent
 *
 * States: idle | pending | success | error
 */
const AppButton: React.FC<AppButtonProps> = ({ label, onPress, disabled, status = 'idle', compact, fullWidth }) => {
  const { tokens } = useAppTheme();

  const scale = useRef(new Animated.Value(1)).current;
  const glow = useRef(new Animated.Value(0)).current; // 0..1
  const shade = useRef(new Animated.Value(0)).current; // 0..1, press darkening

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

  const isJarvis = tokens.key === 'jarvis';
  const isRetro = tokens.key.startsWith('retro');

  const basePadding = compact ? tokens.spacing.sm : tokens.spacing.md;

  const colors = tokens.colors;

  const [size, setSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });
  const onLayout = (e: LayoutChangeEvent) => {
    const { width, height } = e.nativeEvent.layout;
    if (width !== size.w || height !== size.h) setSize({ w: width, h: height });
  };

  const androidRipple = useMemo(() => ({
    color: 'rgba(255,176,0,0.15)',
    borderless: false,
  }), []);

  // Increase contrast: on Jarvis use onSurface (light blue/white)
  const textColor = useMemo(() => {
    if (status === 'success') return '#00FF9C';
    if (status === 'error') return colors.error ?? '#FF4D4D';
    return colors.onSurface;
  }, [status, colors]);

  const containerStyle = useMemo(() => {
    if (isJarvis) {
      return [
        styles.base,
        {
          borderRadius: 0, // SVG defines the shape; avoid rounded clipping artifacts
          backgroundColor: 'transparent',
          overflow: 'visible',
        },
      ];
    }

    // Retro variants
    return [
      styles.base,
      {
        borderRadius: 0,
        backgroundColor: colors.surface,
        borderWidth: 1,
        borderColor: colors.outline ?? '#2a2a2a',
        overflow: 'hidden',
      },
    ];
  }, [isJarvis, colors]);

  const innerStyle = useMemo(() => {
    return {
      paddingVertical: basePadding,
      paddingHorizontal: tokens.spacing.lg,
      alignItems: 'center',
      justifyContent: 'center',
    } as const;
  }, [basePadding, tokens.spacing.lg]);

  const onPressIn = () => {
    Animated.parallel([
      Animated.spring(scale, { toValue: 0.98, useNativeDriver: true, speed: 50, bounciness: 6 }),
      Animated.timing(glow, { toValue: 1, duration: 160, useNativeDriver: false }),
      Animated.timing(shade, { toValue: 1, duration: 100, useNativeDriver: false }),
    ]).start();
  };
  const onPressOut = () => {
    Animated.parallel([
      Animated.spring(scale, { toValue: 1, useNativeDriver: true, speed: 50, bounciness: 6 }),
      Animated.timing(glow, { toValue: 0, duration: 240, useNativeDriver: false }),
      Animated.timing(shade, { toValue: 0, duration: 140, useNativeDriver: false }),
    ]).start();
  };

  const content = (
    <Animated.View style={[{ transform: [{ scale }] }, fullWidth ? { alignSelf: 'stretch' } : null]}>
      <View style={containerStyle} onLayout={onLayout}>
        {/* Jarvis angular SVG visual with clipped glow and shade */}
        {isJarvis && size.w > 0 && size.h > 0 ? (
          <View style={{ position: 'absolute', left: 0, right: 0, top: 0, bottom: 0 }} pointerEvents="none">
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

        {/* Retro scanline layer */}
        {isRetro && tokens.effects.scanlines ? (
          <View pointerEvents="none" style={[StyleSheet.absoluteFill, { opacity: 0.08 }]}> 
            <View style={{ flex: 1, backgroundColor: 'transparent' }} />
          </View>
        ) : null}

        <View style={innerStyle}>
          {status === 'pending' ? (
            <ActivityIndicator size={18} color={colors.primary} />
          ) : (
            <Text style={{ color: textColor, fontFamily: tokens.typography.headingFamily }}>
              {label}
            </Text>
          )}
        </View>
      </View>
    </Animated.View>
  );

  return (
    <Pressable
      onPress={onPress}
      disabled={disabled || status === 'pending'}
      // Disable native ripple for Jarvis so shade stays within custom border
      android_ripple={Platform.OS === 'android' && !isJarvis ? androidRipple : undefined}
      onPressIn={onPressIn}
      onPressOut={onPressOut}
      style={({ pressed }) => [
        fullWidth ? { alignSelf: 'stretch' } : null,
        { opacity: disabled ? 0.6 : pressed ? 0.96 : 1 },
      ]}
    >
      {content}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  base: {
    minWidth: 48,
  },
});

export default AppButton;
