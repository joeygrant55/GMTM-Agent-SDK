import { NextRequest, NextResponse } from 'next/server'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

function buildMockResults(query: string) {
  const cleaned = query.trim() || 'Jordan Mitchell'
  const firstName = cleaned.split(' ')[0] || 'Jordan'
  const lastName = cleaned.split(' ').slice(1).join(' ') || 'Mitchell'

  return [
    {
      maxprepsAthleteId: 'mock-1',
      name: `${firstName} ${lastName}`,
      position: 'Cornerback',
      school: 'Aledo High School',
      classYear: 2026,
      city: 'Aledo',
      state: 'TX',
      teamRecord: '11-2 (District Champions)',
      seasonStats: [
        { season: 'Sophomore', tackles: 28, interceptions: 1, passBreakups: 7 },
        { season: 'Junior', tackles: 47, interceptions: 3, passBreakups: 12 },
      ],
    },
    {
      maxprepsAthleteId: 'mock-2',
      name: `${firstName} ${lastName}`,
      position: 'Wide Receiver',
      school: 'Keller High School',
      classYear: 2027,
      city: 'Keller',
      state: 'TX',
      seasonStats: [
        { season: 'Sophomore', touchdowns: 5 },
        { season: 'Junior', touchdowns: 8 },
      ],
    },
    {
      maxprepsAthleteId: 'mock-3',
      name: `${firstName} ${lastName}`,
      position: 'Safety',
      school: 'Southlake Carroll',
      classYear: 2026,
      city: 'Southlake',
      state: 'TX',
      seasonStats: [
        { season: 'Junior', tackles: 39, interceptions: 2, passBreakups: 9 },
      ],
    },
  ]
}

export async function GET(request: NextRequest) {
  const q = request.nextUrl.searchParams.get('q')?.trim() || ''

  if (!q) {
    return NextResponse.json({ error: 'Query parameter `q` is required.' }, { status: 400 })
  }

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

  try {
    const res = await fetch(`${backendUrl}/api/maxpreps/search?q=${encodeURIComponent(q)}`, {
      method: 'GET',
      headers: { Accept: 'application/json' },
      cache: 'no-store',
    })

    if (!res.ok) {
      throw new Error(`Backend search returned ${res.status}`)
    }

    const data = await res.json()
    const results = Array.isArray(data?.results)
      ? data.results
      : Array.isArray(data?.athletes)
        ? data.athletes
        : Array.isArray(data)
          ? data
          : []

    return NextResponse.json({ results })
  } catch {
    return NextResponse.json({ results: buildMockResults(q), fallback: true })
  }
}
