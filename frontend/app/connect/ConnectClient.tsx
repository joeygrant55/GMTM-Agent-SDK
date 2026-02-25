'use client'

import { useState, useEffect } from 'react'
import { useUser } from '@clerk/nextjs'

interface AthleteResult {
  user_id: number
  first_name: string
  last_name: string
  city?: string
  state?: string
  position?: string
}

export default function ConnectClient() {
  const { user } = useUser()
  const [mode, setMode] = useState<'choice' | 'id' | 'search'>('choice')
  const [athleteId, setAthleteId] = useState('')
  const [searchName, setSearchName] = useState('')
  const [results, setResults] = useState<AthleteResult[]>([])
  const [preview, setPreview] = useState<AthleteResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [connected, setConnected] = useState(false)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

  // Check if already connected — redirect immediately if so
  useEffect(() => {
    if (user?.id) {
      setLoading(true)
      fetch(`${backendUrl}/api/profile/by-clerk/${user.id}`)
        .then(r => r.json())
        .then(data => {
          if (data.found && data.user_id) {
            window.location.href = `/athlete/${data.user_id}`
          } else {
            setLoading(false)
          }
        })
        .catch(() => setLoading(false))
    }
  }, [user?.id, backendUrl])

  const lookupById = async () => {
    if (!athleteId.trim()) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${backendUrl}/api/athlete/${athleteId}`)
      if (!res.ok) throw new Error('Athlete not found')
      const data = await res.json()
      setPreview(data)
    } catch {
      setError('No athlete found with that ID. Check your number and try again.')
      setPreview(null)
    }
    setLoading(false)
  }

  const searchByName = async () => {
    if (!searchName.trim() || searchName.trim().length < 2) return
    setLoading(true)
    setError('')
    try {
      const res = await fetch(`${backendUrl}/api/athlete/search?name=${encodeURIComponent(searchName)}`)
      if (!res.ok) throw new Error('Search failed')
      const data = await res.json()
      setResults(data.athletes || [])
      if (data.athletes?.length === 0) setError('No athletes found. Try a different name.')
    } catch {
      setError('Search failed. Try again.')
    }
    setLoading(false)
  }

  const connectProfile = async (userId: number) => {
    if (!user) return
    setLoading(true)
    try {
      await fetch(`${backendUrl}/api/profile/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId, clerk_id: user.id })
      })
      setConnected(true)
      setTimeout(() => {
        window.location.href = `/athlete/${userId}`
      }, 1500)
    } catch {
      setError('Failed to connect profile. Try again.')
    }
    setLoading(false)
  }

  // Show loading while checking if already connected
  if (loading && mode === 'choice' && !results.length && !preview) {
    return (
      <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Checking your profile...</p>
        </div>
      </div>
    )
  }

  if (connected) {
    return (
      <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🎉</div>
          <h2 className="text-3xl font-bold text-white mb-2">You're Connected!</h2>
          <p className="text-gray-400">Taking you to your dashboard...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center px-4">
      <div className="max-w-lg w-full">
        {/* Logo */}
        <div className="text-center mb-8">
          <img src="/sparq-logo.jpg" alt="SPARQ" className="w-14 h-14 rounded-2xl mx-auto mb-6" />
          <h1 className="text-3xl font-bold text-white">Connect Your Profile</h1>
          <p className="text-gray-400 mt-2">
            Link your SPARQ/GMTM athlete profile to get personalized recruiting advice.
          </p>
        </div>

        {/* Choice */}
        {mode === 'choice' && (
          <div className="space-y-4">
            <button
              onClick={() => setMode('id')}
              className="w-full bg-white/5 border border-white/10 rounded-xl p-6 text-left hover:border-sparq-lime/30 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-sparq-lime/10 rounded-lg flex items-center justify-center text-2xl">🔢</div>
                <div>
                  <h3 className="text-lg font-bold text-white">I Know My Athlete Number</h3>
                  <p className="text-gray-400 text-sm">Enter your GMTM athlete ID to connect instantly</p>
                </div>
              </div>
            </button>

            <button
              onClick={() => setMode('search')}
              className="w-full bg-white/5 border border-white/10 rounded-xl p-6 text-left hover:border-sparq-lime/30 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 bg-sparq-lime/10 rounded-lg flex items-center justify-center text-2xl">🔍</div>
                <div>
                  <h3 className="text-lg font-bold text-white">Search By Name</h3>
                  <p className="text-gray-400 text-sm">Find your profile by searching your name</p>
                </div>
              </div>
            </button>

            <div className="text-center pt-4">
              <p className="text-gray-500 text-sm">
                Don't have a GMTM profile? <a href="https://gmtm.com" target="_blank" className="text-sparq-lime hover:underline">Create one at gmtm.com</a>
              </p>
            </div>
          </div>
        )}

        {/* Lookup by ID */}
        {mode === 'id' && !preview && (
          <div className="bg-white/5 border border-white/10 rounded-xl p-8">
            <button onClick={() => { setMode('choice'); setError('') }} className="text-gray-400 text-sm hover:text-white mb-4">← Back</button>
            <h2 className="text-xl font-bold text-white mb-4">Enter Your Athlete Number</h2>
            <p className="text-gray-400 text-sm mb-6">
              Your athlete number is on your GMTM profile page (e.g., gmtm.com/profile/<strong className="text-white">67782</strong>)
            </p>
            <div className="flex gap-3">
              <input
                type="number"
                value={athleteId}
                onChange={e => setAthleteId(e.target.value)}
                placeholder="e.g. 67782"
                className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:border-sparq-lime focus:ring-1 focus:ring-sparq-lime"
                onKeyDown={e => e.key === 'Enter' && lookupById()}
              />
              <button
                onClick={lookupById}
                disabled={loading || !athleteId.trim()}
                className="px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark disabled:opacity-50 transition-colors"
              >
                {loading ? '...' : 'Find'}
              </button>
            </div>
            {error && <p className="mt-3 text-red-400 text-sm">{error}</p>}
          </div>
        )}

        {/* Preview / Confirm */}
        {preview && (
          <div className="bg-white/5 border border-white/10 rounded-xl p-8">
            <button onClick={() => { setPreview(null); setError('') }} className="text-gray-400 text-sm hover:text-white mb-4">← Back</button>
            <h2 className="text-xl font-bold text-white mb-6">Is This You?</h2>
            <div className="bg-white/5 border border-white/10 rounded-lg p-6 mb-6">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-sparq-lime/20 rounded-full flex items-center justify-center">
                  <span className="text-sparq-lime text-xl font-bold">
                    {preview.first_name?.[0]}{preview.last_name?.[0]}
                  </span>
                </div>
                <div>
                  <h3 className="text-xl font-bold text-white">{preview.first_name} {preview.last_name}</h3>
                  <p className="text-gray-400">
                    {preview.position && <span>{preview.position} • </span>}
                    {preview.city}, {preview.state}
                  </p>
                  <p className="text-gray-500 text-sm">Athlete #{preview.user_id}</p>
                </div>
              </div>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => connectProfile(preview.user_id)}
                disabled={loading}
                className="flex-1 px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark disabled:opacity-50 transition-colors"
              >
                {loading ? 'Connecting...' : "Yes, That's Me!"}
              </button>
              <button
                onClick={() => { setPreview(null); setAthleteId('') }}
                className="px-6 py-3 border border-white/20 rounded-lg text-white hover:bg-white/5 transition-colors"
              >
                Not Me
              </button>
            </div>
          </div>
        )}

        {/* Search by Name */}
        {mode === 'search' && (
          <div className="bg-white/5 border border-white/10 rounded-xl p-8">
            <button onClick={() => { setMode('choice'); setError(''); setResults([]) }} className="text-gray-400 text-sm hover:text-white mb-4">← Back</button>
            <h2 className="text-xl font-bold text-white mb-4">Search By Name</h2>
            <div className="flex gap-3 mb-4">
              <input
                type="text"
                value={searchName}
                onChange={e => setSearchName(e.target.value)}
                placeholder="First and last name"
                className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-lg text-white placeholder-gray-500 focus:border-sparq-lime focus:ring-1 focus:ring-sparq-lime"
                onKeyDown={e => e.key === 'Enter' && searchByName()}
              />
              <button
                onClick={searchByName}
                disabled={loading || searchName.trim().length < 2}
                className="px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark disabled:opacity-50 transition-colors"
              >
                {loading ? '...' : 'Search'}
              </button>
            </div>
            {error && <p className="mb-3 text-red-400 text-sm">{error}</p>}
            {results.length > 0 && (
              <div className="space-y-2 max-h-80 overflow-y-auto">
                {results.map(athlete => (
                  <button
                    key={athlete.user_id}
                    onClick={() => { setPreview(athlete); setMode('id') }}
                    className="w-full flex items-center gap-3 p-3 bg-white/5 rounded-lg hover:bg-white/10 transition-colors text-left"
                  >
                    <div className="w-10 h-10 bg-sparq-lime/20 rounded-full flex items-center justify-center">
                      <span className="text-sparq-lime text-sm font-bold">{athlete.first_name?.[0]}{athlete.last_name?.[0]}</span>
                    </div>
                    <div>
                      <div className="text-white font-medium">{athlete.first_name} {athlete.last_name}</div>
                      <div className="text-gray-400 text-sm">
                        {athlete.position && <span>{athlete.position} • </span>}
                        {athlete.city}, {athlete.state} • #{athlete.user_id}
                      </div>
                    </div>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
