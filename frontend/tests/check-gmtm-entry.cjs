// GMTM entry routes: compiled actual handlers with real next/server; fetch is stubbed.
// No server, credentials or network. Run: SPARQ_TEST_NODE_MODULES=<frontend/node_modules> node frontend/tests/check-gmtm-entry.cjs
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const policy = require('../lib/backend-config.cjs')
const deps = process.env.SPARQ_TEST_NODE_MODULES
if (!deps) throw Error('Set SPARQ_TEST_NODE_MODULES to an existing dependency tree')
const ts = require(path.join(deps, 'typescript'))
const nextServer = require(path.join(deps, 'next/server'))
const checks = []
async function check(name, fn) { await fn(); checks.push(name) }

const env = { NEXT_PUBLIC_GMTM_WEB_URL: 'https://gmtm.example', NEXT_PUBLIC_BACKEND_URL: 'https://backend.example', SPARQ_ENTRY_SECRET: 'synthetic-secret' }
let fetchCalls = [], fetchReply = null
function load(rel, modules) {
  const file = path.resolve(__dirname, '../app/enter', rel)
  const code = ts.transpileModule(fs.readFileSync(file, 'utf8'), { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020 } }).outputText
  const module = { exports: {} }
  const req = id => id in modules ? modules[id] : id === 'next/server' ? nextServer : id === 'node:crypto' ? require('node:crypto') : assert.fail('unexpected import ' + id)
  new Function('exports', 'require', 'module', 'process', 'fetch', code)(module.exports, req, module, { env }, async (...args) => { fetchCalls.push(args); return fetchReply })
  return module.exports
}
const entry = load('entry.ts', {})
const start = load('route.ts', { './entry': entry })
const callback = load('callback/route.ts', { '../entry': entry, '@/lib/backend-config.cjs': policy })
const request = (url, cookie) => new nextServer.NextRequest(url, { headers: cookie ? { cookie } : {} })
const reply = (status, body) => ({ ok: status === 200, status, json: async () => body })

;(async () => {
  await check('statesMatch is exact', () => {
    assert.equal(entry.statesMatch('abc', 'abc'), true)
    for (const [a, b] of [['abc', 'abd'], ['abc', 'abcd'], [undefined, 'abc'], ['abc', null], ['', '']]) assert.equal(entry.statesMatch(a, b), false)
  })
  await check('/enter binds random state cookie and redirects to GMTM', () => {
    const res = start.GET()
    assert.equal(res.status, 302)
    const location = new URL(res.headers.get('location'))
    assert.equal(location.origin + location.pathname, 'https://gmtm.example/sparq/authorize')
    const state = location.searchParams.get('state')
    assert.match(state, /^[A-Za-z0-9_-]{43}$/)
    const cookie = res.headers.get('set-cookie')
    assert.match(cookie, new RegExp('^__Host-sparq-tx=' + state + ';'))
    for (const flag of ['Path=/', 'Max-Age=300', 'Secure', 'HttpOnly', 'SameSite=lax']) assert.ok(cookie.includes(flag), flag + ' in ' + cookie)
    assert.equal(res.headers.get('referrer-policy'), 'no-referrer')
    assert.equal(res.headers.get('cache-control'), 'no-store')
    assert.notEqual(start.GET().headers.get('location'), res.headers.get('location'))
  })
  for (const [name, url, cookie] of [
    ['state mismatch', 'https://sparq.example/enter/callback?code=c&state=other', '__Host-sparq-tx=mine'],
    ['missing cookie', 'https://sparq.example/enter/callback?code=c&state=mine', null],
    ['missing state', 'https://sparq.example/enter/callback?code=c', '__Host-sparq-tx=mine'],
    ['missing code', 'https://sparq.example/enter/callback?state=mine', '__Host-sparq-tx=mine'],
  ]) await check('Callback rejects ' + name + ' without calling the backend', async () => {
    fetchCalls = []
    const res = await callback.GET(request(url, cookie))
    assert.equal(res.headers.get('location'), 'https://sparq.example/enter/unavailable?reason=retry')
    assert.equal(fetchCalls.length, 0)
    assert.match(res.headers.get('set-cookie'), /__Host-sparq-tx=;.*Max-Age=0/)
    assert.equal(res.headers.get('cache-control'), 'no-store')
  })
  await check('Callback exchanges server to server and stores ticket in a 60 s cookie only', async () => {
    fetchCalls = []; fetchReply = reply(200, { eligible: true, ticket: 'ticket-synthetic' })
    const res = await callback.GET(request('https://sparq.example/enter/callback?code=thecode&state=mine', '__Host-sparq-tx=mine'))
    assert.equal(res.headers.get('location'), 'https://sparq.example/enter/finish')
    assert.equal(fetchCalls.length, 1)
    const [url, init] = fetchCalls[0]
    assert.equal(url, 'https://backend.example/gmtm-entry/exchange')
    assert.equal(init.headers['x-sparq-entry-secret'], 'synthetic-secret')
    assert.deepEqual(JSON.parse(init.body), { code: 'thecode', state: 'mine' })
    const cookies = res.headers.getSetCookie()
    assert.ok(cookies.some(c => /^__Host-sparq-tx=;/.test(c) && c.includes('Max-Age=0')))
    const ticket = cookies.find(c => c.startsWith('__Host-sparq-ticket='))
    for (const flag of ['__Host-sparq-ticket=ticket-synthetic;', 'Max-Age=60', 'Secure', 'HttpOnly', 'SameSite=lax', 'Path=/']) assert.ok(ticket.includes(flag), flag)
    assert.ok(!res.headers.get('location').includes('ticket'))
  })
  await check('Ineligible goes to the unavailable page with no ticket', async () => {
    fetchReply = reply(200, { eligible: false })
    const res = await callback.GET(request('https://sparq.example/enter/callback?code=thecode&state=mine', '__Host-sparq-tx=mine'))
    assert.equal(res.headers.get('location'), 'https://sparq.example/enter/unavailable')
    assert.ok(!res.headers.getSetCookie().some(c => c.startsWith('__Host-sparq-ticket=')))
  })
  for (const r of [reply(401, { detail: 'x' }), reply(503, null), reply(200, { eligible: true })]) await check('Backend failure ' + r.status + ' asks to retry', async () => {
    fetchReply = r
    const res = await callback.GET(request('https://sparq.example/enter/callback?code=thecode&state=mine', '__Host-sparq-tx=mine'))
    assert.equal(res.headers.get('location'), 'https://sparq.example/enter/unavailable?reason=retry')
  })
  await check('Athlete already linked (409) gets its own page and no ticket', async () => {
    fetchReply = reply(409, { detail: 'x' })
    const res = await callback.GET(request('https://sparq.example/enter/callback?code=thecode&state=mine', '__Host-sparq-tx=mine'))
    assert.equal(res.headers.get('location'), 'https://sparq.example/enter/unavailable?reason=linked')
    assert.ok(!res.headers.getSetCookie().some(c => c.startsWith('__Host-sparq-ticket=')))
  })
  const { completeEntry } = load('finish/complete.ts', {})
  function fakeClerk({ signedIn, status = 'complete', signOutFails = false, createFails = false }) {
    const log = []
    const clerk = {
      session: signedIn ? { id: 'sess_A' } : null,
      client: { signIn: { create: async p => { log.push(['create', p.ticket, clerk.session ? 'still-signed-in' : 'signed-out']); if (createFails) throw Error('used'); return { status, createdSessionId: status === 'complete' ? 'sess_B' : null } } } },
      signOut: async cb => { log.push(['signOut', typeof cb]); if (signOutFails) throw Error('net'); clerk.session = null; await cb() },
      setActive: async p => { log.push(['setActive', p.session]) },
    }
    return { clerk, log }
  }
  await check('Signed-in user A is signed out, then the ticket is redeemed in the same run', async () => {
    const { clerk, log } = fakeClerk({ signedIn: true })
    assert.equal(await completeEntry(clerk, 'tkt'), true)
    assert.deepEqual(log, [['signOut', 'function'], ['create', 'tkt', 'signed-out'], ['setActive', 'sess_B']])
  })
  await check('Signed-out browser redeems without sign-out', async () => {
    const { clerk, log } = fakeClerk({ signedIn: false })
    assert.equal(await completeEntry(clerk, 'tkt'), true)
    assert.deepEqual(log.map(x => x[0]), ['create', 'setActive'])
  })
  for (const [name, opts, ticket] of [['sign-out failure', { signedIn: true, signOutFails: true }, 'tkt'], ['ticket rejected', { signedIn: false, createFails: true }, 'tkt'], ['incomplete sign-in', { signedIn: false, status: 'needs_second_factor' }, 'tkt'], ['no ticket', { signedIn: true }, '']]) await check('Completion fails closed on ' + name, async () => {
    const { clerk, log } = fakeClerk(opts)
    assert.equal(await completeEntry(clerk, ticket), false)
    assert.ok(!log.some(x => x[0] === 'setActive'))
    if (opts.signOutFails) assert.ok(!log.some(x => x[0] === 'create'))
  })
  await check('Profile surface allows exactly the entry pages', () => {
    for (const p of ['/enter', '/enter/callback', '/enter/finish', '/enter/unavailable']) assert.equal(policy.candidatePagePolicy(p, 'GET', 'profile'), 'page')
    for (const p of ['/enter/other', '/enter/', '/enter/finish/x']) assert.equal(policy.candidatePagePolicy(p, 'GET', 'profile'), 'deny')
    assert.equal(policy.candidatePagePolicy('/enter', 'POST', 'profile'), 'deny')
    for (const p of ['/enter', '/enter/callback']) assert.equal(policy.candidatePagePolicy(p, 'GET', 'combine'), 'deny')
  })
  await check('Profile surface turns off sign-up; combine keeps it', () => {
    for (const p of ['/sign-up', '/sign-up/verify-email-address']) assert.equal(policy.candidatePagePolicy(p, 'GET', 'profile'), 'deny')
    assert.equal(policy.candidatePagePolicy('/sign-in', 'GET', 'profile'), 'page')
    assert.equal(policy.candidatePagePolicy('/sign-up', 'GET'), 'page')
  })
  await check('Parent notice API is profile-only GET/POST', () => {
    for (const m of ['GET', 'POST']) assert.equal(policy.resolveAPIRequest('/api/athlete/parent-notice', 'https://backend.example', 'profile', m), 'https://backend.example/api/athlete/parent-notice')
    for (const [m, s] of [['PATCH', 'profile'], ['GET', 'combine']]) assert.throws(() => policy.resolveAPIRequest('/api/athlete/parent-notice', 'https://backend.example', s, m))
    assert.throws(() => policy.resolveAPIRequest('/gmtm-entry/exchange', 'https://backend.example', 'profile', 'POST'))
  })
  console.log(JSON.stringify({ status: 'passed', checks: checks.length }))
})().catch(error => { console.error(error); process.exit(1) })
