import React from 'react';
import { interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS, FONTS } from '../styles';
import type { CollegeMatch } from '../RecruitingVideo';

export const MatchCard: React.FC<{
  match: CollegeMatch;
  frame: number;
  delay: number;
  index: number;
}> = ({ match, frame, delay, index }) => {
  const { fps } = useVideoConfig();
  const delayedFrame = Math.max(0, frame - delay);

  const slideIn = spring({
    frame: delayedFrame,
    fps,
    config: { damping: 15, stiffness: 120 },
  });

  const barProgress = spring({
    frame: Math.max(0, delayedFrame - 10),
    fps,
    config: { damping: 20, stiffness: 60 },
  });

  const translateX = interpolate(slideIn, [0, 1], [600, 0]);
  const opacity = interpolate(slideIn, [0, 1], [0, 1]);

  return (
    <div
      style={{
        transform: `translateX(${translateX}px)`,
        opacity,
        backgroundColor: COLORS.card,
        borderRadius: 16,
        padding: '24px 32px',
        marginBottom: 20,
        border: `1px solid ${COLORS.accent}20`,
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
        <span style={{ fontFamily: FONTS.heading, fontSize: 28, fontWeight: 700, color: COLORS.white }}>
          {match.school}
        </span>
        <span style={{ fontFamily: FONTS.heading, fontSize: 32, fontWeight: 700, color: COLORS.accent }}>
          {match.matchPct}%
        </span>
      </div>
      <div style={{ fontFamily: FONTS.body, fontSize: 18, color: COLORS.gray, marginBottom: 12 }}>
        {match.fitDetail}
      </div>
      {/* Progress bar */}
      <div style={{ height: 6, backgroundColor: COLORS.darkGray, borderRadius: 3, overflow: 'hidden' }}>
        <div
          style={{
            height: '100%',
            width: `${barProgress * match.matchPct}%`,
            backgroundColor: COLORS.accent,
            borderRadius: 3,
            boxShadow: `0 0 12px ${COLORS.accent}60`,
          }}
        />
      </div>
    </div>
  );
};
