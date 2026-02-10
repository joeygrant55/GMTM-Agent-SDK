import type { AthleteData } from './RecruitingVideo';

export const sampleData: AthleteData = {
  name: 'JoJo Earle',
  sport: 'Football',
  position: 'Wide Receiver',
  classYear: 2022,
  location: 'Aledo, TX',
  height: '5\'10"',
  weight: '170 lbs',
  fortyYard: '4.41s',
  stats: [
    { label: 'Receptions', value: '55' },
    { label: 'Rec Yards', value: '1,039' },
    { label: 'Touchdowns', value: '16' },
  ],
  sparqRating: 94,
  sparqPercentile: 'Top 6%',
  matches: [
    {
      school: 'University of Alabama',
      matchPct: 97,
      fitDetail: 'Slot receiver need, up-tempo spread offense',
    },
    {
      school: 'Ohio State University',
      matchPct: 93,
      fitDetail: 'WR depth needed, pro-style with RPO',
    },
    {
      school: 'LSU',
      matchPct: 89,
      fitDetail: 'Speed receiver priority, passing game focus',
    },
  ],
  socialHandles: '@jojoearle',
};
