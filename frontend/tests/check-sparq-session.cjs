// SPARQ session on every surface (GMTM is the only sign-in): token verification,
// middleware GMTM binding, same-origin proxy, session/sign-out routes, CSP and the
// absence of any third-party sign-in package. Compiled actual sources with real
// next/server; fetch is a stub. No server, credentials or network.
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
let fetchCalls = [], fetchReply = null
function load(rel, modules = {}, moduleEnv = env) {
  const file = path.resolve(root, rel)
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
  const module = { exports: {} }
  const known = { 'next/server': nextServer, '@/lib/backend-config.cjs': policy, './lib/backend-config.cjs': policy, '@/lib/sparq-session.cjs': session, './lib/sparq-session.cjs': session, ...modules }
  const req = id => id in known ? known[id] : assert.fail('unexpected import ' + id + ' in ' + rel)
  new Function('exports', 'require', 'module', 'process', 'fetch', code)(module.exports, req, module, { env: moduleEnv }, async (...args) => { fetchCalls.push(args); return fetchReply })
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
  await check('Middleware denies sign-in/up, claim and connect pages on profile', async () => {
    for (const p of ['/sign-in', '/sign-up', '/connect', '/claim/abc', '/onboarding/search']) assert.equal((await run(request('https://sparq.example' + p, { token: sign() }))).status, 404, p)
  })
  const combineMw = load('middleware.ts', {}, { ...env, NEXT_PUBLIC_APP_SURFACE: 'combine' }).default
  await check('Combine middleware uses the same GMTM-bound session', async () => {
    let res = await combineMw(request('https://combine.example/home/inbox', { token: sign() }), {})
    assert.equal(res.headers.get('location'), null)
    assert.equal(res.headers.get('x-middleware-request-x-sparq-gsh'), GSH)
    res = await combineMw(request('https://combine.example/home/inbox', { token: sign(), raw: 'another-gmtm-user' }), {})
    assert.equal(res.headers.get('location'), 'https://combine.example/enter')
    assert.ok(cleared(res))
    for (const p of ['/sign-in', '/connect', '/claim/abc']) assert.equal((await combineMw(request('https://combine.example' + p, { token: sign() }), {})).status, 404, p)
    assert.equal((await combineMw(request('https://combine.example/enter', {}), {})).headers.get('location'), null)
  })
  const legacyEnv = { ...env, NEXT_PUBLIC_APP_SURFACE: '' }
  const legacyMw = load('middleware.ts', {}, legacyEnv).default
  await check('Legacy middleware: public pages need no session, every other page needs the GMTM-bound session', async () => {
    for (const p of ['/', '/demo', '/quick-scan', '/athlete/12', '/report/tok', '/enter', '/enter/callback?code=c&state=s', '/api/sparq/session']) {
      const res = await legacyMw(request('https://legacy.example' + p, {}), {})
      assert.equal(res.headers.get('location'), null, p)
      assert.match(res.headers.get('content-security-policy'), /connect-src 'self' https:\/\/backend\.example;/)
    }
    for (const p of ['/home', '/home/inbox', '/home/profile', '/sign-in', '/onboarding/search']) {
      const res = await legacyMw(request('https://legacy.example' + p, {}), {})
      assert.equal(res.headers.get('location'), 'https://legacy.example/enter', p)
    }
    assert.equal((await legacyMw(request('https://legacy.example/home', { token: sign() }), {})).headers.get('location'), null)
    assert.equal((await legacyMw(request('https://legacy.example/home', { raw: null }), {})).headers.get('location'), 'https://gmtm.example/')
  })
  await check('Legacy proxy forwards legacy routes (incl. PUT/DELETE) with the session bearer', async () => {
    const legacyServer = load('app/api/sparq/server.ts', {}, legacyEnv)
    const legacyProxy = load('app/api/sparq/proxy/[...path]/route.ts', { '../../server': legacyServer }, legacyEnv)
    const token = sign()
    for (const [method, p] of [['GET', '/api/workspace/inbox/gmtm_7301'], ['PUT', '/api/workspace/outreach/3/status'], ['DELETE', '/api/links/4']]) {
      fetchCalls = []; fetchReply = new Response('{}', { status: 200 })
      const res = await legacyProxy[method](request('https://legacy.example/api/sparq/proxy' + p, { token, gsh: GSH, method }))
      assert.equal(res.status, 200, method + p)
      assert.equal(fetchCalls[0][0], 'https://backend.example' + p)
      assert.equal(fetchCalls[0][1].headers.Authorization, 'Bearer ' + token)
      if (method !== 'PUT') assert.equal(fetchCalls[0][1].body, undefined)
    }
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
  await check('Browser API helper calls only the same-origin proxy, with no token', async () => {
    const calls = []
    const code = ts.transpileModule(fs.readFileSync(path.join(root, 'app/_lib/api.ts'), 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
    const module = { exports: {} }
    new Function('exports', 'require', 'module', 'process', 'fetch', 'window', code)(module.exports, () => policy, module, { env }, async (...args) => { calls.push(args); return { ok: true } }, {})
    await module.exports.apiFetch('https://backend.example/api/athlete/workspace', { method: 'PATCH', body: '{}' })
    assert.equal(calls[0][0], '/api/sparq/proxy/api/athlete/workspace')
    assert.equal(calls[0][1].credentials, 'same-origin')
    assert.ok(!calls[0][1].headers)
    await assert.rejects(module.exports.apiFetch('/api/workspace/inbox/me'))
    assert.equal(calls.length, 1)
  })

  // ── CSP and sign-in package reachability ─────────────────────────────────────
  await check('Profile CSP has no third-party sign-in or Turnstile host and connects only to self', () => {
    const csp = policy.profileContentSecurityPolicy({ nonce: 'c3ludGhldGljLW5vbmNlLXZhbHVl' })
    assert.ok(!/challenges\.cloudflare|accounts\./i.test(csp))
    assert.ok(csp.includes("connect-src 'self';"))
  })
  await check('No source file, package.json or lockfile names a third-party sign-in package', () => {
    const banned = new RegExp('cle' + 'rk', 'i'), allowed = new RegExp('\\b' + 'cle' + 'rk_id\\b', 'g'), hits = []
    const walk = dir => { for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
      if (['node_modules', '.next'].includes(entry.name)) continue
      const file = path.join(dir, entry.name)
      if (entry.isDirectory()) walk(file)
      else if (/\.(?:tsx?|cjs|js|mjs|json|md|css)$/.test(entry.name) && banned.test(fs.readFileSync(file, 'utf8').replace(allowed, ''))) hits.push(path.relative(root, file))
    } }
    walk(root)
    assert.deepEqual(hits, [])
    for (const d of ['app/sign-in', 'app/sign-up', 'app/claim', 'app/connect', 'app/onboarding', 'app/api/onboarding']) assert.ok(!fs.existsSync(path.join(root, d)), d)
  })
  await check('Every page renders per request so scripts carry the CSP nonce', () => {
    assert.match(fs.readFileSync(path.join(root, 'app/layout.tsx'), 'utf8'), /headers\(\)\s*return \(/)
  })
  console.log(JSON.stringify({ status: 'passed', checks: checks.length }))
})().catch(error => { console.error(error); process.exit(1) })
