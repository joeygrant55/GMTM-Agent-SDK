import React from 'react';
import { AbsoluteFill, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS, FONTS } from '../styles';

export const IntroScene: React.FC<{ frame: number; duration: number }> = ({ frame }) => {
  const { fps } = useVideoConfig();

  // SPARQ text springs in
  const titleSpring = spring({ frame, fps, config: { damping: 12, stiffness: 100 } });
  const titleScale = interpolate(titleSpring, [0, 1], [0.3, 1]);
  const titleOpacity = interpolate(titleSpring, [0, 1], [0, 1]);

  // Tagline fades in after title
  const taglineOpacity = interpolate(frame, [40, 60], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const taglineY = interpolate(frame, [40, 60], [20, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Glow pulse
  const glowIntensity = interpolate(Math.sin(frame * 0.1), [-1, 1], [20, 60]);

  // Particles
  const particles = Array.from({ length: 20 }, (_, i) => {
    const x = ((i * 137.5 + frame * 0.3) % 100);
    const y = ((i * 89.3 + frame * 0.5) % 100);
    const size = 2 + (i % 3);
    const particleOpacity = interpolate(frame, [0, 30], [0, 0.3 + (i % 5) * 0.1], {
      extrapolateRight: 'clamp',
    });
    return { x, y, size, opacity: particleOpacity };
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        flexDirection: 'column',
      }}
    >
      {/* Particles */}
      {particles.map((p, i) => (
        <div
          key={i}
          style={{
            position: 'absolute',
            left: `${p.x}%`,
            top: `${p.y}%`,
            width: p.size,
            height: p.size,
            borderRadius: '50%',
            backgroundColor: COLORS.accent,
            opacity: p.opacity,
          }}
        />
      ))}

      {/* SPARQ Title */}
      <div
        style={{
          fontFamily: FONTS.heading,
          fontSize: 140,
          fontWeight: 700,
          color: COLORS.accent,
          letterSpacing: 12,
          transform: `scale(${titleScale})`,
          opacity: titleOpacity,
          textShadow: `0 0 ${glowIntensity}px ${COLORS.accent}, 0 0 ${glowIntensity * 2}px ${COLORS.accent}60`,
        }}
      >
        SPARQ
      </div>

      {/* Tagline */}
      <div
        style={{
          fontFamily: FONTS.body,
          fontSize: 32,
          color: COLORS.white,
          opacity: taglineOpacity,
          transform: `translateY(${taglineY}px)`,
          letterSpacing: 6,
          marginTop: 16,
        }}
      >
        YOUR RECRUITING EDGE
      </div>
    </AbsoluteFill>
  );
};
