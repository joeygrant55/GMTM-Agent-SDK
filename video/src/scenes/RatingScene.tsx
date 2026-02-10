import React from 'react';
import { AbsoluteFill, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS, FONTS } from '../styles';
import { AnimatedCounter } from '../components/AnimatedCounter';
import { GlowCircle } from '../components/GlowCircle';
import type { AthleteData } from '../RecruitingVideo';

export const RatingScene: React.FC<{ frame: number; duration: number; data: AthleteData }> = ({ frame, data }) => {
  const { fps } = useVideoConfig();

  // Dramatic pause — slight delay before anything appears
  const revealDelay = 15;
  const revealFrame = Math.max(0, frame - revealDelay);

  const containerScale = spring({
    frame: revealFrame,
    fps,
    config: { damping: 10, stiffness: 80 },
  });

  // Percentile text fades in later
  const percentileOpacity = interpolate(frame, [90, 110], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const percentileY = interpolate(frame, [90, 110], [20, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // "SPARQ RATING" label
  const labelOpacity = interpolate(revealFrame, [0, 15], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', flexDirection: 'column' }}>
      {/* Label */}
      <div
        style={{
          fontFamily: FONTS.body,
          fontSize: 24,
          color: COLORS.gray,
          letterSpacing: 6,
          marginBottom: 40,
          opacity: labelOpacity,
        }}
      >
        SPARQ RATING
      </div>

      {/* Circle + Counter */}
      <div
        style={{
          position: 'relative',
          transform: `scale(${containerScale})`,
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
        }}
      >
        <GlowCircle frame={frame} progress={data.sparqRating / 100} delay={revealDelay} size={300} />
        <div style={{ position: 'absolute' }}>
          <AnimatedCounter frame={frame} targetValue={data.sparqRating} delay={revealDelay} fontSize={120} />
        </div>
      </div>

      {/* Percentile */}
      <div
        style={{
          fontFamily: FONTS.heading,
          fontSize: 32,
          color: COLORS.accent,
          marginTop: 40,
          opacity: percentileOpacity,
          transform: `translateY(${percentileY}px)`,
          textShadow: `0 0 20px ${COLORS.accent}40`,
        }}
      >
        {data.sparqPercentile} of Athletes
      </div>
    </AbsoluteFill>
  );
};
