// Profile surface SPARQ session (no Clerk): token verification, middleware GMTM
// binding, same-origin proxy, session/sign-out routes, CSP and Clerk reachability.
// Compiled actual sources with real next/server; fetch and Clerk are stubs. No
// server, credentials or network.
// Run: SPARQ_TEST_NODE_MODULES=<frontend/node_modules> node frontend/tests/check-sparq-session.cjs
const assert = require('node:assert/strict')
const crypto = require('node:crypto')
const fs = require('node:fs')
const path = require('node:path')
const policy = require('../lib/backend-config.cjs')
const session = require('../lib/sparq-session.cjs')
const deps = process.env.SPARQ_TEST_NODE_MODULES
if (!deps) throw Error('Set SPARQ_TEST_NODE_MODULES to an existing dependency tree')
const ts = require(path.join(deps, 'typescript'))
const nextServer = require(path.join(deps, 'next/server'))
const root = path.resolve(__dirname, '..')
const checks = []
async function check(name, fn) { await fn(); checks.push(name) }

const SECRET = 'synthetic-sparq-session-secret-32-bytes!'
const RAW = 'synthetic-gmtm-session-id'
const GSH = crypto.createHash('sha256').update(RAW).digest('hex')
const now = () => Math.floor(Date.now() / 1000)
const b64 = value => Buffer.from(typeof value === 'string' ? value : JSON.stringify(value)).toString('base64url')
function sign(claims = {}, { secret = SECRET, header = { alg: 'HS256', typ: 'JWT' } } = {}) {
  const body = { sub: 'gmtm_7301', jti: 'j'.repeat(43), gsh: GSH, iat: now(), exp: now() + 86400, ...claims }
  const head = b64(header) + '.' + b64(body)
  return head + '.' + crypto.createHmac('sha256', secret).update(head).digest('base64url')
}

const env = {
  NEXT_PUBLIC_APP_SURFACE: 'profile', NEXT_PUBLIC_BACKEND_URL: 'https://backend.example', NODE_ENV: 'production',
  NEXT_PUBLIC_GMTM_WEB_URL: 'https://gmtm.example', SPARQ_SESSION_SECRET: SECRET,
}
let fetchCalls = [], fetchReply = null, clerkCalls = 0
const clerkStub = { clerkMiddleware: () => { clerkCalls++; throw Error('Clerk must not run on profile') }, createRouteMatcher: () => () => false }
function load(rel, modules = {}) {
  const file = path.resolve(root, rel)
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
  const module = { exports: {} }
  const known = { 'next/server': nextServer, '@/lib/backend-config.cjs': policy, './lib/backend-config.cjs': policy, '@/lib/sparq-session.cjs': session, './lib/sparq-session.cjs': session, '@clerk/nextjs/server': clerkStub, ...modules }
  const req = id => id in known ? known[id] : assert.fail('unexpected import ' + id + ' in ' + rel)
  new Function('exports', 'require', 'module', 'process', 'fetch', code)(module.exports, req, module, { env }, async (...args) => { fetchCalls.push(args); return fetchReply })
  return module.exports
}
const cookieOf = (res, name) => res.headers.getSetCookie().find(c => c.startsWith(name + '='))
const cleared = res => { const c = cookieOf(res, '__Host-sparq-session'); return !!c && c.includes('Max-Age=0') }
const SAME = { 'sec-fetch-site': 'same-origin' }
const request = (url, { token, raw = RAW, gsh, method = 'GET', body, headers = method === 'GET' ? {} : SAME } = {}) => {
  const cookie = [token !== undefined && `__Host-sparq-session=${token}`, raw && `sessionId=${raw}`, 'other=1'].filter(Boolean).join('; ')
  return new nextServer.NextRequest(url, { method, body, headers: { cookie, ...(gsh ? { 'x-sparq-gsh': gsh } : {}), ...headers } })
}

;(async () => {
  // ── Token verification ────────────────────────────────────────────────────────
  await check('verifySession accepts a valid token bound to the current GMTM session', async () => {
    assert.deepEqual(await session.verifySession(sign(), SECRET, GSH), { sub: 'gmtm_7301', exp: JSON.parse(Buffer.from(sign().split('.')[1], 'base64url')).exp })
  })
  for (const [name, token, secret, gsh] of [
    ['GMTM session mismatch (gsh)', sign(), SECRET, crypto.createHash('sha256').update('another-gmtm-user').digest('hex')],
    ['no GMTM session', sign(), SECRET, null],
    ['expired', sign({ exp: now() - 1 }), SECRET, GSH],
    ['issued in the future', sign({ iat: now() + 3600 }), SECRET, GSH],
    ['wrong secret', sign({}, { secret: 'w'.repeat(40) }), SECRET, GSH],
    ['short server secret', sign({}, { secret: 'short' }), 'short', GSH],
    ['alg none', b64({ alg: 'none' }) + '.' + b64({ sub: 'x', jti: 'j', gsh: GSH, iat: now(), exp: now() + 60 }) + '.', SECRET, GSH],
    ['tampered subject', (() => { const [h, , s] = sign().split('.'); return h + '.' + b64({ sub: 'gmtm_1', jti: 'j', gsh: GSH, iat: now(), exp: now() + 60 }) + '.' + s })(), SECRET, GSH],
    ['missing jti', sign({ jti: undefined }), SECRET, GSH],
    ['raw sessionId instead of hash', sign({ gsh: RAW }), SECRET, RAW],
    ['garbage', 'not.a.jwt', SECRET, GSH],
    ['no token', undefined, SECRET, GSH],
  ]) await check('verifySession refuses ' + name, async () => assert.equal(await session.verifySession(token, secret, gsh), null))
  await check('gmtmSessionHash hashes only the exact sessionId cookie', async () => {
    assert.equal(await session.gmtmSessionHash(`a=1; sessionId=${RAW}; b=2`), GSH)
    for (const header of ['', null, 'mysessionId=1; sessionIdx=2', 'sessionId=']) assert.equal(await session.gmtmSessionHash(header), null)
  })

  // ── Middleware (profile) ──────────────────────────────────────────────────────
  const middleware = load('middleware.ts').default
  const run = req => middleware(req, {})
  await check('Middleware passes a bound session and forwards only the GMTM hash', async () => {
    const res = await run(request('https://sparq.example/home/inbox', { token: sign(), gsh: 'f'.repeat(64) }))
    assert.equal(res.headers.get('location'), null)
    assert.equal(res.headers.get('x-middleware-request-x-sparq-gsh'), GSH, 'client x-sparq-gsh replaced')
    const forwarded = res.headers.get('x-middleware-request-cookie')
    assert.ok(!forwarded.includes('sessionId') && !forwarded.includes(RAW) && forwarded.includes('__Host-sparq-session='))
    assert.ok(!JSON.stringify([...res.headers]).includes(RAW), 'raw GMTM session never forwarded')
    assert.match(res.headers.get('content-security-policy'), /'nonce-/)
    assert.ok(!cookieOf(res, '__Host-sparq-session'))
  })
  for (const [name, opts, location] of [
    ['GMTM session mismatch (gsh)', { token: sign(), raw: 'another-gmtm-user' }, 'https://sparq.example/enter'],
    ['missing GMTM cookie', { token: sign(), raw: null }, 'https://gmtm.example/'],
    ['expired token', { token: sign({ exp: now() - 1 }) }, 'https://sparq.example/enter'],
    ['wrong-secret token', { token: sign({}, { secret: 'w'.repeat(40) }) }, 'https://sparq.example/enter'],
    ['empty token', { token: '' }, 'https://sparq.example/enter'],
  ]) await check('Middleware clears the session and redirects on ' + name, async () => {
    const res = await run(request('https://sparq.example/home/inbox', opts))
    assert.equal(res.status, 307)
    assert.equal(res.headers.get('location'), location)
    assert.ok(cleared(res), 'session cookie cleared')
    const c = cookieOf(res, '__Host-sparq-session')
    for (const flag of ['Path=/', 'Secure', 'HttpOnly']) assert.ok(c.includes(flag), flag)
    assert.equal(res.headers.get('cache-control'), 'no-store')
  })
  await check('Middleware with no session goes to /enter (GMTM cookie) or GMTM (none), nothing to clear', async () => {
    let res = await run(request('https://sparq.example/home/colleges', {}))
    assert.equal(res.headers.get('location'), 'https://sparq.example/enter')
    assert.ok(!cookieOf(res, '__Host-sparq-session'))
    res = await run(request('https://sparq.example/home', { raw: null }))
    assert.equal(res.headers.get('location'), 'https://gmtm.example/')
  })
  await check('Middleware lets the /enter bridge and /api/sparq routes through without a session', async () => {
    for (const url of ['https://sparq.example/enter', 'https://sparq.example/enter/callback?code=c&state=s', 'https://sparq.example/enter/unavailable', 'https://sparq.example/api/sparq/session', 'https://sparq.example/api/sparq/proxy/api/athlete/evidence']) {
      const res = await run(request(url, { gsh: 'f'.repeat(64) }))
      assert.equal(res.headers.get('location'), null, url)
      assert.equal(res.headers.get('x-middleware-request-x-sparq-gsh'), GSH, url)
    }
    const res = await run(request('https://sparq.example/api/sparq/session', { raw: null, gsh: 'f'.repeat(64) }))
    assert.equal(res.headers.get('x-middleware-request-x-sparq-gsh'), null, 'forged hash dropped')
  })
  await check('Middleware denies Clerk sign-in/up and connect pages; never builds or calls Clerk on profile', async () => {
    for (const p of ['/sign-in', '/sign-up', '/connect']) assert.equal((await run(request('https://sparq.example' + p, { token: sign() }))).status, 404, p)
    assert.equal(clerkCalls, 0)
  })

  // ── Same-origin routes ────────────────────────────────────────────────────────
  const server = load('app/api/sparq/server.ts')
  const proxy = load('app/api/sparq/proxy/[...path]/route.ts', { '../../server': server })
  const sessionRoute = load('app/api/sparq/session/route.ts', { '../server': server })
  const signOut = load('app/api/sparq/sign-out/route.ts', { '../server': server })
  const reply = (status, body) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
  await check('Proxy forwards an allowed path with the session as bearer and no browser credentials', async () => {
    const token = sign()
    for (const [method, p, body] of [['GET', '/api/athlete/evidence'], ['PATCH', '/api/athlete/workspace', '{"version":1}'], ['POST', '/api/workspace/trigger-matching/gmtm_7301', '{}']]) {
      fetchCalls = []; fetchReply = reply(200, { ok: true })
      const res = await proxy[method](request('https://sparq.example/api/sparq/proxy' + p, { token, gsh: GSH, method, body, headers: body ? { 'content-type': 'application/json', ...SAME } : SAME }))
      assert.equal(res.status, 200)
      assert.equal(res.headers.get('cache-control'), 'private, no-store')
      assert.equal(fetchCalls.length, 1)
      const [url, init] = fetchCalls[0]
      assert.equal(url, 'https://backend.example' + p)
      assert.equal(init.method, method)
      assert.equal(init.redirect, 'error')
      assert.equal(init.headers.Authorization, 'Bearer ' + token)
      assert.ok(!('cookie' in init.headers) && !('Cookie' in init.headers))
      if (body) assert.equal(Buffer.from(init.body).toString(), body)
    }
  })
  for (const [method, p] of [['GET', '/api/workspace/inbox/me'], ['POST', '/gmtm-entry/exchange'], ['POST', '/gmtm-entry/sign-out'], ['GET', '/api/athlete/evidence?user_id=2'], ['GET', '/api/%2e%2e/athlete/evidence'], ['POST', '/api/athlete/evidence'], ['GET', '/api/combine/current'], ['GET', '/api/reports/public/token']]) await check('Proxy refuses ' + method + ' ' + p + ' without a bearer', async () => {
    fetchCalls = []
    const res = await proxy[method](request('https://sparq.example/api/sparq/proxy' + p, { token: sign(), gsh: GSH, method }))
    assert.equal(res.status, 404)
    assert.equal(fetchCalls.length, 0)
  })
  for (const [name, opts] of [['no session', { gsh: GSH }], ['gsh mismatch', { token: sign(), gsh: 'f'.repeat(64) }], ['no GMTM session hash', { token: sign() }], ['expired', { token: sign({ exp: now() - 1 }), gsh: GSH }]]) await check('Proxy answers 401 and clears the cookie on ' + name, async () => {
    fetchCalls = []
    const res = await proxy.GET(request('https://sparq.example/api/sparq/proxy/api/athlete/evidence', opts))
    assert.equal(res.status, 401)
    assert.ok(cleared(res))
    assert.equal(fetchCalls.length, 0)
  })
  for (const [name, headers] of [
    ['cross-site POST', { 'sec-fetch-site': 'cross-site', origin: 'https://evil.example' }],
    ['same-site other-subdomain POST', { 'sec-fetch-site': 'same-site', origin: 'https://www.gmtm.com' }],
    ['missing fetch metadata and origin', {}],
    ['spoofed origin with other host', { origin: 'https://sparq.example.evil' }],
  ]) await check('Proxy and sign-out refuse ' + name + ' with 403 before any backend call', async () => {
    fetchCalls = []
    const proxied = await proxy.POST(request('https://sparq.example/api/sparq/proxy/api/athlete/debrief', { token: sign(), gsh: GSH, method: 'POST', body: '{}', headers }))
    assert.equal(proxied.status, 403)
    const out = await signOut.POST(request('https://sparq.example/api/sparq/sign-out', { token: sign(), method: 'POST', headers }))
    assert.equal(out.status, 403)
    assert.ok(!cookieOf(out, '__Host-sparq-session'), 'cookie untouched')
    assert.equal(fetchCalls.length, 0)
  })
  await check('Same-origin POST by Origin header alone is forwarded', async () => {
    fetchCalls = []; fetchReply = reply(200, { ok: true })
    const res = await proxy.POST(request('https://sparq.example/api/sparq/proxy/api/athlete/debrief', { token: sign(), gsh: GSH, method: 'POST', body: '{}', headers: { origin: 'https://sparq.example' } }))
    assert.equal(res.status, 200)
    assert.equal(fetchCalls.length, 1)
  })
  await check('Session route returns sub only, never the token', async () => {
    const token = sign()
    const res = await sessionRoute.GET(request('https://sparq.example/api/sparq/session', { token, gsh: GSH }))
    assert.equal(res.status, 200)
    const text = await res.text()
    assert.deepEqual(JSON.parse(text), { sub: 'gmtm_7301' })
    assert.ok(!text.includes(token.split('.')[2]))
    const denied = await sessionRoute.GET(request('https://sparq.example/api/sparq/session', { token, gsh: 'f'.repeat(64) }))
    assert.equal(denied.status, 401)
    assert.ok(cleared(denied))
  })
  await check('Sign-out ends the jti on the backend and clears the cookie', async () => {
    const token = sign()
    fetchCalls = []; fetchReply = reply(200, { signed_out: true })
    const res = await signOut.POST(request('https://sparq.example/api/sparq/sign-out', { token, method: 'POST' }))
    assert.equal(fetchCalls.length, 1)
    assert.equal(fetchCalls[0][0], 'https://backend.example/gmtm-entry/sign-out')
    assert.equal(fetchCalls[0][1].headers.Authorization, 'Bearer ' + token)
    assert.ok(cleared(res))
    assert.equal((await res.json()).next, 'https://gmtm.example')
    fetchCalls = []
    assert.ok(cleared(await signOut.POST(request('https://sparq.example/api/sparq/sign-out', { method: 'POST' }))))
    assert.equal(fetchCalls.length, 0)
  })
  await check('Browser API helper on profile calls only the same-origin proxy, with no token', async () => {
    const calls = []
    const code = ts.transpileModule(fs.readFileSync(path.join(root, 'app/_lib/api.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
    const module = { exports: {} }
    new Function('exports', 'require', 'module', 'process', 'fetch', 'window', code)(module.exports, () => policy, module, { env }, async (...args) => { calls.push(args); return { ok: true } }, { Clerk: { session: { getToken: () => assert.fail('no Clerk token on profile') } } })
    await module.exports.apiFetch('https://backend.example/api/athlete/workspace', { method: 'PATCH', body: '{}' })
    assert.equal(calls[0][0], '/api/sparq/proxy/api/athlete/workspace')
    assert.equal(calls[0][1].credentials, 'same-origin')
    assert.ok(!calls[0][1].headers)
    await assert.rejects(module.exports.apiFetch('/api/workspace/inbox/me'))
    assert.equal(calls.length, 1)
  })

  // ── CSP and Clerk reachability ───────────────────────────────────────────────
  await check('Profile CSP has no Clerk or Turnstile host and connects only to self', () => {
    const csp = policy.profileContentSecurityPolicy({ nonce: 'c3ludGhldGljLW5vbmNlLXZhbHVl' })
    assert.ok(!/clerk|challenges\.cloudflare/i.test(csp))
    assert.ok(csp.includes("connect-src 'self';"))
  })
  // Static import closure from the modules only the profile surface renders.
  const roots = ['app/home/components/ProfileWorkspaceShell.tsx', 'app/home/components/ProfileWorkspace.tsx', 'app/home/components/ProfileColleges.tsx',
    'app/home/components/ParentNoticeGate.tsx', 'app/_lib/api.ts', 'app/_lib/useSparqSession.ts', 'app/enter/route.ts', 'app/enter/callback/route.ts',
    'app/enter/unavailable/page.tsx', 'app/api/sparq/session/route.ts', 'app/api/sparq/sign-out/route.ts', 'app/api/sparq/proxy/[...path]/route.ts']
  function resolveImport(from, spec) {
    const base = spec.startsWith('@/') ? path.join(root, spec.slice(2)) : spec.startsWith('.') ? path.resolve(path.dirname(from), spec) : null
    if (!base) return null
    for (const candidate of [base, ...['.tsx', '.ts', '.cjs', '.js'].map(ext => base + ext), ...['index.tsx', 'index.ts'].map(f => path.join(base, f))]) if (fs.existsSync(candidate) && fs.statSync(candidate).isFile()) return candidate
    return assert.fail('unresolved ' + spec + ' from ' + from)
  }
  await check('No @clerk import is reachable from profile-surface modules', () => {
    const seen = new Set(), clerk = []
    const walk = file => {
      if (seen.has(file)) return
      seen.add(file)
      const source = fs.readFileSync(file, 'utf8')
      for (const [, spec] of source.matchAll(/(?:import|export)[^'"]*?from\s*['"]([^'"]+)['"]|import\(\s*['"]([^'"]+)['"]\s*\)|require\(\s*['"]([^'"]+)['"]\s*\)/g).map(m => [m[0], m[1] || m[2] || m[3]])) {
        if (spec.startsWith('@clerk/')) clerk.push(path.relative(root, file))
        const next = resolveImport(file, spec)
        if (next) walk(next)
      }
    }
    roots.forEach(r => walk(path.join(root, r)))
    assert.ok(seen.size > 20, 'walked ' + seen.size)
    assert.deepEqual(clerk, [])
  })
  await check('Shared entry files send the profile surface to Clerk-free modules before any Clerk use', () => {
    const read = rel => fs.readFileSync(path.join(root, rel), 'utf8')
    assert.match(read('app/layout.tsx'), /if \(profile\) \{\s*headers\(\)\s*return body\s*\}\s*if \(clerkKey\) return <ClerkProvider/)
    assert.match(read('app/home/layout.tsx'), /if \(isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)\) \{\s*return <ProfileWorkspaceShell>/)
    assert.match(read('app/home/page.tsx'), /if \(isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)\) redirect\('\/home\/inbox'\)\s*return <HomeClient \/>/)
    assert.match(read('app/home/inbox/page.tsx'), /if \(isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)\) return <ProfileWorkspace \/>/)
    assert.match(read('app/home/colleges/page.tsx'), /export default isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\) \? ProfileColleges :/)
    assert.match(read('app/home/colleges/[id]/page.tsx'), /if \(isProfileSurface\(process\.env\.NEXT_PUBLIC_APP_SURFACE\)\) return <ProfileCollegeDetail /)
    const mw = read('middleware.ts')
    assert.match(mw, /const authenticatedMiddleware = profile \? null : clerkMiddleware\(/)
    assert.ok(mw.indexOf('if (profile) return profileMiddleware(request, policy)') < mw.indexOf('return authenticatedMiddleware!(request, event)'))
  })
  console.log(JSON.stringify({ status: 'passed', checks: checks.length }))
})().catch(error => { console.error(error); process.exit(1) })
