import React from 'react';
import { Composition } from 'remotion';
import { RecruitingVideo } from './RecruitingVideo';
import { sampleData } from './sample-data';
import { loadFont as loadSpaceGrotesk } from '@remotion/google-fonts/SpaceGrotesk';
import { loadFont as loadInter } from '@remotion/google-fonts/Inter';

loadSpaceGrotesk();
loadInter();

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* Landscape 1920x1080 */}
      <Composition
        id="RecruitingVideo"
        component={RecruitingVideo}
        durationInFrames={900}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ data: sampleData }}
      />
      {/* Portrait 1080x1920 for social */}
      <Composition
        id="RecruitingVideoPortrait"
        component={RecruitingVideo}
        durationInFrames={900}
        fps={30}
        width={1080}
        height={1920}
        defaultProps={{ data: sampleData }}
      />
    </>
  );
};
