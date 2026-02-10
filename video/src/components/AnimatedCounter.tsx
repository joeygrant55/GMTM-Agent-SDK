import React from 'react';
import { interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS, FONTS } from '../styles';

export const AnimatedCounter: React.FC<{
  frame: number;
  targetValue: number;
  delay?: number;
  fontSize?: number;
}> = ({ frame, targetValue, delay = 0, fontSize = 120 }) => {
  const { fps } = useVideoConfig();
  const delayedFrame = Math.max(0, frame - delay);

  const progress = spring({
    frame: delayedFrame,
    fps,
    config: { damping: 30, stiffness: 80, mass: 1 },
  });

  const currentValue = Math.round(interpolate(progress, [0, 1], [0, targetValue]));

  const scale = spring({
    frame: delayedFrame,
    fps,
    config: { damping: 12, stiffness: 200, mass: 0.5 },
  });

  return (
    <div
      style={{
        fontFamily: FONTS.heading,
        fontSize,
        fontWeight: 700,
        color: COLORS.accent,
        transform: `scale(${scale})`,
        textShadow: `0 0 40px ${COLORS.accent}80, 0 0 80px ${COLORS.accent}40`,
      }}
    >
      {currentValue}
    </div>
  );
};
