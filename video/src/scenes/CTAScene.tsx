import React from 'react';
import { AbsoluteFill, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS, FONTS } from '../styles';
import type { AthleteData } from '../RecruitingVideo';

export const CTAScene: React.FC<{ frame: number; duration: number; data: AthleteData }> = ({ frame, data }) => {
  const { fps } = useVideoConfig();

  const mainSpring = spring({ frame, fps, config: { damping: 12, stiffness: 100 } });
  const scale = interpolate(mainSpring, [0, 1], [0.8, 1]);
  const opacity = interpolate(mainSpring, [0, 1], [0, 1]);

  const urlOpacity = interpolate(frame, [30, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const socialOpacity = interpolate(frame, [50, 70], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Glow pulse on CTA
  const glowPulse = interpolate(Math.sin(frame * 0.12), [-1, 1], [10, 40]);

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        flexDirection: 'column',
        transform: `scale(${scale})`,
        opacity,
      }}
    >
      {/* CTA Text */}
      <div
        style={{
          fontFamily: FONTS.heading,
          fontSize: 56,
          fontWeight: 700,
          color: COLORS.white,
          marginBottom: 32,
          textAlign: 'center',
        }}
      >
        Ready to get recruited?
      </div>

      {/* SPARQ Logo Text */}
      <div
        style={{
          fontFamily: FONTS.heading,
          fontSize: 80,
          fontWeight: 700,
          color: COLORS.accent,
          letterSpacing: 8,
          textShadow: `0 0 ${glowPulse}px ${COLORS.accent}, 0 0 ${glowPulse * 2}px ${COLORS.accent}40`,
          marginBottom: 24,
        }}
      >
        SPARQ
      </div>

      {/* URL */}
      <div
        style={{
          fontFamily: FONTS.body,
          fontSize: 28,
          color: COLORS.gray,
          opacity: urlOpacity,
          marginBottom: 16,
        }}
      >
        sparq-agent.vercel.app
      </div>

      {/* Social */}
      {data.socialHandles && (
        <div
          style={{
            fontFamily: FONTS.body,
            fontSize: 22,
            color: COLORS.accent,
            opacity: socialOpacity,
          }}
        >
          {data.socialHandles}
        </div>
      )}
    </AbsoluteFill>
  );
};
