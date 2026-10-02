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
  assert.match(source, /\/\^\[A-Za-z0-9\._\+-\]\+@\[A-Za-z0-9-\]\+\(\\\.\[A-Za-z0-9-\]\+\)\+\$\//)
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
  assert.match(source, /onClick=\{\(\) => void copy\(\)\} disabled=\{busy\}/)
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
  new Function('exports', 'module', ts.transpileModule(fs.readFileSync(path.join(root, file), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText)(module.exports, module)
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

check('Pages: /home is the journey; Home, Colleges, Emails (progress), My card (footage) tabs; active tab per URL; profile-only', () => {
  const home = fs.readFileSync(path.join(root, 'app/home/page.tsx'), 'utf8')
  assert.match(home, /<ProfileWorkspace view="home" \/>/)
  assert.match(fs.readFileSync(path.join(root, 'app/home/inbox/page.tsx'), 'utf8'), /isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)\) redirect\('\/home'\)/)
  for (const [page, view] of [['progress', 'progress'], ['footage', 'footage']]) {
    const source = fs.readFileSync(path.join(root, `app/home/${page}/page.tsx`), 'utf8')
    assert.match(source, /if \(!isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)\) notFound\(\)/)
    assert.match(source, new RegExp(`<ProfileWorkspace view="${view}" />`))
    assert.equal(policy.candidatePagePolicy(`/home/${page}`, 'GET', 'profile'), 'page')
    assert.equal(policy.candidatePagePolicy(`/home/${page}`, 'GET', 'combine'), 'deny')
  }
  const shell = fs.readFileSync(path.join(root, 'app/home/components/ProfileWorkspaceShell.tsx'), 'utf8')
  for (const [href, label] of [['/home', 'Home'], ['/home/colleges', 'Colleges'], ['/home/progress', 'Emails'], ['/home/footage', 'My card']]) assert.ok(shell.includes(`{ href: '${href}', label: '${label}'`), label)
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

check('Colleges UI: no coach contact yet, "I sent it" only marks a date, saves are POST {saved}', () => {
  const source = fs.readFileSync(path.join(root, 'app/home/components/ProfileColleges.tsx'), 'utf8')
  assert.ok(!/coach_email|head_coach|staff_page/.test(source))
  assert.match(source, /JSON_POST\(\{ sent \}\)/)
  assert.match(source, /JSON_POST\(\{ saved: next \}\)/)
  assert.match(source, /← Colleges/)
})

console.log(JSON.stringify({ status: 'passed', checks: checks.length, names: checks }, null, 2))
