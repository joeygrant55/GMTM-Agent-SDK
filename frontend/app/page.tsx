'use client'

import { useState } from 'react'
import Link from 'next/link'

export default function Home() {
  const [athleteId, setAthleteId] = useState('')
  const [menuOpen, setMenuOpen] = useState(false)

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white">
      {/* Nav */}
      <nav className="border-b border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center justify-between">
          <div className="flex items-center">
            <img src="/sparq-logo-white.png" alt="SPARQ" className="h-8 w-auto" />
          </div>
          {/* Desktop nav */}
          <div className="hidden sm:flex items-center gap-6">
            <a href="#features" className="text-sm text-gray-400 hover:text-white transition-colors">Features</a>
            <a href="#pricing" className="text-sm text-gray-400 hover:text-white transition-colors">Pricing</a>
            <Link href="/sign-in" className="px-4 py-2 text-sm font-medium bg-sparq-lime text-sparq-charcoal rounded-lg hover:bg-sparq-lime-dark transition-colors">
              Sign In
            </Link>
          </div>
          {/* Mobile hamburger */}
          <button onClick={() => setMenuOpen(!menuOpen)} className="sm:hidden p-2 -mr-2 text-gray-400 hover:text-white">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {menuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
        {/* Mobile menu */}
        {menuOpen && (
          <div className="sm:hidden border-t border-white/10 px-4 py-4 space-y-3">
            <a href="#features" onClick={() => setMenuOpen(false)} className="block text-sm text-gray-400 hover:text-white py-2">Features</a>
            <a href="#pricing" onClick={() => setMenuOpen(false)} className="block text-sm text-gray-400 hover:text-white py-2">Pricing</a>
            <Link href="/sign-in" className="block w-full text-center px-4 py-3 text-sm font-medium bg-sparq-lime text-sparq-charcoal rounded-lg hover:bg-sparq-lime-dark transition-colors">
              Sign In
            </Link>
          </div>
        )}
      </nav>

      {/* Hero */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 pt-12 sm:pt-20 pb-12 sm:pb-16 relative">
        {/* Hero Background */}
        <div className="absolute inset-0 -z-10 overflow-hidden">
          <img 
            src="/images/hero-bg.png" 
            alt="" 
            className="absolute inset-0 w-full h-full object-cover opacity-30"
          />
          <div className="absolute inset-0 bg-gradient-to-b from-sparq-charcoal/80 via-sparq-charcoal/60 to-sparq-charcoal" />
        </div>
        <div className="max-w-4xl relative">
          <div className="inline-block px-3 py-1 bg-sparq-lime/10 border border-sparq-lime/20 rounded-full text-sparq-lime text-sm font-medium mb-6">
            AI-Powered Recruiting Intelligence
          </div>
          <h1 className="text-4xl sm:text-5xl lg:text-7xl font-extrabold leading-tight">
            Your Personal
            <br />
            <span className="text-sparq-lime">Recruiting Advisor</span>
          </h1>
          <p className="mt-4 sm:mt-6 text-base sm:text-xl text-gray-400 max-w-2xl leading-relaxed">
            Get $5,000-level recruiting guidance for a fraction of the cost. SPARQ Agent analyzes your profile, matches you to programs, researches coaching staffs, and helps you get recruited — 24/7.
          </p>
          <div className="mt-10 flex flex-wrap gap-4">
            <Link href="/sign-up" className="px-8 py-4 bg-sparq-lime text-sparq-charcoal font-bold text-lg rounded-lg hover:bg-sparq-lime-dark transition-colors">
              Get Started Free
            </Link>
            <Link href="/demo" className="px-8 py-4 border border-white/20 text-white font-medium text-lg rounded-lg hover:bg-white/5 transition-colors">
              See Demo →
            </Link>
          </div>
        </div>
      </section>

      {/* Stats Bar */}
      <section className="border-y border-white/10 bg-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 grid grid-cols-2 sm:grid-cols-4 gap-4 sm:gap-8">
          <div className="text-center">
            <div className="text-2xl sm:text-3xl font-bold text-sparq-lime">75,000+</div>
            <div className="text-sm text-gray-400 mt-1">Athlete Profiles</div>
          </div>
          <div className="text-center">
            <div className="text-2xl sm:text-3xl font-bold text-sparq-lime">2,900+</div>
            <div className="text-sm text-gray-400 mt-1">College Programs</div>
          </div>
          <div className="text-center">
            <div className="text-2xl sm:text-3xl font-bold text-sparq-lime">131K</div>
            <div className="text-sm text-gray-400 mt-1">Performance Metrics</div>
          </div>
          <div className="text-center">
            <div className="text-2xl sm:text-3xl font-bold text-sparq-lime">24/7</div>
            <div className="text-sm text-gray-400 mt-1">Always Available</div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section id="features" className="max-w-7xl mx-auto px-4 sm:px-6 py-12 sm:py-20">
        <div className="text-center mb-10 sm:mb-16">
          <h2 className="text-2xl sm:text-4xl font-bold">Everything You Need to <span className="text-sparq-lime">Get Recruited</span></h2>
          <p className="mt-4 text-gray-400 text-base sm:text-lg max-w-2xl mx-auto">
            SPARQ Agent combines AI intelligence with real recruiting data to give you an unfair advantage.
          </p>
        </div>

        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-8">
          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-sparq-lime/30 transition-colors group">
            <div className="h-32 overflow-hidden">
              <img src="/images/college-matching.png" alt="College Matching" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
            </div>
            <div className="p-6">
              <h3 className="text-xl font-bold mb-3">College Matching</h3>
              <p className="text-gray-400 leading-relaxed">
                Get matched to programs based on your metrics, academics, location, and playing style. See which coaches are recruiting your position.
              </p>
            </div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-sparq-lime/30 transition-colors group">
            <div className="h-32 overflow-hidden">
              <img src="/images/profile-analysis.png" alt="Profile Analysis" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
            </div>
            <div className="p-6">
              <h3 className="text-xl font-bold mb-3">Profile Analysis</h3>
              <p className="text-gray-400 leading-relaxed">
                See how you stack up against other athletes at your position. Know your strengths, areas to improve, and where you rank.
              </p>
            </div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-sparq-lime/30 transition-colors group">
            <div className="h-32 overflow-hidden">
              <img src="/images/deep-research.png" alt="Deep Research" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
            </div>
            <div className="p-6">
              <h3 className="text-xl font-bold mb-3">Deep Research</h3>
              <p className="text-gray-400 leading-relaxed">
                Your agent researches coaching staffs, depth charts, recruiting classes, and NIL landscapes — so you don't have to.
              </p>
            </div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-sparq-lime/30 transition-colors group">
            <div className="h-32 overflow-hidden">
              <img src="/images/coach-outreach.png" alt="Coach Outreach" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
            </div>
            <div className="p-6">
              <h3 className="text-xl font-bold mb-3">Coach Outreach</h3>
              <p className="text-gray-400 leading-relaxed">
                Draft personalized emails to coaches with your real metrics. Know what to say, when to reach out, and how to follow up.
              </p>
            </div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-sparq-lime/30 transition-colors group">
            <div className="h-32 overflow-hidden">
              <img src="/images/camp-finder.png" alt="Camp Finder" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
            </div>
            <div className="p-6">
              <h3 className="text-xl font-bold mb-3">Camp Finder</h3>
              <p className="text-gray-400 leading-relaxed">
                Find camps, combines, and showcases near you. Get verified metrics that coaches trust.
              </p>
            </div>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-xl overflow-hidden hover:border-sparq-lime/30 transition-colors group">
            <div className="h-32 overflow-hidden">
              <img src="/images/saved-reports.png" alt="Saved Reports" className="w-full h-full object-cover group-hover:scale-105 transition-transform" />
            </div>
            <div className="p-6">
              <h3 className="text-xl font-bold mb-3">Saved Reports</h3>
              <p className="text-gray-400 leading-relaxed">
                Every deep research session generates a report you can save, reference, and share with coaches and family.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-y border-white/10 bg-white/5">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-12 sm:py-20">
          <h2 className="text-2xl sm:text-4xl font-bold text-center mb-10 sm:mb-16">How It <span className="text-sparq-lime">Works</span></h2>
          <div className="grid sm:grid-cols-3 gap-8 sm:gap-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-sparq-lime text-sparq-charcoal rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-5">1</div>
              <h3 className="text-xl font-bold mb-2">Create Your Profile</h3>
              <p className="text-gray-400">Sign up and connect your athlete profile. Add your links, film, and social media.</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-sparq-lime text-sparq-charcoal rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-5">2</div>
              <h3 className="text-xl font-bold mb-2">Ask Your Agent</h3>
              <p className="text-gray-400">Ask anything about recruiting. Your agent researches programs, analyzes your fit, and gives specific advice.</p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-sparq-lime text-sparq-charcoal rounded-full flex items-center justify-center text-2xl font-bold mx-auto mb-5">3</div>
              <h3 className="text-xl font-bold mb-2">Take Action</h3>
              <p className="text-gray-400">Use your reports to email coaches, attend the right camps, and make informed decisions about your future.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="max-w-7xl mx-auto px-4 sm:px-6 py-12 sm:py-20">
        <h2 className="text-2xl sm:text-4xl font-bold text-center mb-4">Simple <span className="text-sparq-lime">Pricing</span></h2>
        <p className="text-center text-gray-400 mb-10 sm:mb-16 text-base sm:text-lg">Recruiting services charge $2,000-5,000/year. We don&apos;t.</p>
        
        <div className="grid sm:grid-cols-2 gap-6 sm:gap-8 max-w-4xl mx-auto">
          {/* Free */}
          <div className="bg-white/5 border border-white/10 rounded-xl p-8">
            <h3 className="text-xl font-bold">Free</h3>
            <div className="mt-4 mb-6">
              <span className="text-4xl font-bold">$0</span>
              <span className="text-gray-400 ml-2">/month</span>
            </div>
            <ul className="space-y-3 text-gray-400 mb-8">
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> 3 conversations/month</li>
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> Basic profile analysis</li>
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> Camp finder</li>
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> 1 saved report</li>
            </ul>
            <Link href="/sign-up" className="block text-center px-6 py-3 border border-white/20 rounded-lg font-medium hover:bg-white/5 transition-colors">
              Get Started
            </Link>
          </div>

          {/* Premium */}
          <div className="bg-sparq-lime/5 border-2 border-sparq-lime rounded-xl p-8 relative">
            <div className="absolute -top-3 left-6 px-3 py-0.5 bg-sparq-lime text-sparq-charcoal text-xs font-bold rounded-full">MOST POPULAR</div>
            <h3 className="text-xl font-bold">Premium</h3>
            <div className="mt-4 mb-6">
              <span className="text-4xl font-bold">$29</span>
              <span className="text-gray-400 ml-2">/month</span>
            </div>
            <ul className="space-y-3 text-gray-300 mb-8">
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> <strong className="text-white">Unlimited</strong> conversations</li>
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> Deep college fit reports</li>
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> Coach email drafting</li>
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> Recruiting calendar alerts</li>
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> Unlimited saved reports</li>
              <li className="flex gap-2"><span className="text-sparq-lime">✓</span> Priority research</li>
            </ul>
            <Link href="/sign-up" className="block text-center px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark transition-colors">
              Start Free Trial
            </Link>
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-white/10 bg-white/5">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-12 sm:py-20 text-center">
          <h2 className="text-2xl sm:text-4xl font-bold mb-4">Ready to Get Recruited?</h2>
          <p className="text-gray-400 text-base sm:text-lg mb-8">
            Built on 75,000 athlete profiles and 2,900 college programs. Your recruiting edge starts here.
          </p>
          <div className="flex flex-wrap justify-center gap-4">
            <Link href="/sign-up" className="px-8 py-4 bg-sparq-lime text-sparq-charcoal font-bold text-lg rounded-lg hover:bg-sparq-lime-dark transition-colors">
              Get Started Free
            </Link>
            <div className="flex items-center gap-2">
              <input
                type="number"
                value={athleteId}
                onChange={(e) => setAthleteId(e.target.value)}
                placeholder="Athlete ID"
                className="px-4 py-4 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500 w-36"
              />
              <Link 
                href="/demo"
                className="px-6 py-4 border border-white/20 text-white font-medium rounded-lg hover:bg-white/5 transition-colors"
              >
                Try Demo
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/10">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 sm:py-8 flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center">
            <img src="/sparq-logo-white.png" alt="SPARQ" className="h-5 w-auto opacity-50" />
          </div>
          <p className="text-xs sm:text-sm text-gray-500">
            Powered by SPARQ data • Built for athletes
          </p>
        </div>
      </footer>
    </div>
  )
}
