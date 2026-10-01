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
check('Production CSP: nonce + strict-dynamic, no script unsafe-inline, no Clerk (rev 3), self-only connect', () => {
  const csp = policy.profileContentSecurityPolicy({ nonce })
  const directive = name => csp.split('; ').find(part => part.startsWith(name + ' ')) || ''
  const script = directive('script-src')
  assert.ok(script.includes(`'nonce-${nonce}'`) && script.includes("'strict-dynamic'"))
  assert.ok(!script.includes("'unsafe-inline'") && !script.includes("'unsafe-eval'"))
  assert.ok(!/clerk|challenges\.cloudflare/i.test(csp), 'no Clerk or Turnstile host')
  assert.equal(directive('connect-src'), "connect-src 'self'")
  for (const part of ["object-src 'none'", "base-uri 'self'", "frame-ancestors 'none'", "default-src 'self'"]) assert.ok(csp.includes(part), part)
})

check('Dev CSP adds only unsafe-eval (Next dev runtime), still no script unsafe-inline', () => {
  const script = policy.profileContentSecurityPolicy({ nonce, dev: true }).split('; ').find(part => part.startsWith('script-src '))
  assert.ok(script.includes("'unsafe-eval'") && !script.includes("'unsafe-inline'"))
})

check('CSP refuses a missing or weak nonce and ignores any Clerk key', () => {
  for (const bad of [undefined, '', 'short', "x' 'unsafe-inline"]) assert.throws(() => policy.profileContentSecurityPolicy({ nonce: bad }))
  const csp = policy.profileContentSecurityPolicy({ nonce, publishableKey: 'pk_live_' + Buffer.from('clerk.sparq.example$').toString('base64') })
  assert.ok(!csp.includes('clerk'))
})

check('GMTM sessionId is removed from the forwarded Cookie header; other cookies stay', () => {
  assert.equal(policy.withoutGmtmSession('sessionId=abc; __session=jwt; other=1'), '__session=jwt; other=1')
  assert.equal(policy.withoutGmtmSession(' sessionId=abc '), '')
  assert.equal(policy.withoutGmtmSession('mysessionId=1; sessionIdx=2'), 'mysessionId=1; sessionIdx=2')
  assert.equal(policy.withoutGmtmSession(undefined), '')
})

check('Profile middleware applies the CSP + cookie filter to every response; GMTM sessionId only hashed', () => {
  const source = fs.readFileSync(path.join(root, 'middleware.ts'), 'utf8')
  assert.match(source, /if \(profile\) return profileMiddleware\(request, policy\)/)
  assert.match(source, /return profileResponse\(request, gsh\)/)
  assert.match(source, /withoutGmtmSession\(headers\.get\('cookie'\)\)/)
  assert.match(source, /response\.headers\.set\('Content-Security-Policy', csp\)/)
  // The raw value is read only inside gmtmSessionHash (sha256); nothing else names it.
  assert.ok(!/sessionId/.test(source.replace(/\/\/.*$/gm, '').replace(/withoutGmtmSession|gmtmSessionHash/g, '')))
  const helper = fs.readFileSync(path.join(root, 'lib/sparq-session.cjs'), 'utf8')
  assert.match(helper, /=== 'sessionId'\) \{\s*const value = part\.slice\(at \+ 1\)\.trim\(\)\s*return value \? sha256Hex\(value\) : null/)
  assert.ok(!/console\./.test(helper + source))
  // Per-request render so Next's scripts carry the nonce; no ClerkProvider on profile.
  assert.match(fs.readFileSync(path.join(root, 'app/layout.tsx'), 'utf8'), /if \(profile\) \{\s*headers\(\)\s*return body/)
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

console.log(JSON.stringify({ status: 'passed', checks: checks.length, names: checks }, null, 2))
