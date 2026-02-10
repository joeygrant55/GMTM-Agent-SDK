import React from 'react';
import { interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS } from '../styles';

export const GlowCircle: React.FC<{
  frame: number;
  progress: number;
  size?: number;
  delay?: number;
}> = ({ frame, progress, size = 280, delay = 0 }) => {
  const { fps } = useVideoConfig();
  const delayedFrame = Math.max(0, frame - delay);

  const strokeProgress = spring({
    frame: delayedFrame,
    fps,
    config: { damping: 30, stiffness: 80 },
  });

  const circumference = Math.PI * (size - 16);
  const strokeDashoffset = circumference * (1 - strokeProgress * progress);

  // Glow pulse when complete
  const pulseFrame = Math.max(0, delayedFrame - 60);
  const glowIntensity = pulseFrame > 0
    ? interpolate(Math.sin(pulseFrame * 0.15), [-1, 1], [0.4, 1])
    : 0;

  return (
    <div style={{ position: 'relative', width: size, height: size }}>
      <svg
        width={size}
        height={size}
        style={{
          transform: 'rotate(-90deg)',
          filter: `drop-shadow(0 0 ${20 + glowIntensity * 30}px ${COLORS.accent}80)`,
        }}
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={(size - 16) / 2}
          fill="none"
          stroke={COLORS.darkGray}
          strokeWidth={8}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={(size - 16) / 2}
          fill="none"
          stroke={COLORS.accent}
          strokeWidth={8}
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
        />
      </svg>
    </div>
  );
};
