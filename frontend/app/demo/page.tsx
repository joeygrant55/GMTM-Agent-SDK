'use client'

import { useState, useEffect, useRef, useCallback } from 'react'
import Link from 'next/link'

// ============================================================
// HARDCODED DEMO DATA
// ============================================================

const DEMO_ATHLETE = {
  name: 'JoJo Earle',
  position: 'Cornerback',
  city: 'Aledo',
  state: 'TX',
  stars: 4,
  classYear: 2026,
  height: '5\'11"',
  weight: 175,
  gpa: 3.4,
  initials: 'JE',
  stats: {
    fortyYard: '4.45',
    shuttle: '4.02',
    vertical: '38.5"',
    broad: '10\'4"',
    benchReps: 12,
  },
}

const AGENT_STEPS = [
  { delay: 0, type: 'status' as const, text: '● Agent online — analyzing athlete profile...' },
  { delay: 800, type: 'tool' as const, text: '🔍 query_athlete_metrics(id=383)', result: '→ 47 verified metrics loaded (speed, agility, film grades)' },
  { delay: 1800, type: 'tool' as const, text: '📊 compute_percentile_rankings(position="CB", state="TX")', result: '→ 94th percentile speed · 89th percentile coverage' },
  { delay: 2800, type: 'tool' as const, text: '🎓 match_college_programs(filters={D1, Big12, SEC, AAC})', result: '→ Scanned 2,932 programs — 6 strong matches found' },
  { delay: 3800, type: 'tool' as const, text: '🏟️ analyze_roster_needs(programs=6)', result: '→ 4/6 programs have CB roster gaps for 2026' },
  { delay: 4600, type: 'status' as const, text: '✅ Analysis complete — rendering results' },
]

const COLLEGE_MATCHES = [
  {
    name: 'TCU',
    fullName: 'Texas Christian University',
    conference: 'Big 12',
    matchScore: 94,
    scholarshipLikelihood: 'High',
    reasons: ['Your 4.45 40-yard dash matches their speed requirements', 'DB coach recruited 3 Texas CBs last cycle', 'Academic profile aligns (3.4 GPA vs 3.2 avg)'],
    coach: 'Coach Mark Perry',
    coachEmail: 'mark.perry@tcu.edu',
    recentRecruits: 'Signed 2 CBs from TX in 2025',
    rosterNeed: 'Losing 2 senior CBs — high need for 2026',
    color: '#4D1979',
  },
  {
    name: 'Baylor',
    fullName: 'Baylor University',
    conference: 'Big 12',
    matchScore: 91,
    scholarshipLikelihood: 'High',
    reasons: ['Film grade matches their press coverage scheme', 'Your shuttle time (4.02) is elite for their defensive system', 'Strong Texas pipeline from Aledo area'],
    coach: 'Coach Tyler Turner',
    coachEmail: 'tyler.turner@baylor.edu',
    recentRecruits: 'Signed 4 DFW-area recruits in 2025',
    rosterNeed: 'Rebuilding secondary — 3 CB spots open',
    color: '#154734',
  },
  {
    name: 'Arkansas',
    fullName: 'University of Arkansas',
    conference: 'SEC',
    matchScore: 88,
    scholarshipLikelihood: 'Medium-High',
    reasons: ['SEC program actively targeting Texas talent', 'Your vertical (38.5") ranks top-10 among CB prospects', 'Scheme fit: zone-heavy defense needs athletic CBs'],
    coach: 'Coach Donte Williams',
    coachEmail: 'donte.williams@arkansas.edu',
    recentRecruits: 'Expanding TX recruiting footprint',
    rosterNeed: 'Need 2 CBs for 2026 class',
    color: '#9D2235',
  },
  {
    name: 'Oklahoma State',
    fullName: 'Oklahoma State University',
    conference: 'Big 12',
    matchScore: 86,
    scholarshipLikelihood: 'Medium-High',
    reasons: ['Defensive coordinator values speed — your 4.45 is a fit', 'Strong track record developing 4-star DBs', 'Campus visit program active for TX recruits'],
    coach: 'Coach Bryan Nardo',
    coachEmail: 'bryan.nardo@okstate.edu',
    recentRecruits: 'Signed 1 CB from TX in 2025',
    rosterNeed: 'Moderate need — targeting top-tier talent',
    color: '#FF6600',
  },
  {
    name: 'Texas Tech',
    fullName: 'Texas Tech University',
    conference: 'Big 12',
    matchScore: 84,
    scholarshipLikelihood: 'Medium',
    reasons: ['In-state program with aggressive DB recruiting', 'Your broad jump (10\'4") shows explosive athleticism they value', 'New defensive scheme fits your skill set'],
    coach: 'Coach Derek Jones',
    coachEmail: 'derek.jones@ttu.edu',
    recentRecruits: 'Heavy TX recruiting — 8 in-state signees in 2025',
    rosterNeed: 'Building depth at CB position',
    color: '#CC0000',
  },
  {
    name: 'Houston',
    fullName: 'University of Houston',
    conference: 'Big 12',
    matchScore: 82,
    scholarshipLikelihood: 'Medium',
    reasons: ['New Big 12 member investing in defensive talent', 'Proximity advantage — strong TX family ties', 'Film analysis shows fit for their aggressive man coverage'],
    coach: 'Coach Shaun Jolly',
    coachEmail: 'shaun.jolly@houston.edu',
    recentRecruits: 'Doubled DB recruiting budget for 2026',
    rosterNeed: 'Need athletic CBs for Big 12 competition',
    color: '#C8102E',
  },
]

const DRAFT_EMAIL = `Dear Coach Perry,

My name is JoJo Earle, a Class of 2026 Cornerback from Aledo High School in Aledo, TX. I'm writing to express my strong interest in TCU's football program and the Horned Frogs' tradition of developing elite defensive backs.

This past season, I recorded 4 interceptions and 38 tackles while earning All-District honors. My verified testing numbers include a 4.45 40-yard dash, 4.02 shuttle, and a 38.5" vertical — metrics I believe align well with TCU's defensive philosophy.

I maintain a 3.4 GPA and am committed to excelling both on the field and in the classroom.

I would love the opportunity to visit campus and learn more about your program. My highlight film and full profile are available on SPARQ.

Thank you for your time and consideration.

Best regards,
JoJo Earle
SPARQ Profile: sparq.io/athletes/383`

// ============================================================
// HELPER COMPONENTS
// ============================================================

function TypewriterText({ text, speed = 20, onComplete, className = '' }: {
  text: string
  speed?: number
  onComplete?: () => void
  className?: string
}) {
  const [displayed, setDisplayed] = useState('')
  const indexRef = useRef(0)

  useEffect(() => {
    indexRef.current = 0
    setDisplayed('')
    const interval = setInterval(() => {
      indexRef.current++
      if (indexRef.current <= text.length) {
        setDisplayed(text.slice(0, indexRef.current))
      } else {
        clearInterval(interval)
        onComplete?.()
      }
    }, speed)
    return () => clearInterval(interval)
  }, [text, speed, onComplete])

  return <span className={className}>{displayed}<span className="animate-pulse text-sparq-lime">▊</span></span>
}

function AnimatedProgressBar({ target, delay = 0, color = 'bg-sparq-lime' }: {
  target: number
  delay?: number
  color?: string
}) {
  const [width, setWidth] = useState(0)

  useEffect(() => {
    const timer = setTimeout(() => {
      requestAnimationFrame(() => setWidth(target))
    }, delay)
    return () => clearTimeout(timer)
  }, [target, delay])

  return (
    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
      <div
        className={`h-full rounded-full transition-all duration-1000 ease-out ${color}`}
        style={{ width: `${width}%` }}
      />
    </div>
  )
}

function StarRating({ stars }: { stars: number }) {
  return (
    <div className="flex gap-0.5">
      {[1, 2, 3, 4, 5].map(i => (
        <svg key={i} className={`w-4 h-4 ${i <= stars ? 'text-sparq-lime' : 'text-gray-600'}`} fill="currentColor" viewBox="0 0 20 20">
          <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
        </svg>
      ))}
    </div>
  )
}

// ============================================================
// MAIN DEMO PAGE
// ============================================================

export default function DemoPage() {
  // Auto-demo state
  const [visibleSteps, setVisibleSteps] = useState<number[]>([])
  const [visibleCards, setVisibleCards] = useState<number[]>([])
  const [expandedCard, setExpandedCard] = useState<number | null>(null)
  const [showEmailPrompt, setShowEmailPrompt] = useState(false)
  const [showEmail, setShowEmail] = useState(false)
  const [emailComplete, setEmailComplete] = useState(false)
  const [showCTA, setShowCTA] = useState(false)
  const [athleteVisible, setAthleteVisible] = useState(false)
  const [demoStarted, setDemoStarted] = useState(false)
  const [cardScoresAnimated, setCardScoresAnimated] = useState(false)

  // Interactive section state
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [selectedAthlete, setSelectedAthlete] = useState<any>(null)
  const [chatMessages, setChatMessages] = useState<{ role: string; content: string; streaming?: boolean }[]>([])
  const [chatInput, setChatInput] = useState('')
  const [isChatStreaming, setIsChatStreaming] = useState(false)
  const [liveToolCalls, setLiveToolCalls] = useState<string[]>([])
  const [conversationId, setConversationId] = useState<string | null>(null)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://focused-essence-production-9809.up.railway.app'
  const chatEndRef = useRef<HTMLDivElement>(null)

  // ============================================================
  // AUTO-DEMO SEQUENCE
  // ============================================================

  useEffect(() => {
    if (demoStarted) return
    setDemoStarted(true)

    // (0s) Show athlete card
    const t0 = setTimeout(() => setAthleteVisible(true), 300)

    // Agent steps appear with their delays
    const stepTimers = AGENT_STEPS.map((step, i) =>
      setTimeout(() => {
        setVisibleSteps(prev => [...prev, i])
      }, 1000 + step.delay)
    )

    // (3.5s) Cards start appearing one by one
    const cardTimers = COLLEGE_MATCHES.map((_, i) =>
      setTimeout(() => {
        setVisibleCards(prev => [...prev, i])
      }, 4500 + i * 400)
    )

    // (5.5s) Animate scores
    const scoreTimer = setTimeout(() => setCardScoresAnimated(true), 5500)

    // (7s) Expand first card
    const expandTimer = setTimeout(() => setExpandedCard(0), 7500)

    // (9s) Show email prompt
    const emailPromptTimer = setTimeout(() => setShowEmailPrompt(true), 9500)

    // (10s) Show email
    const emailTimer = setTimeout(() => setShowEmail(true), 10500)

    // (15s) Show CTA (give email time to type)
    const ctaTimer = setTimeout(() => setShowCTA(true), 18000)

    return () => {
      clearTimeout(t0)
      stepTimers.forEach(clearTimeout)
      cardTimers.forEach(clearTimeout)
      clearTimeout(scoreTimer)
      clearTimeout(expandTimer)
      clearTimeout(emailPromptTimer)
      clearTimeout(emailTimer)
      clearTimeout(ctaTimer)
    }
  }, [demoStarted])

  // Scroll chat
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [chatMessages, liveToolCalls])

  // ============================================================
  // INTERACTIVE SEARCH & CHAT
  // ============================================================

  const handleSearch = useCallback(async (q: string) => {
    if (!q.trim() || q.length < 2) {
      setSearchResults([])
      return
    }
    setIsSearching(true)
    try {
      const res = await fetch(`${backendUrl}/api/search?q=${encodeURIComponent(q)}&limit=10`)
      if (res.ok) {
        const data = await res.json()
        setSearchResults(data.results || data || [])
      }
    } catch (err) {
      console.error('Search error:', err)
    }
    setIsSearching(false)
  }, [backendUrl])

  useEffect(() => {
    const debounce = setTimeout(() => {
      if (searchQuery.length >= 2) handleSearch(searchQuery)
      else setSearchResults([])
    }, 300)
    return () => clearTimeout(debounce)
  }, [searchQuery, handleSearch])

  const selectAthlete = (athlete: any) => {
    setSelectedAthlete(athlete)
    setSearchResults([])
    setSearchQuery('')
    setChatMessages([])
    setConversationId(null)
  }

  const sendChatMessage = async (text: string) => {
    if (!text.trim() || isChatStreaming || !selectedAthlete) return

    const userMsg = { role: 'user', content: text }
    setChatMessages(prev => [...prev, userMsg])
    setChatInput('')
    setIsChatStreaming(true)

    let fullText = ''
    const toolsUsed: string[] = []

    try {
      const res = await fetch(`${backendUrl}/api/agent/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_id: String(selectedAthlete.id || selectedAthlete.athlete_id),
          message: text,
          conversation_id: conversationId,
        }),
      })

      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let currentEvent = ''

      setChatMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const rawData = line.slice(6)
            if (currentEvent === 'text') {
              fullText += rawData.replace(/\\n/g, '\n')
              setChatMessages(prev => {
                const updated = [...prev]
                updated[updated.length - 1] = { role: 'assistant', content: fullText, streaming: true }
                return updated
              })
            } else if (currentEvent === 'tool_start') {
              try {
                const data = JSON.parse(rawData)
                toolsUsed.push(data.tool)
                setLiveToolCalls(prev => [...prev, data.tool])
              } catch {}
            } else if (currentEvent === 'tool_done') {
              try {
                const data = JSON.parse(rawData)
                setLiveToolCalls(prev => prev.filter(t => t !== data.tool))
              } catch {}
            } else if (currentEvent === 'conversation_id') {
              try {
                const data = JSON.parse(rawData)
                setConversationId(data.conversation_id)
              } catch {}
            }
            currentEvent = ''
          }
        }
      }
    } catch {
      fullText = 'Connection error — please try again.'
    }

    setChatMessages(prev => {
      const updated = [...prev]
      updated[updated.length - 1] = { role: 'assistant', content: fullText, streaming: false }
      return updated
    })
    setLiveToolCalls([])
    setIsChatStreaming(false)
  }

  // ============================================================
  // RENDER
  // ============================================================

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white">
      {/* ===== HEADER ===== */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-sparq-charcoal/90 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <div className="w-8 h-8 bg-sparq-lime rounded-lg flex items-center justify-center">
                <span className="text-sparq-charcoal font-black text-sm">S</span>
              </div>
              <span className="font-bold text-white text-lg hidden sm:block">SPARQ Agent</span>
            </Link>
            <span className="px-2 py-0.5 bg-sparq-lime/10 text-sparq-lime text-xs font-semibold rounded-full border border-sparq-lime/20 animate-pulse">
              LIVE DEMO
            </span>
          </div>
          <Link
            href="/sign-up"
            className="px-5 py-2 bg-sparq-lime text-sparq-charcoal text-sm font-bold rounded-lg hover:bg-sparq-lime-dark transition-all hover:scale-105"
          >
            Get Started Free
          </Link>
        </div>
      </header>

      {/* ===== HERO SECTION ===== */}
      <section className="relative overflow-hidden">
        {/* Subtle grid background */}
        <div className="absolute inset-0 opacity-5" style={{
          backgroundImage: 'linear-gradient(rgba(205,220,57,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(205,220,57,0.3) 1px, transparent 1px)',
          backgroundSize: '40px 40px',
        }} />

        <div className="relative max-w-7xl mx-auto px-4 pt-8 pb-4">
          {/* Title */}
          <div className="text-center mb-8">
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-black mb-3">
              <span className="text-white">AI Recruiting Agent</span>{' '}
              <span className="text-sparq-lime">in Action</span>
            </h1>
            <p className="text-gray-400 text-lg max-w-2xl mx-auto">
              Watch our agent analyze a real athlete profile, match to colleges, and draft outreach — in seconds.
            </p>
          </div>

          {/* ===== SPLIT SCREEN LAYOUT ===== */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">

            {/* LEFT: Agent Brain */}
            <div className="bg-black/40 border border-white/10 rounded-xl overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 bg-white/5 border-b border-white/10">
                <div className="flex gap-1.5">
                  <div className="w-3 h-3 rounded-full bg-red-500/80" />
                  <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
                  <div className="w-3 h-3 rounded-full bg-green-500/80" />
                </div>
                <span className="text-xs font-mono text-gray-400 ml-2">sparq-agent — analysis</span>
              </div>

              <div className="p-4 font-mono text-sm space-y-2 max-h-[500px] overflow-y-auto">
                {/* Athlete Card */}
                <div className={`transition-all duration-700 ${athleteVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
                  <div className="bg-white/5 rounded-lg p-4 mb-3 border border-white/10">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-12 h-12 bg-sparq-lime/20 rounded-full flex items-center justify-center flex-shrink-0">
                        <span className="text-sparq-lime font-bold">{DEMO_ATHLETE.initials}</span>
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <span className="text-white font-bold text-base">{DEMO_ATHLETE.name}</span>
                          <StarRating stars={DEMO_ATHLETE.stars} />
                        </div>
                        <span className="text-gray-400 text-xs">{DEMO_ATHLETE.position} · {DEMO_ATHLETE.city}, {DEMO_ATHLETE.state} · Class of {DEMO_ATHLETE.classYear}</span>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      {Object.entries(DEMO_ATHLETE.stats).map(([key, val]) => (
                        <div key={key} className="bg-black/30 rounded px-2 py-1.5 text-center">
                          <div className="text-sparq-lime font-bold">{val}</div>
                          <div className="text-gray-500 capitalize">{key.replace(/([A-Z])/g, ' $1').trim()}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Agent Steps */}
                {AGENT_STEPS.map((step, i) => (
                  <div
                    key={i}
                    className={`transition-all duration-500 ${visibleSteps.includes(i) ? 'opacity-100 translate-x-0' : 'opacity-0 -translate-x-4'}`}
                  >
                    {step.type === 'status' ? (
                      <div className="text-sparq-lime text-xs py-1">{step.text}</div>
                    ) : (
                      <div className="bg-black/30 rounded p-2 border-l-2 border-sparq-lime/50">
                        <div className="text-sparq-lime/80 text-xs">{step.text}</div>
                        {step.result && visibleSteps.includes(i) && (
                          <div className="text-gray-500 text-xs mt-1">{step.result}</div>
                        )}
                      </div>
                    )}
                  </div>
                ))}

                {/* Email Prompt */}
                {showEmailPrompt && (
                  <div className="mt-3 transition-all duration-500 animate-fadeIn">
                    <div className="bg-sparq-lime/10 border border-sparq-lime/30 rounded-lg p-3">
                      <div className="text-sparq-lime text-xs font-semibold mb-1">💬 Agent Suggestion</div>
                      <div className="text-gray-300 text-xs">TCU is your strongest match (94%). Want me to draft an intro email to Coach Perry?</div>
                      {!showEmail && (
                        <button
                          onClick={() => setShowEmail(true)}
                          className="mt-2 px-3 py-1 bg-sparq-lime text-sparq-charcoal text-xs font-bold rounded hover:bg-sparq-lime-dark transition-colors"
                        >
                          Draft Email →
                        </button>
                      )}
                      {showEmail && (
                        <div className="text-sparq-lime/60 text-xs mt-1">✓ Drafting email...</div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* RIGHT: Results */}
            <div className="space-y-3">
              {/* Results Header */}
              <div className={`transition-all duration-500 ${visibleCards.length > 0 ? 'opacity-100' : 'opacity-0'}`}>
                <div className="flex items-center justify-between mb-1">
                  <h3 className="text-white font-bold text-lg">College Matches</h3>
                  <span className="text-sparq-lime text-sm font-medium">{visibleCards.length}/{COLLEGE_MATCHES.length} found</span>
                </div>
                <p className="text-gray-500 text-xs mb-3">Ranked by overall fit score — metrics, academics, scheme, and roster needs</p>
              </div>

              {/* College Cards */}
              <div className="space-y-3 max-h-[480px] overflow-y-auto pr-1">
                {COLLEGE_MATCHES.map((college, i) => (
                  <div
                    key={i}
                    className={`transition-all duration-600 ${visibleCards.includes(i) ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-8'}`}
                  >
                    <div
                      className={`bg-white/5 border rounded-xl overflow-hidden cursor-pointer transition-all duration-300 hover:bg-white/[0.07] ${expandedCard === i ? 'border-sparq-lime/50 ring-1 ring-sparq-lime/20' : 'border-white/10'}`}
                      onClick={() => setExpandedCard(expandedCard === i ? null : i)}
                    >
                      <div className="p-4">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-3">
                            <div
                              className="w-10 h-10 rounded-lg flex items-center justify-center font-bold text-white text-sm"
                              style={{ backgroundColor: college.color }}
                            >
                              {college.name.slice(0, 3).toUpperCase()}
                            </div>
                            <div>
                              <div className="text-white font-semibold">{college.fullName}</div>
                              <div className="text-gray-500 text-xs">{college.conference}</div>
                            </div>
                          </div>
                          <div className="text-right">
                            <div className="text-2xl font-black text-sparq-lime">
                              {cardScoresAnimated ? college.matchScore : 0}%
                            </div>
                            <div className={`text-xs font-medium ${
                              college.scholarshipLikelihood === 'High' ? 'text-green-400' :
                              college.scholarshipLikelihood === 'Medium-High' ? 'text-yellow-400' :
                              'text-orange-400'
                            }`}>
                              {college.scholarshipLikelihood} scholarship likelihood
                            </div>
                          </div>
                        </div>

                        {/* Progress Bar */}
                        <AnimatedProgressBar
                          target={cardScoresAnimated ? college.matchScore : 0}
                          delay={i * 200}
                        />

                        {/* Reasons */}
                        <div className="mt-3 space-y-1">
                          {college.reasons.slice(0, expandedCard === i ? 3 : 1).map((reason, j) => (
                            <div key={j} className="flex items-start gap-2 text-xs">
                              <span className="text-sparq-lime mt-0.5 flex-shrink-0">✓</span>
                              <span className="text-gray-400">{reason}</span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Expanded Details */}
                      {expandedCard === i && (
                        <div className="border-t border-white/10 p-4 bg-black/20 space-y-3 animate-fadeIn">
                          <div className="grid grid-cols-2 gap-3 text-xs">
                            <div>
                              <div className="text-gray-500 mb-1">Position Coach</div>
                              <div className="text-white font-medium">{college.coach}</div>
                              <div className="text-sparq-lime">{college.coachEmail}</div>
                            </div>
                            <div>
                              <div className="text-gray-500 mb-1">Roster Need</div>
                              <div className="text-white">{college.rosterNeed}</div>
                            </div>
                          </div>
                          <div className="text-xs">
                            <div className="text-gray-500 mb-1">Recent Activity</div>
                            <div className="text-gray-300">{college.recentRecruits}</div>
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Email Draft */}
              {showEmail && (
                <div className="bg-white/5 border border-white/10 rounded-xl p-4 animate-fadeIn">
                  <div className="flex items-center gap-2 mb-3">
                    <span className="text-sparq-lime">✉️</span>
                    <span className="text-white font-semibold text-sm">Draft Email to TCU</span>
                  </div>
                  <div className="bg-black/30 rounded-lg p-3 text-xs text-gray-300 font-mono leading-relaxed whitespace-pre-wrap">
                    {!emailComplete ? (
                      <TypewriterText
                        text={DRAFT_EMAIL}
                        speed={15}
                        onComplete={() => {
                          setEmailComplete(true)
                          setShowCTA(true)
                        }}
                      />
                    ) : (
                      <>{DRAFT_EMAIL}</>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Hero CTA */}
          {showCTA && (
            <div className="text-center mt-10 animate-fadeIn">
              <Link
                href="/sign-up"
                className="inline-flex items-center gap-2 px-8 py-4 bg-sparq-lime text-sparq-charcoal text-lg font-black rounded-xl hover:bg-sparq-lime-dark transition-all hover:scale-105 shadow-lg shadow-sparq-lime/20"
              >
                Get This for YOUR Athlete →
              </Link>
              <p className="text-gray-500 text-sm mt-3">Free for athletes. No credit card needed.</p>
            </div>
          )}
        </div>
      </section>

      {/* ===== DIVIDER ===== */}
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="h-px bg-gradient-to-r from-transparent via-sparq-lime/30 to-transparent" />
      </div>

      {/* ===== INTERACTIVE SECTION ===== */}
      <section className="max-w-7xl mx-auto px-4 pb-16">
        <div className="text-center mb-8">
          <h2 className="text-2xl sm:text-3xl font-black text-white mb-2">Try It Yourself</h2>
          <p className="text-gray-400">Search any athlete and get real-time AI recruiting analysis</p>
        </div>

        {/* Search */}
        <div className="max-w-xl mx-auto mb-8 relative">
          <div className="relative">
            <svg className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search 75,000+ athletes by name..."
              className="w-full pl-12 pr-4 py-4 bg-white/5 border border-white/20 rounded-xl text-white placeholder-gray-500 focus:border-sparq-lime focus:ring-1 focus:ring-sparq-lime text-lg"
            />
            {isSearching && (
              <div className="absolute right-4 top-1/2 -translate-y-1/2">
                <div className="w-5 h-5 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin" />
              </div>
            )}
          </div>

          {/* Search Results Dropdown */}
          {searchResults.length > 0 && (
            <div className="absolute z-40 w-full mt-2 bg-sparq-charcoal-light border border-white/10 rounded-xl shadow-2xl overflow-hidden">
              {searchResults.map((athlete: any, i: number) => (
                <button
                  key={i}
                  onClick={() => selectAthlete(athlete)}
                  className="w-full flex items-center gap-3 px-4 py-3 hover:bg-white/5 transition-colors text-left border-b border-white/5 last:border-0"
                >
                  <div className="w-9 h-9 bg-sparq-lime/20 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-sparq-lime text-xs font-bold">
                      {(athlete.name || athlete.first_name || '?')[0]}
                    </span>
                  </div>
                  <div>
                    <div className="text-white text-sm font-medium">
                      {athlete.name || `${athlete.first_name || ''} ${athlete.last_name || ''}`}
                    </div>
                    <div className="text-gray-500 text-xs">
                      {athlete.position || 'Athlete'} {athlete.city ? `· ${athlete.city}, ${athlete.state}` : ''}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Selected Athlete Chat */}
        {selectedAthlete && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 animate-fadeIn">
            {/* Live Agent Brain (narrow) */}
            <div className="bg-black/40 border border-white/10 rounded-xl overflow-hidden">
              <div className="flex items-center gap-2 px-4 py-2.5 bg-white/5 border-b border-white/10">
                <div className="w-2 h-2 rounded-full bg-green-400 animate-pulse" />
                <span className="text-xs font-mono text-gray-400">agent live</span>
              </div>
              <div className="p-3 space-y-2 max-h-[400px] overflow-y-auto font-mono text-xs">
                {liveToolCalls.length > 0 ? (
                  liveToolCalls.map((tool, i) => (
                    <div key={i} className="flex items-center gap-2 text-sparq-lime">
                      <div className="w-3 h-3 border border-sparq-lime border-t-transparent rounded-full animate-spin" />
                      <span>{tool}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-gray-600">Waiting for query...</div>
                )}
              </div>
            </div>

            {/* Chat (wide) */}
            <div className="lg:col-span-2 bg-white/5 border border-white/10 rounded-xl overflow-hidden flex flex-col" style={{ maxHeight: '500px' }}>
              <div className="px-4 py-3 bg-white/5 border-b border-white/10 flex items-center gap-3">
                <div className="w-8 h-8 bg-sparq-lime/20 rounded-full flex items-center justify-center">
                  <span className="text-sparq-lime text-xs font-bold">
                    {(selectedAthlete.name || selectedAthlete.first_name || '?')[0]}
                  </span>
                </div>
                <div>
                  <div className="text-white text-sm font-semibold">
                    {selectedAthlete.name || `${selectedAthlete.first_name || ''} ${selectedAthlete.last_name || ''}`}
                  </div>
                  <div className="text-gray-500 text-xs">Live agent session</div>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-4 space-y-3">
                {chatMessages.length === 0 && (
                  <div className="text-center py-8">
                    <p className="text-gray-500 text-sm mb-4">Ask anything about this athlete&apos;s recruiting potential</p>
                    <div className="flex flex-wrap justify-center gap-2">
                      {['Best college fits?', 'Draft an email to coaches', 'How do their stats compare?'].map((q, i) => (
                        <button
                          key={i}
                          onClick={() => sendChatMessage(q)}
                          className="px-3 py-1.5 bg-white/5 border border-white/10 rounded-lg text-xs text-gray-300 hover:border-sparq-lime/30 transition-colors"
                        >
                          {q}
                        </button>
                      ))}
                    </div>
                  </div>
                )}

                {chatMessages.map((msg, i) => (
                  <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[80%] rounded-xl px-4 py-2.5 text-sm ${
                      msg.role === 'user'
                        ? 'bg-sparq-lime text-sparq-charcoal'
                        : 'bg-black/30 border border-white/10 text-gray-300'
                    }`}>
                      {msg.streaming ? (
                        <>{msg.content}<span className="animate-pulse text-sparq-lime">▊</span></>
                      ) : (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      )}
                    </div>
                  </div>
                ))}
                <div ref={chatEndRef} />
              </div>

              <div className="p-3 border-t border-white/10">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={chatInput}
                    onChange={e => setChatInput(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && sendChatMessage(chatInput)}
                    placeholder="Ask about recruiting..."
                    disabled={isChatStreaming}
                    className="flex-1 px-3 py-2 bg-black/30 border border-white/10 rounded-lg text-white text-sm placeholder-gray-600 focus:border-sparq-lime disabled:opacity-50"
                  />
                  <button
                    onClick={() => sendChatMessage(chatInput)}
                    disabled={isChatStreaming || !chatInput.trim()}
                    className="px-4 py-2 bg-sparq-lime text-sparq-charcoal text-sm font-bold rounded-lg hover:bg-sparq-lime-dark disabled:opacity-50 transition-colors"
                  >
                    Send
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* ===== BOTTOM CTA ===== */}
      <section className="border-t border-white/10 bg-black/20">
        <div className="max-w-4xl mx-auto px-4 py-16 text-center">
          <h2 className="text-2xl sm:text-3xl md:text-4xl font-black text-white mb-4">
            This is what <span className="text-sparq-lime">$5,000 recruiting advisors</span> charge for.
          </h2>
          <p className="text-xl text-gray-400 mb-8">Get it free with SPARQ.</p>
          <Link
            href="/sign-up"
            className="inline-flex items-center gap-2 px-10 py-4 bg-sparq-lime text-sparq-charcoal text-lg font-black rounded-xl hover:bg-sparq-lime-dark transition-all hover:scale-105 shadow-lg shadow-sparq-lime/20"
          >
            Sign Up Free →
          </Link>

          {/* Stats Bar */}
          <div className="mt-12 grid grid-cols-3 gap-8 max-w-lg mx-auto">
            {[
              { value: '75K+', label: 'Athletes' },
              { value: '2,900+', label: 'Colleges' },
              { value: '131K+', label: 'Metrics' },
            ].map((stat, i) => (
              <div key={i} className="text-center">
                <div className="text-2xl font-black text-sparq-lime">{stat.value}</div>
                <div className="text-gray-500 text-sm">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Global Styles for animations */}
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
