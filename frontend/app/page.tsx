'use client'

import { MotionConfig } from 'framer-motion'
import { Nav } from '@/components/landing/Nav'
import { Hero } from '@/components/landing/Hero'
import { ProofBar } from '@/components/landing/ProofBar'
import { TheShift } from '@/components/landing/TheShift'
import { BentoFeatures } from '@/components/landing/BentoFeatures'
import { HowItWorks } from '@/components/landing/HowItWorks'
import { SocialProof } from '@/components/landing/SocialProof'
import { Pricing } from '@/components/landing/Pricing'
import { FinalCTA } from '@/components/landing/FinalCTA'
import { Footer } from '@/components/landing/Footer'
import { Grain } from '@/components/landing/_primitives/Grain'

export default function Home() {
  return (
    <MotionConfig reducedMotion="user">
      <div className="relative min-h-screen overflow-x-clip bg-sparq-charcoal text-white">
        <Grain />
        <Nav />
        <main>
          <Hero />
          <ProofBar />
          <TheShift />
          <BentoFeatures />
          <HowItWorks />
          <SocialProof />
          <Pricing />
          <FinalCTA />
        </main>
        <Footer />
      </div>
    </MotionConfig>
  )
}
