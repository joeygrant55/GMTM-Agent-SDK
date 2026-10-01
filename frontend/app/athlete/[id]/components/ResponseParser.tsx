'use client'

import {
  CollegeMatchCard,
  CampCard,
  EmailPreviewCard,
  StatCard,
  ActionButtons,
  type CollegeMatchData,
  type CampData,
  type EmailPreviewData,
  type StatData,
  type ActionOption,
} from './ResponseCards'
import SafeMarkdown from '@/components/SafeMarkdown'

/* ═══════════════════════════════════════════════
   Types
   ═══════════════════════════════════════════════ */

type Segment =
  | { type: 'text'; content: string }
  | { type: 'colleges'; data: CollegeMatchData[] }
  | { type: 'camp'; data: CampData }
  | { type: 'email'; data: EmailPreviewData }
  | { type: 'stats'; data: StatData[] }
  | { type: 'actions'; data: ActionOption[] }

interface ResponseParserProps {
  content: string
  onAction: (text: string) => void
  formatFallback?: (text: string) => string
}

/* ═══════════════════════════════════════════════
   Detection helpers
   ═══════════════════════════════════════════════ */

// College match: "School Name (94%)" or "School Name — 94% match" or "Match Score: 94%"
const COLLEGE_MATCH_RE =
  /(?:^|\n).*?([A-Z][A-Za-z&' .-]{2,40})\s*(?:\((\d{1,3})%\)|[-—–]\s*(\d{1,3})%\s*match|Match\s*(?:Score)?[:\s]*(\d{1,3})%)/gm

function extractColleges(text: string): { colleges: CollegeMatchData[]; remaining: string } | null {
  const matches: CollegeMatchData[] = []
  const matchedLines = new Set<string>()

  // Reset regex
  COLLEGE_MATCH_RE.lastIndex = 0
  let m
  while ((m = COLLEGE_MATCH_RE.exec(text)) !== null) {
    const school = m[1].trim()
    const pct = parseInt(m[2] || m[3] || m[4], 10)
    if (pct > 0 && pct <= 100 && school.length > 2) {
      // Grab context lines around the match for details
      const matchLine = m[0].trim()
      matchedLines.add(matchLine)

      // Look for bullet details following this match
      const afterIdx = (m.index ?? 0) + m[0].length
      const after = text.slice(afterIdx, afterIdx + 500)
      const detailLines: string[] = []
      for (const line of after.split('\n')) {
        const t = line.trim()
        if (t.startsWith('- ') || t.startsWith('• ') || t.startsWith('* ')) {
          detailLines.push(t.replace(/^[-•*]\s*/, ''))
          matchedLines.add(t)
        } else if (t === '' && detailLines.length > 0) {
          break
        } else if (detailLines.length > 0) {
          break
        }
      }

      matches.push({ school, matchPercent: pct, details: detailLines.slice(0, 3) })
    }
  }

  if (matches.length === 0) return null

  // Remove matched content from text
  let remaining = text
  for (const line of Array.from(matchedLines)) {
    remaining = remaining.replace(line, '')
  }
  remaining = remaining.replace(/\n{3,}/g, '\n\n').trim()

  return { colleges: matches, remaining }
}

// Email detection
function extractEmail(text: string): { email: EmailPreviewData; remaining: string } | null {
  // Look for Subject: line
  const subjectMatch = text.match(/Subject:\s*(.+)/i)
  if (!subjectMatch) return null

  // Look for "Dear Coach" or "To: Coach"
  const toMatch = text.match(/(?:To:\s*|Dear\s+)(Coach\s+[A-Za-z.]+|[A-Za-z.]+@[^\s,]+)/i)
  const to = toMatch ? toMatch[1] : 'Coach'

  const subject = subjectMatch[1].trim()

  // Extract body: everything after "Subject:" line (or after "Dear...")
  const subjectIdx = text.indexOf(subjectMatch[0])
  let bodyStart = subjectIdx + subjectMatch[0].length
  const dearMatch = text.indexOf('Dear ', bodyStart)
  if (dearMatch !== -1 && dearMatch < bodyStart + 100) {
    bodyStart = dearMatch
  } else {
    // Skip to next line
    const nl = text.indexOf('\n', bodyStart)
    if (nl !== -1) bodyStart = nl + 1
  }

  const body = text.slice(bodyStart).trim()

  // Check if there's meaningful email content
  if (body.length < 20) return null

  return {
    email: { to, subject, body },
    remaining: text.slice(0, Math.max(0, subjectIdx)).trim(),
  }
}

// Camp detection
const CAMP_RE =
  /(?:camp|combine|showcase|clinic|prospect\s*day)/i

function extractCamps(text: string): { camps: CampData[]; remaining: string } | null {
  if (!CAMP_RE.test(text)) return null

  const camps: CampData[] = []
  const lines = text.split('\n')
  const consumedIndices = new Set<number>()

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i].trim()
    if (!CAMP_RE.test(line)) continue

    // This line mentions a camp — try to extract info
    const name = line.replace(/^[-•*\d.)\s]+/, '').replace(/\*\*/g, '').trim()
    if (name.length < 5) continue

    const camp: CampData = { name }
    consumedIndices.add(i)

    // Look at next few lines for date/location/cost
    for (let j = i + 1; j < Math.min(i + 5, lines.length); j++) {
      const sub = lines[j].trim()
      if (sub === '') break

      const dateMatch = sub.match(
        /(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2}(?:[-–]\d{1,2})?(?:,?\s*\d{4})?/i
      )
      if (dateMatch) {
        camp.date = dateMatch[0]
        consumedIndices.add(j)
        continue
      }

      const costMatch = sub.match(/\$[\d,.]+/)
      if (costMatch) {
        camp.cost = costMatch[0]
        consumedIndices.add(j)
        continue
      }

      // Location heuristic: mentions a state abbreviation or city-like pattern
      if (/[A-Z]{2}|,\s*[A-Z]/.test(sub) && sub.length < 60) {
        camp.location = sub.replace(/^[-•*]\s*/, '').replace(/📍\s*/, '')
        consumedIndices.add(j)
      }
    }

    camps.push(camp)
  }

  if (camps.length === 0) return null

  const remaining = lines
    .filter((_, i) => !consumedIndices.has(i))
    .join('\n')
    .replace(/\n{3,}/g, '\n\n')
    .trim()

  return { camps, remaining }
}

// Stat detection
const STAT_PATTERNS = [
  /(\d+\.?\d*)\s*(second|sec|s)?\s*(40(?:-yard)?(?:\s*dash)?)/i,
  /(\d+\.?\d*)\s*(mph|miles?\s*per\s*hour)\s*(shuttle|speed|velocity)?/i,
  /(\d+)\s*(inch|in|"|')\s*(vertical|vert|broad\s*jump|wingspan)?/i,
  /(\d+)\s*(tackles?|sacks?|interceptions?|ints?|TDs?|touchdowns?|receptions?|yards?|completions?)/i,
  /(\d+\.?\d*)\s*(GPA)/i,
  /(\d+)\s*(lbs?|pounds?|kg)/i,
  /(\d+['′]\d+["″]?)\s*(height|tall)?/i,
]

function extractStats(text: string): StatData[] | null {
  const stats: StatData[] = []
  const seen = new Set<string>()

  for (const pattern of STAT_PATTERNS) {
    const matches = Array.from(text.matchAll(new RegExp(pattern, 'gi')))
    for (const m of matches) {
      const value = m[1]
      const unit = (m[2] || '').trim()
      const metric = (m[3] || m[2] || '').trim()
      const key = `${value}${unit}`
      if (seen.has(key)) continue
      seen.add(key)

      // Try to find comparison text near this stat
      const idx = m.index ?? 0
      const context = text.slice(idx, idx + 200)
      const compMatch = context.match(
        /(?:top|bottom)\s+\d+%|(?:above|below)\s+average|(?:elite|good|average|needs?\s+(?:work|improvement))/i
      )

      let rating: StatData['rating'] = 'average'
      if (compMatch) {
        const c = compMatch[0].toLowerCase()
        if (/top\s+(?:[1-2]?\d)%|elite|above/.test(c)) rating = 'good'
        else if (/bottom|below|needs/.test(c)) rating = 'needs-work'
      }

      stats.push({
        metric: metric || unit,
        value: `${value}${unit ? ' ' + unit : ''}`,
        comparison: compMatch?.[0],
        rating,
      })
    }
  }

  return stats.length >= 2 ? stats.slice(0, 6) : null
}

// Action options: numbered list at end
function extractActions(text: string): { options: ActionOption[]; remaining: string } | null {
  // Look for pattern like "Want me to:" or "I can:" followed by numbered list
  const triggerRe = /(?:want\s+me\s+to|i\s+can|options?|would\s+you\s+like\s+me\s+to|here(?:'s| are)\s+(?:what|your)\s+options?)[:\s]*\n/i
  const triggerMatch = text.match(triggerRe)

  // Also check for just numbered list at the very end
  const lines = text.trimEnd().split('\n')
  const options: ActionOption[] = []
  let startIdx = lines.length

  // Scan from end backwards for numbered items
  for (let i = lines.length - 1; i >= Math.max(0, lines.length - 10); i--) {
    const line = lines[i].trim()
    const numMatch = line.match(/^(\d+)[.)]\s+(.+)/)
    if (numMatch) {
      options.unshift({
        number: parseInt(numMatch[1], 10),
        text: numMatch[2].replace(/\*\*/g, '').trim(),
      })
      startIdx = i
    } else if (options.length > 0) {
      // Hit non-numbered line while we already found some — check if it's the trigger
      if (triggerRe.test(line)) {
        startIdx = i
      }
      break
    }
  }

  if (options.length < 2) return null

  const remaining = lines.slice(0, startIdx).join('\n').trim()
  return { options, remaining }
}

/* ═══════════════════════════════════════════════
   Main Parser
   ═══════════════════════════════════════════════ */

function parseContent(content: string): Segment[] {
  const segments: Segment[] = []
  let text = content

  // 1. Extract action options from end first
  const actionResult = extractActions(text)
  let trailingActions: ActionOption[] | null = null
  if (actionResult) {
    trailingActions = actionResult.options
    text = actionResult.remaining
  }

  // 2. Try email detection (takes priority — it's a distinct format)
  const emailResult = extractEmail(text)
  if (emailResult) {
    if (emailResult.remaining) {
      segments.push({ type: 'text', content: emailResult.remaining })
    }
    segments.push({ type: 'email', data: emailResult.email })
    if (trailingActions) {
      segments.push({ type: 'actions', data: trailingActions })
    }
    return segments
  }

  // 3. Try college match detection
  const collegeResult = extractColleges(text)
  if (collegeResult && collegeResult.colleges.length > 0) {
    if (collegeResult.remaining) {
      // Check for camps in remaining text
      const campResult = extractCamps(collegeResult.remaining)
      if (campResult) {
        if (campResult.remaining) segments.push({ type: 'text', content: campResult.remaining })
        campResult.camps.forEach((c) => segments.push({ type: 'camp', data: c }))
      } else {
        segments.push({ type: 'text', content: collegeResult.remaining })
      }
    }
    segments.push({ type: 'colleges', data: collegeResult.colleges })
    if (trailingActions) {
      segments.push({ type: 'actions', data: trailingActions })
    }
    return segments
  }

  // 4. Try camp detection
  const campResult = extractCamps(text)
  if (campResult) {
    if (campResult.remaining) segments.push({ type: 'text', content: campResult.remaining })
    campResult.camps.forEach((c) => segments.push({ type: 'camp', data: c }))
    if (trailingActions) {
      segments.push({ type: 'actions', data: trailingActions })
    }
    return segments
  }

  // 5. Try stat detection (don't remove from text, just add stat cards below)
  const statResult = extractStats(text)
  if (statResult) {
    segments.push({ type: 'text', content: text })
    segments.push({ type: 'stats', data: statResult })
    if (trailingActions) {
      segments.push({ type: 'actions', data: trailingActions })
    }
    return segments
  }

  // 6. Fallback: plain text
  segments.push({ type: 'text', content: text })
  if (trailingActions) {
    segments.push({ type: 'actions', data: trailingActions })
  }

  return segments
}

/* ═══════════════════════════════════════════════
   ResponseParser Component
   ═══════════════════════════════════════════════ */

export default function ResponseParser({ content, onAction }: ResponseParserProps) {
  const segments = parseContent(content)

  return (
    <div className="space-y-3">
      {segments.map((seg, i) => {
        switch (seg.type) {
          case 'text':
            return (
              <div key={i} className="text-sm leading-relaxed">
                <SafeMarkdown content={seg.content} />
              </div>
            )

          case 'colleges':
            return (
              <div key={i} className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">College Matches</span>
                  <span className="text-[#c8ff00] text-xs font-bold">{seg.data.length} matches</span>
                </div>
                {seg.data.map((college, cidx) => (
                  <CollegeMatchCard key={cidx} data={college} index={cidx} />
                ))}
              </div>
            )

          case 'camp':
            return <CampCard key={i} data={seg.data} />

          case 'email':
            return <EmailPreviewCard key={i} data={seg.data} />

          case 'stats':
            return (
              <div key={i} className="grid grid-cols-2 gap-2">
                {seg.data.map((stat, sidx) => (
                  <StatCard key={sidx} data={stat} />
                ))}
              </div>
            )

          case 'actions':
            return <ActionButtons key={i} options={seg.data} onAction={onAction} />

          default:
            return null
        }
      })}
    </div>
  )
}
