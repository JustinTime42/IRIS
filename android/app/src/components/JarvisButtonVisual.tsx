import React from 'react';
import Svg, { Defs, LinearGradient, Stop, Path, ClipPath, Rect, G } from 'react-native-svg';
import { View } from 'react-native';

export interface JarvisButtonVisualProps {
  width: number;
  height: number;
  glowIntensity: number; // 0..1
  shade?: number; // 0..1, additional uniform darkening when pressed
  borderColor?: string;
  fillColor?: string;
}

/**
 * JarvisButtonVisual
 *
 * Angular sci‑fi button shape with clipped glow that respects the path.
 * Shape: angled corners with notches; gradient stroke glow overlay.
 */
const JarvisButtonVisual: React.FC<JarvisButtonVisualProps> = ({ width, height, glowIntensity, shade = 0, borderColor = 'rgba(0,229,255,0.9)', fillColor = 'rgba(15,21,36,0.95)' }) => {
  const w = width;
  const h = height;
  const notch = Math.min(w, h) * 0.12;
  const inset = 2; // inner padding for stroke visibility

  // Create an angular path: top-left and bottom-right notched
  const d = `M ${inset + notch} ${inset}
             L ${w - inset - notch} ${inset}
             L ${w - inset} ${inset + notch}
             L ${w - inset} ${h - inset - notch}
             L ${w - inset - notch} ${h - inset}
             L ${inset + notch} ${h - inset}
             L ${inset} ${h - inset - notch}
             L ${inset} ${inset + notch}
             Z`;

  const clampedGlow = Math.max(0, Math.min(1, glowIntensity));
  const clampedShade = Math.max(0, Math.min(1, shade));

  return (
    <View style={{ width, height }}>
      <Svg width={w} height={h}>
        <Defs>
          <ClipPath id="clip">
            <Path d={d} />
          </ClipPath>
          <LinearGradient id="glow" x1="0%" y1="0%" x2="100%" y2="0%">
            <Stop offset="0%" stopColor={borderColor} stopOpacity={0.0} />
            <Stop offset="50%" stopColor={borderColor} stopOpacity={0.95} />
            <Stop offset="100%" stopColor={borderColor} stopOpacity={0.0} />
          </LinearGradient>
        </Defs>

        {/* Fill */}
        <Path d={d} fill={fillColor} clipPath="url(#clip)" />

        {/* Uniform press shade clipped to path */}
        {clampedShade > 0 ? (
          <Rect
            x={0}
            y={0}
            width={w}
            height={h}
            clipPath="url(#clip)"
            fill="#000"
            opacity={0.25 * clampedShade}
          />
        ) : null}

        {/* Border */}
        <Path d={d} fill="none" stroke={borderColor} strokeWidth={1.5} />

        {/* Inner edge glow: a thicker stroke clipped to the shape so glow is clearly visible but contained */}
        {clampedGlow > 0 ? (
          <G clipPath="url(#clip)">
            <Path d={d} fill="none" stroke={borderColor} strokeWidth={4} opacity={0.65 * clampedGlow} />
          </G>
        ) : null}

        {/* Glow overlay clipped to shape (broad gradient wash) */}
        {clampedGlow > 0 ? (
          <Rect
            x={0}
            y={0}
            width={w}
            height={h}
            clipPath="url(#clip)"
            fill="url(#glow)"
            opacity={0.8 * clampedGlow}
          />
        ) : null}
      </Svg>
    </View>
  );
};

export default JarvisButtonVisual;
