import React from 'react';
import { View } from 'react-native';
import { useTheme } from 'react-native-paper';

export type DoorState = 'open' | 'closed' | 'opening' | 'closing' | undefined;

/**
 * GarageDoorGlyph
 *
 * Renders a stylized, futuristic garage door glyph that reflects the current door state.
 * Uses layered Views (no SVG dependency) with glow accents tuned to the active theme.
 *
 * Args:
 *   props.state (DoorState): The current state of the door.
 *   props.size (number): The pixel size of the glyph's width. Height scales accordingly.
 *
 * Returns:
 *   React.ReactElement: A compact visual representing door state.
 */
export default function GarageDoorGlyph({ state, size = 28 }: { state: DoorState; size?: number }) {
  const theme = useTheme();
  const [phase, setPhase] = React.useState(0);

  // Normalize incoming state to be case-insensitive and constrained to our union
  const normState: DoorState = typeof state === 'string' ? (state.toLowerCase() as DoorState) : state;

  // Drive a simple 4-frame animation when in a transitioning state.
  React.useEffect(() => {
    if (normState === 'opening' || normState === 'closing') {
      const id = setInterval(() => setPhase(p => (p + 1) % 4), 250); // ~4 fps subtle glow
      return () => clearInterval(id);
    }
    // Reset phase on static states to have deterministic looks when switching
    setPhase(0);
    return undefined;
  }, [normState]);

  // Dimensions
  const width = size;
  const height = Math.round(size * 0.8);
  const border = Math.max(1, Math.round(size * 0.05));
  const slatGap = Math.max(1, Math.round(size * 0.06));
  const slatCount = 3;
  const innerW = width - border * 2;
  const innerH = height - border * 2;
  const slatH = Math.max(2, Math.floor((innerH - slatGap * (slatCount - 1)) / slatCount));

  // Colors
  const frameColor = theme.colors.outlineVariant ?? '#5a5a5a';
  const offFill = theme.colors.surfaceVariant ?? '#2a2a2a';
  const onFill = theme.colors.primary;
  const glow = theme.colors.primary;

  // Determine which slats are bright based on state and phase.
  // Indexing: 0 = top, 1 = middle, 2 = bottom (visual ordering).
  const isBright = (index: 0 | 1 | 2): boolean => {
    if (normState === 'closed') return true; // all bright
    if (normState === 'open') return false;  // all dim
    if (normState === 'closing') {
      // Sequence by phase: [100] → [110] → [111] → [000] → repeat
      switch (phase) {
        case 0: return index === 0;           // top only
        case 1: return index <= 1;            // top + middle
        case 2: return true;                  // all bright
        case 3: return false;                 // all dim (reset frame)
        default: return false;
      }
    }
    if (normState === 'opening') {
      // Sequence by phase: [111] → [110] → [100] → [000] → repeat
      switch (phase) {
        case 0: return true;                  // all bright
        case 1: return index <= 1;            // top + middle
        case 2: return index === 0;           // top only
        case 3: return false;                 // all dim (reset frame)
        default: return false;
      }
    }
    // Fallback
    return false;
  };

  // Door panel style factory
  const slatStyle = (filled: boolean): any => ({
    height: slatH,
    width: innerW,
    backgroundColor: filled ? onFill : offFill,
    borderRadius: Math.max(2, Math.round(size * 0.08)),
    shadowColor: glow,
    shadowOffset: { width: 0, height: filled ? 2 : 0 },
    shadowOpacity: filled ? 0.5 : 0.2,
    shadowRadius: filled ? 6 : 2,
    // Android elevation for glow-ish feel
    elevation: filled ? 4 : 0,
  });

  // Frame
  return (
    <View
      style={{
        width,
        height,
        borderWidth: border,
        borderColor: frameColor,
        borderRadius: Math.max(4, Math.round(size * 0.12)),
        padding: border,
        backgroundColor: theme.colors.surface,
        justifyContent: 'center',
        alignItems: 'center',
      }}
    >
      <View style={{ gap: slatGap }}>
        {/* Render in visual order: top, middle, bottom */}
        <View style={slatStyle(isBright(0))} />
        <View style={slatStyle(isBright(1))} />
        <View style={slatStyle(isBright(2))} />
      </View>
    </View>
  );
}
