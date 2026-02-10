import React from 'react';
import { AbsoluteFill, useCurrentFrame } from 'remotion';
import { IntroScene } from './scenes/IntroScene';
import { ProfileScene } from './scenes/ProfileScene';
import { RatingScene } from './scenes/RatingScene';
import { MatchesScene } from './scenes/MatchesScene';
import { CTAScene } from './scenes/CTAScene';
import { COLORS } from './styles';

export interface StatItem {
  label: string;
  value: string;
}

export interface CollegeMatch {
  school: string;
  matchPct: number;
  fitDetail: string;
}

export interface AthleteData {
  name: string;
  sport: string;
  position: string;
  classYear: number;
  location: string;
  height: string;
  weight: string;
  fortyYard: string;
  stats: StatItem[];
  sparqRating: number;
  sparqPercentile: string;
  matches: CollegeMatch[];
  socialHandles?: string;
}

// Scene frame ranges (at 30fps)
const SCENES = {
  intro: { start: 0, duration: 90 },       // 0-3s
  profile: { start: 90, duration: 240 },    // 3-11s
  rating: { start: 330, duration: 150 },    // 11-16s
  matches: { start: 480, duration: 300 },   // 16-26s
  cta: { start: 780, duration: 120 },       // 26-30s
};

export const RecruitingVideo: React.FC<{ data: AthleteData }> = ({ data }) => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: COLORS.bg }}>
      {/* Grid background */}
      <AbsoluteFill style={{ opacity: 0.06 }}>
        <svg width="100%" height="100%">
          <defs>
            <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke={COLORS.accent} strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#grid)" />
        </svg>
      </AbsoluteFill>

      {frame >= SCENES.intro.start && frame < SCENES.intro.start + SCENES.intro.duration && (
        <IntroScene frame={frame - SCENES.intro.start} duration={SCENES.intro.duration} />
      )}
      {frame >= SCENES.profile.start && frame < SCENES.profile.start + SCENES.profile.duration && (
        <ProfileScene frame={frame - SCENES.profile.start} duration={SCENES.profile.duration} data={data} />
      )}
      {frame >= SCENES.rating.start && frame < SCENES.rating.start + SCENES.rating.duration && (
        <RatingScene frame={frame - SCENES.rating.start} duration={SCENES.rating.duration} data={data} />
      )}
      {frame >= SCENES.matches.start && frame < SCENES.matches.start + SCENES.matches.duration && (
        <MatchesScene frame={frame - SCENES.matches.start} duration={SCENES.matches.duration} data={data} />
      )}
      {frame >= SCENES.cta.start && frame < SCENES.cta.start + SCENES.cta.duration && (
        <CTAScene frame={frame - SCENES.cta.start} duration={SCENES.cta.duration} data={data} />
      )}
    </AbsoluteFill>
  );
};
