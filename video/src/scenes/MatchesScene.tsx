import React from 'react';
import { AbsoluteFill, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS, FONTS } from '../styles';
import { MatchCard } from '../components/MatchCard';
import type { AthleteData } from '../RecruitingVideo';

export const MatchesScene: React.FC<{ frame: number; duration: number; data: AthleteData }> = ({ frame, data }) => {
  const { fps } = useVideoConfig();

  // Header animation
  const headerSpring = spring({ frame, fps, config: { damping: 15, stiffness: 120 } });
  const headerOpacity = interpolate(headerSpring, [0, 1], [0, 1]);
  const headerY = interpolate(headerSpring, [0, 1], [-40, 0]);

  return (
    <AbsoluteFill style={{ justifyContent: 'center', padding: '0 80px' }}>
      {/* Header */}
      <div
        style={{
          fontFamily: FONTS.heading,
          fontSize: 52,
          fontWeight: 700,
          color: COLORS.white,
          marginBottom: 48,
          opacity: headerOpacity,
          transform: `translateY(${headerY}px)`,
        }}
      >
        Your Top Matches
      </div>

      {/* Match Cards */}
      {data.matches.map((match, i) => (
        <MatchCard key={i} match={match} frame={frame} delay={20 + i * 30} index={i} />
      ))}
    </AbsoluteFill>
  );
};
