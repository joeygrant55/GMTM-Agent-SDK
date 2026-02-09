'use client'

import { useState, useEffect, useRef } from 'react'
import Link from 'next/link'

// ============================================================
// HARDCODED DATA — Zero API calls, instant load
// ============================================================

const ATHLETE = {
  name: 'JoJo Earle',
  position: 'Cornerback',
  city: 'Aledo',
  state: 'TX',
  highSchool: 'Aledo High School',
  stars: 4,
  classYear: 2026,
  height: '5\'11"',
  weight: 175,
  gpa: 3.4,
  fortyYard: 4.45,
  shuttle: 4.02,
  vertical: 38.5,
  broadJump: 10.33,
  benchReps: 12,
  interceptions: 4,
  tackles: 38,
  passBreakups: 12,
  honors: 'All-District First Team',
}

// Radar chart data: label, value (0-100), percentile
const RADAR_METRICS = [
  { label: 'Speed', value: 94, percentile: 94 },
  { label: 'Agility', value: 89, percentile: 89 },
  { label: 'Explosiveness', value: 91, percentile: 91 },
  { label: 'Coverage', value: 87, percentile: 87 },
  { label: 'Tackling', value: 78, percentile: 78 },
  { label: 'Football IQ', value: 85, percentile: 85 },
]

const COLLEGES = [
  {
    name: 'TCU',
    fullName: 'Texas Christian University',
    conference: 'Big 12',
    matchScore: 94,
    scholarshipChance: 'High',
    color: '#4D1979',
    rosterNeed: 'Losing 2 senior CBs — high need',
    coach: 'Coach Mark Perry',
    coachTitle: 'Defensive Backs Coach',
    schemefit: 'Press-man coverage aligns with your physicality and 4.45 speed.',
    reasons: [
      'Your 4.45 40-yd dash matches their speed requirements',
      'DB coach recruited 3 Texas CBs last cycle',
      'Academic profile aligns (3.4 GPA vs 3.2 avg)',
    ],
  },
  {
    name: 'Baylor',
    fullName: 'Baylor University',
    conference: 'Big 12',
    matchScore: 91,
    scholarshipChance: 'High',
    color: '#154734',
    rosterNeed: 'Rebuilding secondary — 3 CB spots open',
    coach: 'Coach Tyler Turner',
    coachTitle: 'Cornerbacks Coach',
    schemefit: 'Shuttle time (4.02) is elite for their zone-press hybrid system.',
    reasons: [
      'Film grade matches their press coverage scheme',
      'Shuttle time (4.02) is elite for their defensive system',
      'Strong Texas pipeline from DFW area',
    ],
  },
  {
    name: 'Arkansas',
    fullName: 'University of Arkansas',
    conference: 'SEC',
    matchScore: 88,
    scholarshipChance: 'Medium-High',
    color: '#9D2235',
    rosterNeed: 'Need 2 CBs for 2026 class',
    coach: 'Coach Donte Williams',
    coachTitle: 'Secondary Coach',
    schemefit: 'Zone-heavy defense needs athletic CBs — your 38.5" vertical is top-10.',
    reasons: [
      'SEC program actively targeting Texas talent',
      'Your vertical (38.5") ranks top-10 among CB prospects',
      'Scheme fit: zone-heavy defense needs athletic CBs',
    ],
  },
  {
    name: 'Oklahoma St',
    fullName: 'Oklahoma State University',
    conference: 'Big 12',
    matchScore: 86,
    scholarshipChance: 'Medium-High',
    color: '#FF6600',
    rosterNeed: 'Targeting top-tier CB talent',
    coach: 'Coach Bryan Nardo',
    coachTitle: 'Defensive Backs Coach',
    schemefit: 'Coordinator values speed — your 4.45 is a perfect fit for their tempo defense.',
    reasons: [
      'DC values speed — your 4.45 is a fit',
      'Strong track record developing 4-star DBs',
      'Active campus visit program for TX recruits',
    ],
  },
  {
    name: 'Texas Tech',
    fullName: 'Texas Tech University',
    conference: 'Big 12',
    matchScore: 84,
    scholarshipChance: 'Medium',
    color: '#CC0000',
    rosterNeed: 'Building depth at CB',
    coach: 'Coach Derek Jones',
    coachTitle: 'Cornerbacks Coach',
    schemefit: 'New defensive scheme values explosive athleticism — broad jump 10\'4" stands out.',
    reasons: [
      'In-state program with aggressive DB recruiting',
      'Broad jump (10\'4") shows explosiveness they value',
      'New defensive scheme fits your skill set',
    ],
  },
  {
    name: 'Houston',
    fullName: 'University of Houston',
    conference: 'Big 12',
    matchScore: 82,
    scholarshipChance: 'Medium',
    color: '#C8102E',
    rosterNeed: 'Need athletic CBs for Big 12',
    coach: 'Coach Shaun Jolly',
    coachTitle: 'Defensive Backs Coach',
    schemefit: 'Film shows fit for their aggressive man coverage system.',
    reasons: [
      'New Big 12 member investing heavily in defense',
      'Proximity advantage — strong TX family ties',
      'Film analysis shows fit for man coverage',
    ],
  },
]

const TIMELINE = [
  { date: 'Feb 2026', event: 'SPARQ profile created — agent analysis begins', icon: '⚡', active: true },
  { date: 'Mar 2026', event: 'Junior Day visits — TCU, Baylor, Arkansas', icon: '🏟️', active: false },
  { date: 'Apr 2026', event: 'Spring evaluation period — send updated film', icon: '🎬', active: false },
  { date: 'Jun 2026', event: 'Camp circuit — TCU Elite, Baylor Showcase', icon: '🏃', active: false },
  { date: 'Sep 2026', event: 'Senior season kicks off — agent tracks live stats', icon: '🏈', active: false },
  { date: 'Dec 2026', event: 'Early signing period — commit window opens', icon: '✍️', active: false },
]

const DRAFT_EMAIL = `Dear Coach Perry,

My name is JoJo Earle, a Class of 2026 Cornerback from Aledo High School in Aledo, TX. I'm writing to express my strong interest in TCU's football program and the Horned Frogs' tradition of developing elite defensive backs.

This past season, I recorded 4 interceptions and 38 tackles while earning All-District honors. My verified testing numbers include a 4.45 40-yard dash, 4.02 shuttle, and a 38.5" vertical — metrics I believe align well with TCU's press-man defensive philosophy.

I maintain a 3.4 GPA and am committed to excelling both on the field and in the classroom.

I would love the opportunity to visit campus and learn more about your program. My highlight film and full profile are available on SPARQ.

Thank you for your time and consideration.

Best regards,
JoJo Earle
SPARQ Profile: sparq.io/athletes/383`

// ============================================================
// ANIMATION HELPERS
// ============================================================

function useReveal(delay: number) {
  const [visible, setVisible] = useState(false)
  useEffect(() => {
    const t = setTimeout(() => setVisible(true), delay)
    return () => clearTimeout(t)
  }, [delay])
  return visible
}

function useCountUp(target: number, delay: number, duration = 1200) {
  const [value, setValue] = useState(0)
  useEffect(() => {
    const startTime = Date.now() + delay
    let raf: number
    const animate = () => {
      const elapsed = Date.now() - startTime
      if (elapsed < 0) {
        raf = requestAnimationFrame(animate)
        return
      }
      const progress = Math.min(elapsed / duration, 1)
      const eased = 1 - Math.pow(1 - progress, 3) // ease-out cubic
      setValue(Math.round(target * eased))
      if (progress < 1) raf = requestAnimationFrame(animate)
    }
    raf = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(raf)
  }, [target, delay, duration])
  return value
}

function TypewriterText({ text, speed = 18, onComplete, delay = 0 }: {
  text: string; speed?: number; onComplete?: () => void; delay?: number
}) {
  const [displayed, setDisplayed] = useState('')
  const [started, setStarted] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setStarted(true), delay)
    return () => clearTimeout(t)
  }, [delay])

  useEffect(() => {
    if (!started) return
    let idx = 0
    const interval = setInterval(() => {
      idx++
      if (idx <= text.length) {
        setDisplayed(text.slice(0, idx))
      } else {
        clearInterval(interval)
        onComplete?.()
      }
    }, speed)
    return () => clearInterval(interval)
  }, [text, speed, started, onComplete])

  if (!started) return null
  return <>{displayed}<span className="animate-pulse text-sparq-lime">▊</span></>
}

// ============================================================
// CSS-ONLY RADAR CHART (SVG)
// ============================================================

function RadarChart({ metrics, animate, delay }: {
  metrics: typeof RADAR_METRICS; animate: boolean; delay: number
}) {
  const size = 280
  const center = size / 2
  const radius = 110
  const levels = 5

  const angleStep = (2 * Math.PI) / metrics.length
  const startAngle = -Math.PI / 2 // start at top

  const getPoint = (index: number, value: number) => {
    const angle = startAngle + index * angleStep
    const r = (value / 100) * radius
    return { x: center + r * Math.cos(angle), y: center + r * Math.sin(angle) }
  }

  // Grid rings
  const rings = Array.from({ length: levels }, (_, i) => {
    const r = ((i + 1) / levels) * radius
    const points = metrics.map((_, j) => {
      const angle = startAngle + j * angleStep
      return `${center + r * Math.cos(angle)},${center + r * Math.sin(angle)}`
    }).join(' ')
    return points
  })

  // Data polygon
  const dataPoints = metrics.map((m, i) => {
    const val = animate ? m.value : 0
    const p = getPoint(i, val)
    return `${p.x},${p.y}`
  }).join(' ')

  // Labels
  const labelPositions = metrics.map((m, i) => {
    const angle = startAngle + i * angleStep
    const r = radius + 28
    return {
      x: center + r * Math.cos(angle),
      y: center + r * Math.sin(angle),
      label: m.label,
      percentile: m.percentile,
    }
  })

  return (
    <svg viewBox={`0 0 ${size} ${size}`} className="w-full max-w-[280px] mx-auto">
      {/* Grid lines */}
      {rings.map((points, i) => (
        <polygon
          key={i}
          points={points}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth="1"
        />
      ))}
      {/* Axis lines */}
      {metrics.map((_, i) => {
        const p = getPoint(i, 100)
        return (
          <line
            key={i}
            x1={center} y1={center}
            x2={p.x} y2={p.y}
            stroke="rgba(255,255,255,0.06)"
            strokeWidth="1"
          />
        )
      })}
      {/* Data polygon */}
      <polygon
        points={dataPoints}
        fill="rgba(205,220,57,0.15)"
        stroke="#CDDC39"
        strokeWidth="2"
        className="transition-all duration-[1500ms] ease-out"
        style={{ transitionDelay: `${delay}ms` }}
      />
      {/* Data points */}
      {metrics.map((m, i) => {
        const val = animate ? m.value : 0
        const p = getPoint(i, val)
        return (
          <circle
            key={i}
            cx={p.x} cy={p.y} r="4"
            fill="#CDDC39"
            className="transition-all duration-[1500ms] ease-out"
            style={{ transitionDelay: `${delay}ms` }}
          />
        )
      })}
      {/* Labels */}
      {labelPositions.map((pos, i) => (
        <text
          key={i}
          x={pos.x}
          y={pos.y}
          textAnchor="middle"
          dominantBaseline="middle"
          className="fill-gray-400 text-[10px] font-medium"
        >
          {pos.label}
        </text>
      ))}
    </svg>
  )
}

// ============================================================
// SECTION WRAPPER — reveals with animation
// ============================================================

function Section({ delay, children, className = '' }: {
  delay: number; children: React.ReactNode; className?: string
}) {
  const visible = useReveal(delay)
  return (
    <div className={`transition-all duration-700 ease-out ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'} ${className}`}>
      {children}
    </div>
  )
}

// ============================================================
// MAIN PAGE
// ============================================================

export default function DemoPage() {
  const [radarAnimated, setRadarAnimated] = useState(false)
  const [emailDone, setEmailDone] = useState(false)
  const [timeElapsed, setTimeElapsed] = useState(0)

  // Timer counts up to 30
  useEffect(() => {
    const start = Date.now()
    const interval = setInterval(() => {
      const s = Math.min(30, Math.round((Date.now() - start) / 1000))
      setTimeElapsed(s)
      if (s >= 30) clearInterval(interval)
    }, 100)
    return () => clearInterval(interval)
  }, [])

  // Trigger radar animation
  useEffect(() => {
    const t = setTimeout(() => setRadarAnimated(true), 1200)
    return () => clearTimeout(t)
  }, [])

  const matchScore = useCountUp(94, 600)
  const athleteCount = useCountUp(75000, 200, 2000)
  const collegeCount = useCountUp(2932, 200, 2000)
  const metricCount = useCountUp(131000, 200, 2000)

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white selection:bg-sparq-lime/30 selection:text-white">
      {/* HEADER */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-sparq-charcoal/95 backdrop-blur-lg">
        <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-sparq-lime rounded-lg flex items-center justify-center">
                <span className="text-sparq-charcoal font-black text-sm">S</span>
              </div>
              <span className="font-bold text-lg hidden sm:inline">SPARQ</span>
            </Link>
            <span className="px-2 py-0.5 bg-sparq-lime/10 text-sparq-lime text-[10px] font-bold rounded-full border border-sparq-lime/20 uppercase tracking-wider">
              Recruiting Report
            </span>
          </div>
          <div className="flex items-center gap-3">
            <div className="hidden sm:flex items-center gap-1.5 text-xs text-gray-500">
              <div className="w-2 h-2 rounded-full bg-sparq-lime animate-pulse" />
              Generated in {timeElapsed}s
            </div>
            <Link
              href="/sign-up"
              className="px-4 py-2 bg-sparq-lime text-sparq-charcoal text-sm font-bold rounded-lg hover:bg-sparq-lime-dark transition-all hover:scale-105"
            >
              Get Yours Free
            </Link>
          </div>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-4 py-6 sm:py-10 space-y-8 sm:space-y-12">

        {/* ===== GENERATING BANNER ===== */}
        <Section delay={0}>
          <div className="flex items-center gap-3 px-4 py-3 bg-sparq-lime/5 border border-sparq-lime/20 rounded-xl text-sm">
            <div className="w-5 h-5 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin flex-shrink-0" />
            <span className="text-gray-300">
              <span className="text-sparq-lime font-semibold">SPARQ Agent</span> analyzed 2,932 programs, 131K metrics, and 47 verified data points to generate this report.
            </span>
          </div>
        </Section>

        {/* ===== ATHLETE PROFILE CARD ===== */}
        <Section delay={400}>
          <div className="bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/10 rounded-2xl overflow-hidden">
            <div className="p-5 sm:p-8">
              <div className="flex flex-col sm:flex-row gap-6">
                {/* Left: Identity */}
                <div className="flex-1">
                  <div className="flex items-start gap-4 mb-5">
                    <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-sparq-lime/30 to-sparq-lime/10 rounded-2xl flex items-center justify-center flex-shrink-0 border border-sparq-lime/20">
                      <span className="text-sparq-lime font-black text-2xl sm:text-3xl">JE</span>
                    </div>
                    <div>
                      <h1 className="text-2xl sm:text-3xl font-black text-white leading-tight">{ATHLETE.name}</h1>
                      <p className="text-gray-400 text-sm mt-1">{ATHLETE.position} · Class of {ATHLETE.classYear}</p>
                      <p className="text-gray-500 text-sm">{ATHLETE.highSchool} · {ATHLETE.city}, {ATHLETE.state}</p>
                      <div className="flex items-center gap-1 mt-2">
                        {[1,2,3,4,5].map(i => (
                          <svg key={i} className={`w-4 h-4 ${i <= ATHLETE.stars ? 'text-sparq-lime' : 'text-gray-700'}`} fill="currentColor" viewBox="0 0 20 20">
                            <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                          </svg>
                        ))}
                        <span className="text-sparq-lime text-xs font-semibold ml-1">4-Star Prospect</span>
                      </div>
                    </div>
                  </div>

                  {/* Quick Stats Grid */}
                  <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 sm:gap-3">
                    {[
                      { label: '40-Yard', value: `${ATHLETE.fortyYard}s`, highlight: true },
                      { label: 'Shuttle', value: `${ATHLETE.shuttle}s`, highlight: true },
                      { label: 'Vertical', value: `${ATHLETE.vertical}"`, highlight: false },
                      { label: 'Height', value: ATHLETE.height, highlight: false },
                      { label: 'GPA', value: `${ATHLETE.gpa}`, highlight: false },
                    ].map((stat, i) => (
                      <div key={i} className={`rounded-xl px-3 py-2.5 text-center ${stat.highlight ? 'bg-sparq-lime/10 border border-sparq-lime/20' : 'bg-white/5 border border-white/5'}`}>
                        <div className={`text-lg font-black ${stat.highlight ? 'text-sparq-lime' : 'text-white'}`}>{stat.value}</div>
                        <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5">{stat.label}</div>
                      </div>
                    ))}
                  </div>

                  {/* Season Stats */}
                  <div className="mt-4 flex flex-wrap gap-3 text-xs">
                    <span className="px-3 py-1.5 bg-white/5 rounded-full text-gray-300">🏈 {ATHLETE.interceptions} INT</span>
                    <span className="px-3 py-1.5 bg-white/5 rounded-full text-gray-300">💪 {ATHLETE.tackles} Tackles</span>
                    <span className="px-3 py-1.5 bg-white/5 rounded-full text-gray-300">🛡️ {ATHLETE.passBreakups} PBU</span>
                    <span className="px-3 py-1.5 bg-sparq-lime/10 rounded-full text-sparq-lime font-semibold">🏆 {ATHLETE.honors}</span>
                  </div>
                </div>

                {/* Right: Radar Chart */}
                <div className="sm:w-[300px] flex-shrink-0">
                  <div className="text-center mb-2">
                    <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">Percentile Rankings vs. National CBs</span>
                  </div>
                  <RadarChart metrics={RADAR_METRICS} animate={radarAnimated} delay={800} />
                </div>
              </div>
            </div>
          </div>
        </Section>

        {/* ===== TOP MATCH SCORE ===== */}
        <Section delay={1800}>
          <div className="text-center">
            <div className="inline-flex flex-col items-center px-8 py-5 bg-gradient-to-b from-sparq-lime/10 to-transparent border border-sparq-lime/20 rounded-2xl">
              <span className="text-xs text-gray-400 uppercase tracking-wider font-semibold mb-1">Top Match Score</span>
              <span className="text-6xl sm:text-7xl font-black text-sparq-lime leading-none">{matchScore}%</span>
              <span className="text-gray-400 text-sm mt-1">TCU Horned Frogs</span>
            </div>
          </div>
        </Section>

        {/* ===== COLLEGE MATCH CARDS ===== */}
        <Section delay={2800}>
          <div className="flex items-center justify-between mb-5">
            <div>
              <h2 className="text-xl sm:text-2xl font-black text-white">College Matches</h2>
              <p className="text-gray-500 text-sm mt-0.5">Ranked by overall fit — metrics, academics, scheme, and roster needs</p>
            </div>
            <span className="text-sparq-lime text-sm font-bold">{COLLEGES.length} matches</span>
          </div>

          <div className="space-y-4">
            {COLLEGES.map((college, i) => (
              <CollegeCard key={i} college={college} index={i} delay={3200 + i * 300} />
            ))}
          </div>
        </Section>

        {/* ===== RECRUITING TIMELINE ===== */}
        <Section delay={5800}>
          <h2 className="text-xl sm:text-2xl font-black text-white mb-5">Recruiting Timeline</h2>
          <div className="relative">
            {/* Vertical line */}
            <div className="absolute left-[18px] top-2 bottom-2 w-px bg-white/10" />
            <div className="space-y-4">
              {TIMELINE.map((item, i) => (
                <TimelineItem key={i} item={item} index={i} delay={6200 + i * 250} />
              ))}
            </div>
          </div>
        </Section>

        {/* ===== DRAFT EMAIL ===== */}
        <Section delay={7800}>
          <div className="bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/10 rounded-2xl overflow-hidden">
            <div className="px-5 py-4 border-b border-white/10 flex items-center gap-3">
              <span className="text-lg">✉️</span>
              <div>
                <h3 className="text-white font-bold text-sm">Draft Outreach — TCU</h3>
                <p className="text-gray-500 text-[11px]">AI-generated introduction to Coach Mark Perry</p>
              </div>
            </div>
            <div className="p-5">
              <div className="bg-black/30 rounded-xl p-4 sm:p-5 text-sm text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">
                <TypewriterText
                  text={DRAFT_EMAIL}
                  speed={12}
                  delay={8500}
                  onComplete={() => setEmailDone(true)}
                />
              </div>
              {emailDone && (
                <div className="mt-3 flex flex-wrap gap-2 animate-fadeIn">
                  <button className="px-4 py-2 bg-sparq-lime text-sparq-charcoal text-xs font-bold rounded-lg hover:bg-sparq-lime-dark transition-colors">
                    Copy to Clipboard
                  </button>
                  <button className="px-4 py-2 bg-white/5 border border-white/10 text-gray-300 text-xs font-medium rounded-lg hover:bg-white/10 transition-colors">
                    Regenerate
                  </button>
                  <button className="px-4 py-2 bg-white/5 border border-white/10 text-gray-300 text-xs font-medium rounded-lg hover:bg-white/10 transition-colors">
                    Generate for Baylor →
                  </button>
                </div>
              )}
            </div>
          </div>
        </Section>

        {/* ===== BOTTOM CTA ===== */}
        <Section delay={14000}>
          <div className="relative mt-8 mb-4">
            <div className="absolute inset-0 bg-gradient-to-r from-sparq-lime/5 via-sparq-lime/10 to-sparq-lime/5 rounded-3xl blur-xl" />
            <div className="relative bg-gradient-to-b from-sparq-charcoal-light to-sparq-charcoal border border-sparq-lime/20 rounded-3xl px-6 py-10 sm:py-14 text-center">
              <div className="text-sparq-lime text-sm font-bold uppercase tracking-wider mb-3">⚡ Report Complete</div>
              <h2 className="text-2xl sm:text-4xl font-black text-white mb-3 leading-tight">
                This took SPARQ Agent <span className="text-sparq-lime">30 seconds.</span>
                <br />
                <span className="text-gray-400">Want yours?</span>
              </h2>
              <p className="text-gray-500 text-base sm:text-lg mb-8 max-w-lg mx-auto">
                College recruiters charge $5,000+ for this level of analysis. SPARQ does it instantly, for free.
              </p>
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 px-8 sm:px-10 py-4 bg-sparq-lime text-sparq-charcoal text-lg font-black rounded-xl hover:bg-sparq-lime-dark transition-all hover:scale-105 shadow-lg shadow-sparq-lime/25"
              >
                Generate My Report →
              </Link>
              <p className="text-gray-600 text-sm mt-4">Free for athletes. No credit card required.</p>

              {/* Stats */}
              <div className="mt-10 grid grid-cols-3 gap-6 max-w-md mx-auto">
                <div>
                  <div className="text-2xl font-black text-sparq-lime">{athleteCount.toLocaleString()}+</div>
                  <div className="text-gray-500 text-xs uppercase tracking-wider">Athletes</div>
                </div>
                <div>
                  <div className="text-2xl font-black text-sparq-lime">{collegeCount.toLocaleString()}</div>
                  <div className="text-gray-500 text-xs uppercase tracking-wider">Colleges</div>
                </div>
                <div>
                  <div className="text-2xl font-black text-sparq-lime">{metricCount.toLocaleString()}+</div>
                  <div className="text-gray-500 text-xs uppercase tracking-wider">Data Points</div>
                </div>
              </div>
            </div>
          </div>
        </Section>
      </main>

      {/* FOOTER */}
      <footer className="border-t border-white/5 py-6 text-center">
        <p className="text-gray-600 text-xs">
          © 2026 SPARQ · AI-Powered Recruiting Intelligence
        </p>
      </footer>

      {/* Global Styles */}
      <style jsx global>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn {
          animation: fadeIn 0.5s ease-out forwards;
        }
      `}</style>
    </div>
  )
}

// ============================================================
// COLLEGE CARD COMPONENT
// ============================================================

function CollegeCard({ college, index, delay }: {
  college: typeof COLLEGES[0]; index: number; delay: number
}) {
  const visible = useReveal(delay)
  const [expanded, setExpanded] = useState(false)
  const score = useCountUp(college.matchScore, delay, 1000)

  return (
    <div
      className={`transition-all duration-600 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-6'}`}
    >
      <div
        onClick={() => setExpanded(!expanded)}
        className={`bg-white/[0.04] border rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 hover:bg-white/[0.06] ${
          expanded ? 'border-sparq-lime/40 ring-1 ring-sparq-lime/10' : 'border-white/8'
        }`}
      >
        <div className="p-4 sm:p-5">
          <div className="flex items-center gap-4">
            {/* School Badge */}
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center font-black text-white text-xs flex-shrink-0 shadow-lg"
              style={{ backgroundColor: college.color }}
            >
              {college.name.length <= 3 ? college.name : college.name.slice(0, 3)}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-white font-bold text-base">{college.fullName}</span>
                <span className="px-2 py-0.5 bg-white/5 rounded text-[10px] text-gray-400 font-medium">{college.conference}</span>
              </div>
              <p className="text-gray-500 text-xs mt-0.5 truncate">{college.rosterNeed}</p>
            </div>

            {/* Score */}
            <div className="text-right flex-shrink-0">
              <div className="text-3xl font-black text-sparq-lime leading-none">{score}%</div>
              <div className={`text-[10px] font-semibold mt-0.5 ${
                college.scholarshipChance === 'High' ? 'text-green-400' :
                college.scholarshipChance === 'Medium-High' ? 'text-yellow-400' : 'text-orange-400'
              }`}>
                {college.scholarshipChance}
              </div>
            </div>
          </div>

          {/* Match bar */}
          <div className="mt-3 h-1.5 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-sparq-lime to-sparq-lime-light transition-all duration-1000 ease-out"
              style={{ width: visible ? `${college.matchScore}%` : '0%', transitionDelay: `${delay - 2800}ms` }}
            />
          </div>

          {/* Top reason always visible */}
          <div className="mt-3 flex items-start gap-2 text-xs">
            <span className="text-sparq-lime mt-px flex-shrink-0">✓</span>
            <span className="text-gray-400">{college.reasons[0]}</span>
          </div>
        </div>

        {/* Expanded Details */}
        {expanded && (
          <div className="border-t border-white/5 p-4 sm:p-5 bg-black/20 space-y-4 animate-fadeIn">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Position Coach</div>
                <div className="text-white font-semibold text-sm">{college.coach}</div>
                <div className="text-gray-500 text-xs">{college.coachTitle}</div>
              </div>
              <div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Scheme Fit</div>
                <div className="text-gray-300 text-xs leading-relaxed">{college.schemefit}</div>
              </div>
            </div>

            <div>
              <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Why You Match</div>
              <div className="space-y-1.5">
                {college.reasons.map((r, j) => (
                  <div key={j} className="flex items-start gap-2 text-xs">
                    <span className="text-sparq-lime mt-px flex-shrink-0">✓</span>
                    <span className="text-gray-400">{r}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

// ============================================================
// TIMELINE ITEM
// ============================================================

function TimelineItem({ item, index, delay }: {
  item: typeof TIMELINE[0]; index: number; delay: number
}) {
  const visible = useReveal(delay)

  return (
    <div className={`flex gap-4 transition-all duration-500 ${visible ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'}`}>
      <div className={`w-9 h-9 rounded-full flex items-center justify-center flex-shrink-0 text-sm z-10 ${
        item.active
          ? 'bg-sparq-lime text-sparq-charcoal shadow-lg shadow-sparq-lime/30'
          : 'bg-sparq-charcoal-light border border-white/10'
      }`}>
        {item.icon}
      </div>
      <div className={`pb-4 ${item.active ? '' : 'opacity-70'}`}>
        <div className={`text-xs font-bold uppercase tracking-wider mb-0.5 ${item.active ? 'text-sparq-lime' : 'text-gray-500'}`}>
          {item.date}
        </div>
        <div className="text-sm text-gray-300">{item.event}</div>
      </div>
    </div>
  )
}
