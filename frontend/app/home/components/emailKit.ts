// Pure helpers for the coach email kit (no React, no imports): the mailto link and the
// "What's in your note" checklist. SPARQ never sends; the athlete sends from her own email.

// One plain address only: no commas, semicolons, %, ?, & or line breaks (mailto header tricks).
export const PLAIN_EMAIL = /^[A-Za-z0-9._+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$/
export function plainEmail(value: string | null | undefined): string {
  const text = (value || '').trim()
  return text.length <= 254 && PLAIN_EMAIL.test(text) ? text : ''
}

// cc is added only when given (the "CC my parent" toggle is on) and is one plain address.
export function mailtoURL({ to, cc, subject, body }: { to: string; cc?: string | null; subject: string; body: string }): string {
  const params = [`subject=${encodeURIComponent(subject)}`, `body=${encodeURIComponent(body)}`]
  const copy = cc ? plainEmail(cc) : ''
  if (copy) params.unshift(`cc=${encodeURIComponent(copy)}`)
  return `mailto:${plainEmail(to)}?${params.join('&')}`
}

// Some mail apps and browsers cut or refuse mailto links past about 2000 characters.
export const MAILTO_LIMIT = 2000
// The link "Open in my email" uses: the whole note when it fits, else To, CC and subject only
// (she pastes the note after Copy). `long` tells the page to make Copy the main button.
export function openLink(fields: { to: string; cc?: string | null; subject: string; body: string }): { href: string; long: boolean } {
  const full = mailtoURL(fields)
  return full.length <= MAILTO_LIMIT ? { href: full, long: false } : { href: mailtoURL({ ...fields, body: '' }), long: true }
}

// What the server added to the note (stored with the draft). Null for drafts from before this kit.
export interface NoteKit {
  grad_year: number | null; position: string | null; hometown: string | null
  highlight_url: string | null; highlight_reel: boolean; profile_url: string | null; drills: string[]
}
export interface CheckItem { label: string; done: boolean }

// Each line is checked against the text she will send now, so an edit that removes a link unticks it.
export function noteChecklist(text: string, kit: NoteKit | null, cc: string): CheckItem[] {
  const has = (value: string | number | null | undefined) => value !== null && value !== undefined && value !== '' && text.includes(String(value))
  const facts = ([['Grad year', kit?.grad_year], ['position', kit?.position], ['hometown', kit?.hometown]] as const).filter(([, v]) => v)
  return [
    facts.length ? { label: facts.map(([name]) => name).join(', ').replace(/^./, c => c.toUpperCase()), done: facts.every(([, v]) => has(v)) }
      : { label: 'Grad year, position, hometown (add them on GMTM)', done: false },
    kit?.highlight_url ? { label: kit.highlight_reel ? 'Your highlight reel link' : 'Your video link', done: has(kit.highlight_url) }
      : { label: 'Your highlight video (none public on GMTM yet)', done: false },
    kit?.profile_url ? { label: 'Your GMTM profile link', done: has(kit.profile_url) } : { label: 'Your GMTM profile link', done: false },
    kit?.drills.length ? { label: `Your best ${kit.drills.length === 1 ? 'combine number' : `${kit.drills.length} combine numbers`}`, done: kit.drills.every(has) }
      : { label: 'Your combine numbers (none on GMTM yet)', done: false },
    { label: 'Your parent in CC', done: !!plainEmail(cc) },
  ]
}
