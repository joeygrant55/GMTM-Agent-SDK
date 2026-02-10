import React from 'react';
import { AbsoluteFill, interpolate, spring, useVideoConfig } from 'remotion';
import { COLORS, FONTS } from '../styles';
import type { AthleteData } from '../RecruitingVideo';

export const ProfileScene: React.FC<{ frame: number; duration: number; data: AthleteData }> = ({ frame, data }) => {
  const { fps } = useVideoConfig();

  // Name slides in from left
  const nameSlide = spring({ frame, fps, config: { damping: 15, stiffness: 100 } });
  const nameX = interpolate(nameSlide, [0, 1], [-800, 0]);

  // Badge fades in
  const badgeOpacity = interpolate(frame, [15, 30], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const badgeY = interpolate(frame, [15, 30], [20, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  // Stats animate in one by one
  const statItems = [
    { label: 'Height / Weight', value: `${data.height} • ${data.weight}` },
    { label: '40-Yard Dash', value: data.fortyYard },
    ...data.stats.map((s) => ({ label: s.label, value: s.value })),
  ];

  // Class year + location
  const locationOpacity = interpolate(frame, [140, 160], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', padding: '0 80px' }}>
      {/* Athlete Name */}
      <div
        style={{
          fontFamily: FONTS.heading,
          fontSize: 80,
          fontWeight: 700,
          color: COLORS.white,
          transform: `translateX(${nameX}px)`,
          marginBottom: 12,
        }}
      >
        {data.name}
      </div>

      {/* Sport + Position Badge */}
      <div
        style={{
          display: 'flex',
          gap: 12,
          marginBottom: 48,
          opacity: badgeOpacity,
          transform: `translateY(${badgeY}px)`,
        }}
      >
        <div
          style={{
            fontFamily: FONTS.body,
            fontSize: 20,
            color: COLORS.bg,
            backgroundColor: COLORS.accent,
            padding: '8px 20px',
            borderRadius: 8,
            fontWeight: 600,
          }}
        >
          {data.sport}
        </div>
        <div
          style={{
            fontFamily: FONTS.body,
            fontSize: 20,
            color: COLORS.accent,
            border: `2px solid ${COLORS.accent}`,
            padding: '8px 20px',
            borderRadius: 8,
            fontWeight: 600,
          }}
        >
          {data.position}
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
        {statItems.map((stat, i) => {
          const statDelay = 30 + i * 20;
          const statSpring = spring({
            frame: Math.max(0, frame - statDelay),
            fps,
            config: { damping: 14, stiffness: 150 },
          });
          const statX = interpolate(statSpring, [0, 1], [400, 0]);
          const statOpacity = interpolate(statSpring, [0, 1], [0, 1]);

          return (
            <div
              key={i}
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                maxWidth: 600,
                transform: `translateX(${statX}px)`,
                opacity: statOpacity,
                backgroundColor: COLORS.card,
                padding: '16px 24px',
                borderRadius: 12,
                borderLeft: `4px solid ${COLORS.accent}`,
              }}
            >
              <span style={{ fontFamily: FONTS.body, fontSize: 22, color: COLORS.gray }}>{stat.label}</span>
              <span style={{ fontFamily: FONTS.heading, fontSize: 24, fontWeight: 700, color: COLORS.white }}>
                {stat.value}
              </span>
            </div>
          );
        })}
      </div>

      {/* Class Year + Location */}
      <div
        style={{
          marginTop: 40,
          fontFamily: FONTS.body,
          fontSize: 22,
          color: COLORS.gray,
          opacity: locationOpacity,
        }}
      >
        Class of {data.classYear} • {data.location}
      </div>
    </AbsoluteFill>
  );
};
