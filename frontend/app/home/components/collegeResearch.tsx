'use client'

// "Team now" and "Camps" for one saved college: program-level public facts from the college's own site,
// each with its source link and checked date. Counts only, as listed. Never "open spots", "need" or "leave".
import { useEffect, useState } from 'react'
import { apiFetch, BACKEND_URL } from '@/app/_lib/api'
import { campLink, checkedLabel, costLabel, hostOf, https, isOld, positionLine, teamSentence, type Research } from './collegeResearchText'
export type { Research } from './collegeResearchText'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-jr-lime'
const textLink = `inline-flex min-h-11 items-center text-sm text-jr-lime underline underline-offset-4 hover:text-jr-lime-hover ${focus}`

function Source({ url, checked }: { url: string | null; checked: string | null }) {
  const href = https(url)
  const day = checkedLabel(checked)
  if (!href || !day) return null
  return <p className="text-xs text-jr-dim">
    Checked {day} from <a href={href} target="_blank" rel="noopener noreferrer" className={`inline-flex min-h-11 items-center underline underline-offset-4 ${focus}`}>{hostOf(href)}<span className="sr-only"> (opens in a new tab)</span></a>.
    {isOld(checked) && ' May be out of date.'}
  </p>
}

// Refetches when she saves the college on this page, so the cards appear without a reload.
export function useCollegeResearch(userId: string | undefined, programId: string, saved: boolean) {
  const [research, setResearch] = useState<Research | null | undefined>(undefined)
  useEffect(() => {
    if (!userId || !saved) return
    let live = true
    apiFetch(`${BACKEND_URL}/api/workspace/college-research/${encodeURIComponent(userId)}`)
      .then(r => (r.ok ? r.json() : null))
      .then(body => { if (live) setResearch((body?.programs || []).find((p: Research) => p?.program_id === programId) || null) },
        () => { if (live) setResearch(null) })
    return () => { live = false }
  }, [userId, programId, saved])
  return research
}

// Shown only for a saved college (research exists only for saved ones). Missing data says so plainly.
export function CollegeResearchCards({ research, school }: { research: Research; school: string }) {
  const roster = research.roster
  const line = roster ? positionLine(roster) : null
  return <>
    <div className="flex flex-col gap-2.5 rounded-[20px] border border-jr-line bg-jr-card p-5">
      <h2 className="text-lg font-bold">Team now</h2>
      {roster ? <>
        <p className="text-[15px] leading-normal text-[#D4D4DA]">{teamSentence(roster)}</p>
        {line && <p className="text-sm text-jr-muted">{line}</p>}
        <Source url={roster.source_url} checked={research.roster_checked} />
      </> : <p className="text-[15px] text-jr-soft">{research.camps_checked ? `We could not find a roster on ${school}'s site.` : 'We have not checked this college yet.'}</p>}
    </div>
    <div className="flex flex-col gap-2.5 rounded-[20px] border border-jr-line bg-jr-card p-5">
      <h2 className="text-lg font-bold">Flag football camps</h2>
      {research.camps.length ? <ul className="flex flex-col gap-3">
        {research.camps.map(camp => {
          const link = campLink(camp)
          return <li key={`${camp.name}-${camp.start_date}`} className="flex flex-col gap-1">
            <span className="text-[15px] font-semibold text-jr-text">{camp.name}</span>
            <span className="text-sm text-jr-muted">{camp.date_text}{camp.location ? ` · ${camp.location}` : ''} · {costLabel(camp.cost_usd)}</span>
            {camp.eligibility_text && <span className="text-sm text-jr-muted">From the college&apos;s page: “{camp.eligibility_text}”</span>}
            {link && <a href={link.href} target="_blank" rel="noopener noreferrer" className={textLink}>{link.label}<span className="sr-only"> (opens in a new tab)</span></a>}
          </li>
        })}
      </ul> : <p className="text-[15px] text-jr-soft">{research.camps_checked ? `We could not find flag football camps on ${school}'s site.` : 'We have not checked this college for camps yet.'}</p>}
      {research.camps.map(c => c.source_url).filter((url, i, all) => all.indexOf(url) === i).map(url => <Source key={url} url={url} checked={research.camps_checked} />)}
      <p className="text-xs text-jr-dim">SPARQ never signs you up. Ask a parent before you register.</p>
    </div>
  </>
}
