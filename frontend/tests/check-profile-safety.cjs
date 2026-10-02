// Profile-surface (sparq.gmtm.com) safety: no raw-HTML renderers, nonce CSP without
// script 'unsafe-inline', GMTM sessionId stripped, public minor pages denied, no send button.
// Pure source/policy checks; no server or network. Run: node frontend/tests/check-profile-safety.cjs
// The rendered-page nonce check lives in check-production-build.cjs (SPARQ_BUILD_SURFACE=profile).
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const policy = require('../lib/backend-config.cjs')

const root = path.resolve(__dirname, '..')
const checks = []
const check = (name, fn) => { fn(); checks.push(name) }

function sources(dir) {
  return fs.readdirSync(dir, { withFileTypes: true }).flatMap(entry => {
    const file = path.join(dir, entry.name)
    if (entry.isDirectory()) return sources(file)
    return /\.(?:[cm]?[jt]sx?)$/.test(entry.name) ? [file] : []
  })
}

check('No raw-HTML rendering anywhere in app, components, lib or middleware', () => {
  const files = [...sources(path.join(root, 'app')), ...sources(path.join(root, 'components')), ...sources(path.join(root, 'lib')), path.join(root, 'middleware.ts')]
  assert.ok(files.length > 50)
  const offenders = files.filter(file => /dangerouslySetInnerHTML|\.innerHTML\b|outerHTML|insertAdjacentHTML|rehype-raw/.test(fs.readFileSync(file, 'utf8')))
  assert.deepEqual(offenders.map(file => path.relative(root, file)), [])
})

check('SafeMarkdown links open with noopener noreferrer', () => {
  const source = fs.readFileSync(path.join(root, 'components/SafeMarkdown.tsx'), 'utf8')
  assert.match(source, /rel="noopener noreferrer"/)
})

check('SafeMarkdown drops images, renders tables, links only https', () => {
  const source = fs.readFileSync(path.join(root, 'components/SafeMarkdown.tsx'), 'utf8')
  assert.match(source, /disallowedElements=\{\['img'\]\}/)
  assert.match(source, /remarkPlugins=\{\[remarkGfm\]\}/)
  assert.match(source, /href\.startsWith\('https:\/\/'\)/)
})

check('Outreach mailto takes one plain address; profile surface is copy-only', () => {
  const source = fs.readFileSync(path.join(root, 'app/home/components/ArtifactViewer.tsx'), 'utf8')
  const m = source.match(/\/\^\[A-Za-z0-9\._\+-\]\+@\[A-Za-z0-9-\]\+\(\\\.\[A-Za-z0-9-\]\+\)\+\$\//)
  assert.ok(m, 'strict address regex present')
  const re = new RegExp(m[0].slice(1, -1))
  for (const ok of ['coach@school.edu', 'a.b+c@x-y.org']) assert.ok(re.test(ok), ok)
  for (const bad of ['a@x.edu,b@y.com', 'a@x.edu;b@y.com', 'a%0D%0ABcc:x@y.com@x.edu', 'a@x', 'a b@x.edu']) assert.ok(!re.test(bad), bad)
  assert.match(source, /artifact\.type === 'outreach_draft' && copyOnly/)
  assert.match(source, /isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)/)
})

const nonce = 'c3ludGhldGljLW5vbmNlLXZhbHVl'
check('Production CSP: nonce + strict-dynamic, no script unsafe-inline, no third-party sign-in host, self-only connect', () => {
  const csp = policy.profileContentSecurityPolicy({ nonce })
  const directive = name => csp.split('; ').find(part => part.startsWith(name + ' ')) || ''
  const script = directive('script-src')
  assert.ok(script.includes(`'nonce-${nonce}'`) && script.includes("'strict-dynamic'"))
  assert.ok(!script.includes("'unsafe-inline'") && !script.includes("'unsafe-eval'"))
  assert.ok(!/challenges\.cloudflare|accounts\./i.test(csp), 'no sign-in or Turnstile host')
  assert.equal(directive('connect-src'), "connect-src 'self'")
  for (const part of ["object-src 'none'", "base-uri 'self'", "frame-ancestors 'none'", "default-src 'self'"]) assert.ok(csp.includes(part), part)
})

check('Dev CSP adds only unsafe-eval (Next dev runtime), still no script unsafe-inline', () => {
  const script = policy.profileContentSecurityPolicy({ nonce, dev: true }).split('; ').find(part => part.startsWith('script-src '))
  assert.ok(script.includes("'unsafe-eval'") && !script.includes("'unsafe-inline'"))
})

check('CSP refuses a missing or weak nonce; legacy connect adds only the canonical backend origin', () => {
  for (const bad of [undefined, '', 'short', "x' 'unsafe-inline"]) assert.throws(() => policy.profileContentSecurityPolicy({ nonce: bad }))
  const csp = policy.profileContentSecurityPolicy({ nonce, connect: 'https://backend.example' })
  assert.ok(csp.includes("connect-src 'self' https://backend.example;"))
  assert.throws(() => policy.profileContentSecurityPolicy({ nonce, connect: "https://x.example 'unsafe-eval'" }))
})

check('GMTM sessionId is removed from the forwarded Cookie header; other cookies stay', () => {
  assert.equal(policy.withoutGmtmSession('sessionId=abc; __session=jwt; other=1'), '__session=jwt; other=1')
  assert.equal(policy.withoutGmtmSession(' sessionId=abc '), '')
  assert.equal(policy.withoutGmtmSession('mysessionId=1; sessionIdx=2'), 'mysessionId=1; sessionIdx=2')
  assert.equal(policy.withoutGmtmSession(undefined), '')
})

check('Profile middleware applies the CSP + cookie filter to every response; GMTM sessionId only hashed', () => {
  const source = fs.readFileSync(path.join(root, 'middleware.ts'), 'utf8')
  assert.match(source, /return sessionMiddleware\(request, policy === 'page' && !/)
  assert.match(source, /return sessionResponse\(request, gsh\)/)
  assert.match(source, /withoutGmtmSession\(headers\.get\('cookie'\)\)/)
  assert.match(source, /response\.headers\.set\('Content-Security-Policy', csp\)/)
  // The raw value is read only inside gmtmSessionHash (sha256); nothing else names it.
  assert.ok(!/sessionId/.test(source.replace(/\/\/.*$/gm, '').replace(/withoutGmtmSession|gmtmSessionHash/g, '')))
  const helper = fs.readFileSync(path.join(root, 'lib/sparq-session.cjs'), 'utf8')
  assert.match(helper, /=== 'sessionId'\) \{\s*const value = part\.slice\(at \+ 1\)\.trim\(\)\s*return value \? sha256Hex\(value\) : null/)
  assert.ok(!/console\./.test(helper + source))
  // Per-request render on every surface so Next's scripts carry the nonce.
  assert.match(fs.readFileSync(path.join(root, 'app/layout.tsx'), 'utf8'), /headers\(\)\s*return \(/)
})

check('Public athlete pages, share reports and athlete-by-id API are denied on the profile surface', () => {
  for (const page of ['/athlete/123', '/athlete/123/report', '/report/token', '/report/token/x']) assert.equal(policy.candidatePagePolicy(page, 'GET', 'profile'), 'deny', page)
  for (const api of ['/api/athlete/123', '/api/reports/public/token', '/api/artifacts/1/approve']) {
    assert.equal(policy.candidateAPIAllowed(api, 'GET', '', 'profile'), false, api)
    assert.equal(policy.candidateAPIAllowed(api, 'POST', '', 'profile'), false, api)
  }
})

check('Outreach UI on the profile surface offers Copy and Open in my email (Approve & Send only off-profile)', () => {
  const source = fs.readFileSync(path.join(root, 'app/home/components/ArtifactViewer.tsx'), 'utf8')
  assert.ok(!source.includes('athlete_email'))
  // The send button exists only in the non-copyOnly branch; the backend also refuses to send on profile.
  const copyBranch = source.indexOf("artifact.type === 'outreach_draft' && copyOnly ? (")
  const sendLabel = source.indexOf('Approve & Send')
  assert.ok(copyBranch > 0 && sendLabel > copyBranch, 'Approve & Send must sit after the copy-only branch')
  assert.match(source, /mailto:\$\{to\}\?subject=\$\{encodeURIComponent\(subject\)\}&body=\$\{encodeURIComponent\(body\)\}/)
  assert.match(source, /Open in my email/)
})

check('Junior colleges: copy or open in my email only, strict mailto, https-only links, no fit score', () => {
  const source = fs.readFileSync(path.join(root, 'app/home/components/ProfileColleges.tsx'), 'utf8')
  assert.match(fs.readFileSync(path.join(root, 'app/home/components/emailKit.ts'), 'utf8'), /\/\^\[A-Za-z0-9\._\+-\]\+@\[A-Za-z0-9-\]\+\(\\\.\[A-Za-z0-9-\]\+\)\+\$\//)
  assert.match(source, /const open = draft \? openLink\(\{ to, cc: ccAddress, subject: draft\.subject, body: draft\.body \}\) : null/)
  assert.match(source, /<a href=\{open\.href\}/)
  assert.ok(!/mailto:/.test(source), 'the only mailto builder is emailKit.mailtoURL')
  assert.match(source, /url\.startsWith\('https:\/\/'\)/)
  assert.match(source, /Open in my email/)
  assert.ok(!/fit_score|approve|Send<|sendgrid/i.test(source))
})

check('Junior pilot: no Opportunities, Ask SPARQ or summary/introduction drafting on the profile surface', () => {
  const dir = path.join(root, 'app/home/components')
  for (const gone of ['AthleteOpportunities.tsx', 'opportunityEvidence.ts', 'opportunityEngagement.ts', 'AthleteDebriefPanel.tsx', 'athleteDebrief.ts', 'AthleteShowcase.tsx']) assert.ok(!fs.existsSync(path.join(dir, gone)), gone)
  const ui = ['ProfileWorkspace.tsx', 'ProfileWorkspaceShell.tsx', 'AthleteCareerHome.tsx', 'ProfileMaterialsPanel.tsx'].map(name => fs.readFileSync(path.join(dir, name), 'utf8')).join('\n')
  for (const text of ['Opportunities', 'Ask SPARQ', 'Make it yours', 'Rebuild', 'Save draft', 'Remove saved draft', 'Write an introduction', '/api/athlete/debrief', '/api/athlete/opportunities']) assert.ok(!ui.includes(text), text)
  for (const text of ['Playback has not been checked', 'No supported numeric', 'verification is unconfirmed', 'View only; this record']) assert.ok(!ui.includes(text), text)
  for (const route of ['/api/athlete/debrief', '/api/athlete/opportunities', '/api/athlete/opportunities/engagement']) assert.equal(policy.candidateAPIAllowed(route, 'POST', '', 'profile'), false, route)
})

check('Not you? Switch signs out of GMTM; Back to GMTM stays on gmtm.com', () => {
  const gate = fs.readFileSync(path.join(root, 'app/home/components/ParentNoticeGate.tsx'), 'utf8')
  assert.match(gate, /GMTM_SIGN_OUT_URL = `\$\{GMTM_URL\.replace\(\/\\\/\+\$\/, ''\)\}\/sign-out`/)
  assert.match(gate, /<a href=\{GMTM_SIGN_OUT_URL\}[^>]*>Not you\? Switch<\/a>/)
  assert.match(fs.readFileSync(path.join(root, 'app/home/components/ProfileWorkspaceShell.tsx'), 'utf8'), /href="https:\/\/gmtm\.com"[^>]*>Back to GMTM/)
})

check('Coach email: a new draft asks before replacing edits; Copy is off while writing', () => {
  const source = fs.readFileSync(path.join(root, 'app/home/components/ProfileColleges.tsx'), 'utf8')
  assert.match(source, /if \(edited && !replace\) \{ setConfirmReplace\(true\); return \}/)
  assert.match(source, /Replace your edits\?/)
  assert.match(source, /onClick=\{\(\) => void copy\(\)\} disabled=\{busy \|\| !draft\}/)
  assert.match(source.slice(source.indexOf('export function ProfileCollegeDetail(')), /<HeartButton program=\{program\}/)
})

check('Drill results: GMTM spellings share one key; height and weight are hidden everywhere on the profile', () => {
  const ts = require(path.join(process.env.SPARQ_TEST_NODE_MODULES || path.join(root, 'node_modules'), 'typescript'))
  const module = { exports: {} }
  new Function('exports', 'module', ts.transpileModule(fs.readFileSync(path.join(root, 'app/home/components/profileEvidence.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText)(module.exports, module)
  const { drillKey, isBodySize } = module.exports
  for (const [a, b] of [['5-10-5 Shuttle', '5-10-5 Shuttle Run'], ['Push-Ups', 'Max. Push-Ups'], ['Sit-Ups', 'Max. Sit Ups'], ['20-Yard Dash', '20 yard dash'], ['Standing Broad Jump', 'standing broad jump']]) assert.equal(drillKey(a), drillKey(b), a)
  assert.notEqual(drillKey('20-Yard Dash'), drillKey('60-Yard Shuttle'))
  for (const label of ['Height', ' weight ', 'Max. Weight']) assert.ok(isBodySize(label), label)
  assert.ok(!isBodySize('Standing Broad Jump'))
  const dir = path.join(root, 'app/home/components')
  for (const name of ['AthleteCareerHome.tsx', 'ProfileMaterialsPanel.tsx']) assert.match(fs.readFileSync(path.join(dir, name), 'utf8'), /isBodySize\(item\.(label|title)\)/, name)
  assert.match(fs.readFileSync(path.join(dir, 'AthleteCareerHome.tsx'), 'utf8'), /const key = drillKey\(item\.label\)/)
  // Home and My card both read drills through the one filtered helper.
  assert.match(fs.readFileSync(path.join(dir, 'ProfileWorkspace.tsx'), 'utf8'), /const results = drillResults\(profile, materials\.snapshot\)/)
})

const transpile = file => {
  const ts = require(path.join(process.env.SPARQ_TEST_NODE_MODULES || path.join(root, 'node_modules'), 'typescript'))
  const module = { exports: {} }
  // Sibling pure modules only (e.g. cardPicker -> ./profileMaterials).
  const local = id => { if (!/^\.\/[A-Za-z]+$/.test(id)) throw Error('unexpected import ' + id); return transpile(path.join(path.dirname(file), id + '.ts')) }
  new Function('exports', 'module', 'require', ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText)(module.exports, module, local)
  return module.exports
}

check('Journey: 4 steps from real data, save target 3, headline counts steps left to the first email', () => {
  const { journey, SAVE_TARGET } = transpile('app/home/components/journey.ts')
  assert.equal(SAVE_TARGET, 3)
  const empty = journey({ profileReady: false, found: 0, saved: 0, sent: 0 })
  assert.deepEqual([empty.done, empty.left, empty.current.key, empty.percent], [0, 4, 'profile', 0])
  assert.equal(empty.headline, 'You’re 4 steps from your first coach email.')
  const mid = journey({ profileReady: true, found: 12, saved: 2, sent: 0 })
  assert.deepEqual([mid.done, mid.left, mid.current.key, mid.percent, mid.steps[1].title, mid.steps[2].detail], [2, 2, 'save', 50, '12 colleges found', '2 of 3 saved'])
  const last = journey({ profileReady: true, found: 12, saved: 3, sent: 0 })
  assert.deepEqual([last.left, last.current.key, last.headline], [1, 'email', 'You’re 1 step from your first coach email.'])
  const done = journey({ profileReady: true, found: 12, saved: 5, sent: 1 })
  assert.deepEqual([done.done, done.left, done.current, done.percent, done.headline], [4, 0, null, 100, 'You emailed your first coach.'])
})

check('School badges: initials, neutral fallback, every stored school color gives >= 4.5:1 text (small 14px badge)', () => {
  const { badgeColors, initials, contrast } = transpile('app/home/components/journey.ts')
  assert.deepEqual(['Daytona State College', 'Edward Waters University', 'University of Saint Mary', 'Texas A&M University-Kingsville'].map(initials), ['DS', 'EW', 'US', 'TA'])
  assert.deepEqual(badgeColors(null), { background: '#26262C', color: '#F4F4F5' })
  assert.deepEqual(badgeColors('red'), { background: '#26262C', color: '#F4F4F5' })
  assert.equal(badgeColors('#1F4E9C').color, '#FFFFFF')
  assert.equal(badgeColors('#CAFD00').color, '#0B0B0C')
  const colors = JSON.parse(fs.readFileSync(path.join(root, '../backend/data/college_womens_flag_2026.json'), 'utf8')).map(p => p.primary_color).filter(Boolean)
  assert.ok(colors.length > 100)
  for (const c of [...colors, '#808080', '#E4002B', '#FF6A00', '#00A3E0', '#7F7F7F']) {
    const b = badgeColors(c)
    assert.ok(contrast(b.background, b.color) >= 4.5, `${c} -> ${b.background}/${b.color}`)
  }
  assert.ok(contrast('#F4F4F5', '#26262C') >= 4.5)
})

check('Map window: fits her city + listed programs, padded, minimum zoom, 8:5 shape, inside the map', () => {
  const { mapWindow, MIN_SPAN } = transpile('app/home/components/journey.ts')
  assert.deepEqual(mapWindow([]), { x: 0, y: 0, w: 100, h: 100 })
  const florida = [{ x: 82, y: 80 }, { x: 83, y: 77 }, { x: 85, y: 85 }, { x: 81, y: 70 }]
  const fl = mapWindow(florida)
  assert.ok(fl.w === fl.h && fl.w >= MIN_SPAN && fl.w < 40, JSON.stringify(fl))
  for (const p of florida) assert.ok(p.x > fl.x && p.x < fl.x + fl.w && p.y > fl.y && p.y < fl.y + fl.h, 'point inside window')
  assert.ok(fl.x + fl.w <= 100 && fl.y + fl.h <= 100 && fl.x >= 0 && fl.y >= 0)
  const one = mapWindow([{ x: 50, y: 50 }])
  assert.equal(one.w, MIN_SPAN)
  assert.equal(mapWindow([{ x: 5, y: 10 }, { x: 95, y: 90 }]).w, 100)
  const tall = [{ x: 80, y: 20 }, { x: 82, y: 85 }]  // Delaware to Florida: a tall, narrow list
  const t = mapWindow(tall)
  for (const p of tall) assert.ok(p.y > t.y && p.y < t.y + t.h, 'tall list fits vertically')
})

check('Pages: /home is the journey; Home, Colleges, Emails, My card (/home/card) tabs; active tab per URL; profile-only', () => {
  const home = fs.readFileSync(path.join(root, 'app/home/page.tsx'), 'utf8')
  assert.match(home, /<ProfileWorkspace view="home" \/>/)
  assert.match(fs.readFileSync(path.join(root, 'app/home/inbox/page.tsx'), 'utf8'), /isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)\) redirect\('\/home'\)/)
  for (const [page, view] of [['progress', 'progress'], ['footage', 'footage'], ['card', 'card']]) {
    const source = fs.readFileSync(path.join(root, `app/home/${page}/page.tsx`), 'utf8')
    assert.match(source, /if \(!isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)\) notFound\(\)/)
    assert.match(source, new RegExp(`<ProfileWorkspace view="${view}" />`))
    assert.equal(policy.candidatePagePolicy(`/home/${page}`, 'GET', 'profile'), 'page')
    assert.equal(policy.candidatePagePolicy(`/home/${page}`, 'GET', 'combine'), 'deny')
  }
  const shell = fs.readFileSync(path.join(root, 'app/home/components/ProfileWorkspaceShell.tsx'), 'utf8')
  for (const [href, label] of [['/home', 'Home'], ['/home/colleges', 'Colleges'], ['/home/emails', 'Emails'], ['/home/card', 'My card']]) assert.ok(shell.includes(`{ href: '${href}', label: '${label}'`), label)
  const emails = fs.readFileSync(path.join(root, 'app/home/emails/page.tsx'), 'utf8')
  assert.match(emails, /if \(!isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)\) notFound\(\)/)
  assert.match(emails, /m\.ProfileEmails/)
  assert.equal(policy.candidatePagePolicy('/home/emails', 'GET', 'profile'), 'page')
  assert.equal(policy.candidatePagePolicy('/home/emails', 'GET', 'combine'), 'deny')
  assert.match(shell, /match: \(path: string\) => path\.startsWith\('\/home\/colleges'\)/)
  assert.match(shell, /md:hidden/)
  assert.match(shell, /aria-current=\{active === tab\.href \? 'page' : undefined\}/)
})

check('No map tile server or third-party geocoder: local SVG map, CSP connect-src stays self', () => {
  const csp = policy.profileContentSecurityPolicy({ nonce })
  assert.equal(csp.split('; ').find(part => part.startsWith('connect-src ')), "connect-src 'self'")
  const hosts = /openstreetmap|tile\.|mapbox|maps\.googleapis|arcgis|nominatim|leaflet|carto/i
  assert.ok(!hosts.test(csp))
  const ui = ['ProfileColleges.tsx', 'AthleteCareerHome.tsx', 'ProfileWorkspace.tsx'].map(n => fs.readFileSync(path.join(root, 'app/home/components', n), 'utf8')).join('\n')
  assert.ok(!hosts.test(ui))
  assert.match(ui, /src="\/us-states\.svg"/)
  const svg = fs.readFileSync(path.join(root, 'public/us-states.svg'), 'utf8')
  assert.ok(svg.startsWith('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 600">') && svg.length < 80000)
  assert.ok(!/<script|href=|https?:\/\/(?!www\.w3\.org\/2000\/svg)/i.test(svg), 'svg has no script or external reference')
  assert.equal(policy.candidatePagePolicy('/us-states.svg', 'GET', 'profile'), 'asset')
})

check('Colleges UI: coach contact only in the email kit, "I sent it" only marks a date, saves are POST {saved}', () => {
  const source = fs.readFileSync(path.join(root, 'app/home/components/ProfileColleges.tsx'), 'utf8')
  const kitAt = source.indexOf('export function ProfileCollegeDetail(')
  const emailsAt = source.indexOf('export function ProfileEmails(')
  assert.ok(kitAt > 0 && emailsAt > kitAt)
  // The list, cards, map and Emails page never read coach fields; only the kit does.
  const kitSection = source.indexOf('// Sourced coach contact (detail route only)')
  assert.ok(kitSection > 0 && kitSection < kitAt)
  for (const part of [source.slice(0, kitSection), source.slice(emailsAt)]) assert.ok(!/coach_email|head_coach|staff_page|\bcoach\.|\.coach\b|\bCoach\b[^ ]/.test(part), 'coach field outside the kit')
  assert.match(source.slice(kitAt, emailsAt), /setTo\(saved\.draft\?\.to_email \|\| d\.coach\.email \|\| ''\)/)
  assert.match(source.slice(kitAt, emailsAt), /disabled=\{busy \|\| !draft\}/)
  assert.match(source, /JSON_POST\(\{ sent \}\)/)
  assert.match(source, /JSON_POST\(\{ saved: next \}\)/)
  assert.match(source, /← Colleges/)
})

check('Email kit mailto: one plain To and CC, cc only when on, header injection dropped', () => {
  const { mailtoURL, plainEmail } = transpile('app/home/components/emailKit.ts')
  const base = { subject: 'Class of 2028 QB', body: 'Hello Coach,\n\nHi & bye?\n\nAvery' }
  const plain = mailtoURL({ to: 'coach@school.edu', ...base })
  assert.equal(plain, 'mailto:coach@school.edu?subject=Class%20of%202028%20QB&body=Hello%20Coach%2C%0A%0AHi%20%26%20bye%3F%0A%0AAvery')
  assert.ok(!plain.includes('cc='))
  assert.ok(!mailtoURL({ to: 'coach@school.edu', cc: '', ...base }).includes('cc='), 'toggle off: no cc')
  assert.equal(mailtoURL({ to: 'coach@school.edu', cc: 'mom@example.com', ...base }), 'mailto:coach@school.edu?cc=mom%40example.com&' + plain.split('?')[1])
  for (const bad of ['a@x.edu,b@y.com', 'a@x.edu;b@y.com', 'a@x.edu?bcc=evil@y.com', 'a@x.edu&bcc=evil@y.com', 'a%0D%0ABcc:x@y.com@x.edu',
    'a@x.edu\r\nBcc: evil@y.com', 'a@x', 'a b@x.edu', 'javascript:alert(1)//@x.edu', 'x'.repeat(250) + '@a.edu']) {
    assert.equal(plainEmail(bad), '', bad)
    const url = mailtoURL({ to: bad, cc: bad, ...base })
    assert.ok(url.startsWith('mailto:?subject=') && !/bcc|cc=|evil/i.test(url), url)
  }
  assert.equal(plainEmail('  coach@school.edu '), 'coach@school.edu')
})

check('Long notes: past 2000 characters Copy leads and Open in my email carries To, CC and subject only', () => {
  const { openLink, MAILTO_LIMIT } = transpile('app/home/components/emailKit.ts')
  assert.equal(MAILTO_LIMIT, 2000)
  const fields = { to: 'coach@school.edu', cc: 'mom@example.com', subject: 'Class of 2028 QB' }
  const short = openLink({ ...fields, body: 'Hello Coach,' })
  assert.ok(!short.long && short.href.includes('body=Hello%20Coach%2C'))
  const long = openLink({ ...fields, body: 'x'.repeat(1990) })
  assert.ok(long.long && long.href.length <= MAILTO_LIMIT && long.href.endsWith('&body=') && long.href.includes('cc=mom%40example.com'))
  const source = fs.readFileSync(path.join(root, 'app/home/components/ProfileColleges.tsx'), 'utf8')
  assert.match(source, /Your note is long\. Use Copy, then open your email and paste it\./)
  assert.match(source, /\{open\?\.long && <button type="button" onClick=\{\(\) => void copy\(\)\} disabled=\{busy\} className=\{primary\}>Copy<\/button>\}/)
  assert.ok(!/—/.test(source), 'no em dash in UI copy')
})

check('What\'s in your note: ticks only what the current text includes', () => {
  const { noteChecklist } = transpile('app/home/components/emailKit.ts')
  const kit = { grad_year: 2028, position: 'QB', hometown: 'Plano, TX', highlight_url: 'https://gmtm.com/film/301', highlight_reel: true,
    profile_url: 'https://gmtm.com/athletes/7301', drills: ['20-Yard Dash 3.42 s', '5-10-5 Shuttle 5.1 s'] }
  const full = 'Class of 2028 QB from Plano, TX\nMy highlight reel: https://gmtm.com/film/301\nMy GMTM profile: https://gmtm.com/athletes/7301\nMy combine results: 20-Yard Dash 3.42 s, 5-10-5 Shuttle 5.1 s'
  assert.deepEqual(noteChecklist(full, kit, 'mom@example.com').map(i => [i.label, i.done]), [
    ['Grad year, position, hometown', true], ['Your highlight reel link', true], ['Your GMTM profile link', true],
    ['Your best 2 combine numbers', true], ['Your parent in CC', true]])
  const edited = noteChecklist(full.replace('https://gmtm.com/film/301', ''), kit, '')
  assert.deepEqual(edited.map(i => i.done), [true, false, true, true, false])
  const none = noteChecklist('Hello Coach,', { ...kit, grad_year: null, hometown: null, highlight_url: null, drills: [] }, 'bad,a@b.co')
  assert.deepEqual(none.map(i => [i.label, i.done]), [['Position', false], ['Your highlight video (none public on GMTM yet)', false],
    ['Your GMTM profile link', false], ['Your combine numbers (none on GMTM yet)', false], ['Your parent in CC', false]])
})

check('B1: the shell never remounts the page on session load; tabs do not prefetch', () => {
  const shell = fs.readFileSync(path.join(root, 'app/home/components/ProfileWorkspaceShell.tsx'), 'utf8')
  assert.ok(!/<CareerShell key=/.test(shell), 'no session key on the shell (it remounted the page after the first render)')
  assert.match(shell, /const waiting = !sessionLoaded \|\| \(!!userId && notice\.phase === 'loading'\)/)
  assert.match(shell, /\{waiting \? <p role="status"/)
  assert.equal((shell.match(/<Link key=\{tab\.href\} href=\{tab\.href\} prefetch=\{false\}/g) || []).length, 2)
})

check('B5: map labels never sit on the "You" pin or its text, nor on each other', () => {
  const { chooseLabels } = transpile('app/home/components/journey.ts')
  const view = { w: 30, h: 30 }
  const you = { x: 82, y: 78 }  // Orlando-like
  const p = (id, x, y) => ({ id, map: { x, y } })
  const placed = [p('WU', 83, 78.5), p('FM', 85, 79), p('left', 70, 78), p('above', 82, 70), p('near-above', 83, 69.5), p('far', 90, 88), p('x', 60, 60)]
  const ids = chooseLabels(placed, you, view).map(q => q.id)
  assert.ok(!ids.includes('WU') && !ids.includes('FM'), 'labels next to You are dots: ' + ids)
  assert.deepEqual(ids, ['left', 'above', 'far', 'x'])
  assert.equal(chooseLabels(placed, null, view).length, 4)
  assert.equal(chooseLabels([p('a', 50, 50), p('b', 51, 50)], null, view).length, 1)
})

check('B6: the level ("NCAA D1") stays on one line on cards, saved colleges and Emails', () => {
  const colleges = fs.readFileSync(path.join(root, 'app/home/components/ProfileColleges.tsx'), 'utf8')
  assert.equal((colleges.match(/<span className="whitespace-nowrap">\{(program|row)\.level\}<\/span>/g) || []).length, 2)
  assert.match(fs.readFileSync(path.join(root, 'app/home/components/AthleteCareerHome.tsx'), 'utf8'), /<span className="whitespace-nowrap">\{program\.level\}<\/span>/)
})

check('B3: GMTM users/undefined upload keys are never requested', () => {
  const { isProfileThumbnail } = transpile('app/home/components/profileMaterials.ts')
  assert.equal(isProfileThumbnail('https://cdn.gmtm.com/users/undefined/uploads/11111111-2222-4333-8444-555555555555.jpg'), false)
  assert.equal(isProfileThumbnail('https://cdn.gmtm.com/users/7201/uploads/clip.jpg'), true)
})

check('My card CSP: images from self, cdn.gmtm.com and i.ytimg.com (posters); video from self and cdn.gmtm.com only', () => {
  const csp = policy.profileContentSecurityPolicy({ nonce, profile: true })
  const directive = name => csp.split('; ').find(part => part.startsWith(name + ' ')) || ''
  assert.equal(directive('img-src'), "img-src 'self' data: https://cdn.gmtm.com https://i.ytimg.com")
  assert.equal(directive('media-src'), "media-src 'self' https://cdn.gmtm.com")
  assert.ok(!/https:(?!\/\/cdn\.gmtm\.com)/.test(directive('media-src')), 'no other video host')
  assert.ok(!/https:(?!\/\/(?:cdn\.gmtm\.com|i\.ytimg\.com))/.test(directive('img-src')), 'no other image host')
  assert.ok(!/ytimg/.test(directive('connect-src') + directive('media-src')))
  assert.equal(directive('connect-src'), "connect-src 'self'")
  assert.equal(directive('frame-src'), "frame-src 'none'")
  // Every directive other than img/media is identical to the non-profile policy.
  const base = policy.profileContentSecurityPolicy({ nonce }).split('; ')
  assert.deepEqual(csp.split('; ').filter(d => !/^(img|media)-src /.test(d)), base.filter(d => !/^(img|media)-src /.test(d)))
  const source = fs.readFileSync(path.join(root, 'middleware.ts'), 'utf8')
  assert.match(source, /const profile = isProfileSurface\(surface\)/)
  assert.match(source, /profileContentSecurityPolicy\(\{ nonce, dev: [^}]*connect, profile \}\)/)
})

check('My card: page + owner-checked API only on profile; no public card page or share of a SPARQ URL', () => {
  assert.equal(policy.candidatePagePolicy('/home/card', 'GET', 'profile'), 'page')
  for (const s of ['combine']) assert.equal(policy.candidatePagePolicy('/home/card', 'GET', s), 'deny')
  for (const page of ['/card/user_x', '/home/card/user_x', '/athlete/1/card', '/share/card']) assert.equal(policy.candidatePagePolicy(page, 'GET', 'profile'), 'deny', page)
  assert.equal(policy.candidateAPIAllowed('/api/workspace/card/user_x', 'GET', '', 'profile'), true)
  assert.equal(policy.candidateAPIAllowed('/api/workspace/card/user_x', 'POST', '', 'profile'), true)
  assert.equal(policy.candidateAPIAllowed('/api/workspace/card/user_x', 'DELETE', '', 'profile'), false)
  assert.equal(policy.candidateAPIAllowed('/api/workspace/card/user_x/lead', 'GET', '', 'profile'), true)
  assert.equal(policy.candidateAPIAllowed('/api/workspace/card/user_x/lead', 'POST', '', 'profile'), false)
  assert.equal(policy.candidateAPIAllowed('/api/workspace/card/user_x/lead', 'GET', '', 'combine'), false)
  assert.equal(policy.candidateAPIAllowed('/api/workspace/card/user_x', 'GET', '', 'combine'), false)
  const ui = fs.readFileSync(path.join(root, 'app/home/components/MyCard.tsx'), 'utf8')
  // The only copied link is her GMTM profile URL from the backend (set only when GMTM shows it publicly).
  assert.match(ui, /navigator\.clipboard\.writeText\(url\)/)
  assert.match(ui, /const url = share\.profile_url/)
  assert.match(ui, /Make your GMTM profile public to share it\./)
  assert.ok(!/window\.location|location\.origin|sparq\.gmtm\.com/.test(ui), 'no SPARQ card URL is built or shared')
  assert.ok(!/dangerouslySetInnerHTML|innerHTML/.test(ui))
  const shell = fs.readFileSync(path.join(root, 'app/home/components/ProfileWorkspaceShell.tsx'), 'utf8')
  assert.match(shell, /\{ href: '\/home\/card', label: 'My card', match: \(path: string\) => path === '\/home\/card' \|\| path === '\/home\/footage' \}/)
  const home = fs.readFileSync(path.join(root, 'app/home/components/AthleteCareerHome.tsx'), 'utf8')
  assert.match(home, /<Link href="\/home\/card" className=\{outline\}>See my athlete card<\/Link>/)
  // Home: neutral skeleton until the lead-only card read answers; footage default only if it fails.
  assert.match(home, /card\.state === 'ready' \? card\.lead : card\.state === 'failed' \? featuredClip\(clips, featuredId\) : undefined/)
  assert.match(home, /heroLoading \? <div role="status" aria-label="Loading your featured clip"/)
  assert.match(fs.readFileSync(path.join(root, 'app/home/components/ProfileWorkspace.tsx'), 'utf8'), /useCard\(userId, true\)/)
  // Raw uploads are 80-500 MB: no preview video anywhere, and the lead player loads only on her tap.
  const sources = ['MyCard.tsx', 'AthleteCareerHome.tsx', 'ProfileWorkspace.tsx'].map(n => fs.readFileSync(path.join(root, 'app/home/components', n), 'utf8')).join('\n')
  assert.equal((sources.match(/<video\b/g) || []).length, 1)
  assert.match(ui, /<video key=\{clip\.id\} controls autoPlay playsInline preload="none"/)
  assert.match(ui, /if \(inline && playing\)/)
  assert.ok(!/preload="(?:metadata|auto)"|#t=/.test(sources))
  assert.ok(!ui.includes('Write a draft for this college first.'))
})

check('My card picker: tap adds or removes, keeps order, max 3; response check drops bad media and foreign hosts', () => {
  const { togglePick, readCard, isCardVideo, isCardPoster, CARD_MAX } = transpile('app/home/components/cardPicker.ts')
  assert.equal(CARD_MAX, 3)
  let picks = []
  for (const id of ['film-1', 'film-2', 'film-3']) picks = togglePick(picks, id)
  assert.deepEqual(picks, ['film-1', 'film-2', 'film-3'])
  assert.deepEqual(togglePick(picks, 'film-4'), picks, 'a fourth pick is refused')
  assert.deepEqual(togglePick(picks, 'film-2'), ['film-1', 'film-3'])
  assert.deepEqual(togglePick(togglePick(picks, 'film-1'), 'film-1'), ['film-2', 'film-3', 'film-1'], 're-adding goes last')
  assert.ok(isCardVideo('https://cdn.gmtm.com/users/7301/uploads/My%20Clip%20%281%29.mp4'))
  // Junior Highlight Reels: extensionless GMTM uploads under videos/ (served as video/mp4).
  assert.ok(isCardVideo('https://cdn.gmtm.com/videos/events/1305/pre-edit-uploads/0b7c2d1e-4f5a-4b6c-9d8e-112233445566'))
  for (const bad of ['https://cdn.gmtm.com/users/7301/uploads/abc', 'https://cdn.gmtm.com/videos/x', 'https://cdn.gmtm.com/videos/a/../b',
    'https://cdn.gmtm.com/videos//a/b', 'https://cdn.gmtm.com/videos/a/b?x=1', 'https://cdn.gmtm.com/videos/a/b%2e']) assert.equal(isCardVideo(bad), false, bad)
  for (const bad of ['https://evil.example/a.mp4', 'http://cdn.gmtm.com/a.mp4', 'https://cdn.gmtm.com/a.m3u8', 'https://cdn.gmtm.com//a.mp4',
    'https://cdn.gmtm.com/a/../b.mp4', 'https://cdn.gmtm.com.evil.example/a.mp4', 'javascript:alert(1)//.mp4', null]) assert.equal(isCardVideo(bad), false, String(bad))
  assert.ok(isCardPoster('https://cdn.gmtm.com/videos/film/thumbnails/a.jpg'))
  assert.ok(isCardPoster('https://i.ytimg.com/vi/abcdefghijk/0.jpg'))
  for (const bad of ['https://cdn.gmtm.com/users/undefined/uploads/a.jpg', 'https://cdn.gmtm.com/a.svg', 'https://evil.example/vi/abcdefghijk/0.jpg']) assert.equal(isCardPoster(bad), false, bad)
  const clip = (n, extra = {}) => ({ id: `film-${n}`, title: `Clip ${n}`, source_label: 'Junior Combine #2', recorded_at: null, thumbnail_url: null,
    source_url: `https://gmtm.com/film/${n}`, video_url: null, reel: false, ...extra })
  const body = { state: 'ready', clips: [clip(1, { video_url: 'https://evil.example/x.mp4', thumbnail_url: 'https://evil.example/vi/abcdefghijk/0.jpg' }), clip(2)],
    order: ['film-2'], chosen: true, share: { profile_url: 'https://gmtm.com/athletes/7301', settings_url: null } }
  const card = readCard(body)
  assert.equal(card.clips[0].video_url, null); assert.equal(card.clips[0].thumbnail_url, null)
  assert.deepEqual(card.order, ['film-2'])
  assert.equal(readCard({ ...body, share: null }).share, null, "Home's lead-only read has no share")
  for (const broken of [{ ...body, order: ['film-9'] }, { ...body, order: ['film-1', 'film-1'] }, { ...body, order: ['film-1', 'film-2', 'film-1', 'film-2'] },
    { ...body, share: { profile_url: 'https://sparq.gmtm.com/card/1', settings_url: null } },
    { ...body, clips: [clip(1, { source_url: 'https://evil.example/film/1' })], order: [] }]) assert.throws(() => readCard(broken))
})

check('Map and badges: schools that share initials get unique labels in one list', () => {
  const { schoolLabels, initials } = transpile('app/home/components/journey.ts')
  const labels = schoolLabels(['Daytona State College', 'Delaware State University', 'Alabama State University'])
  assert.deepEqual(labels, { 'Daytona State College': 'DSC', 'Delaware State University': 'DSU', 'Alabama State University': 'AS' })
  const more = schoolLabels(['Manhattan University', 'Mercyhurst University', 'Marymount University', 'Marywood University'])
  assert.equal(new Set(Object.values(more)).size, 4, JSON.stringify(more))
  assert.deepEqual(more, { 'Manhattan University': 'Man', 'Mercyhurst University': 'Mer', 'Marymount University': 'Marym', 'Marywood University': 'Maryw' })
  assert.equal(initials('Daytona State College'), 'DS')
  const colleges = fs.readFileSync(path.join(root, 'app/home/components/ProfileColleges.tsx'), 'utf8')
  assert.match(colleges, /<CollegeMap programs=\{shown\} origin=\{list\.origin\} labels=\{labels\} \/>/)
  assert.match(colleges, /\$\{labels\[p\.school\] \|\| initials\(p\.school\)\}/)
})

console.log(JSON.stringify({ status: 'passed', checks: checks.length, names: checks }, null, 2))
