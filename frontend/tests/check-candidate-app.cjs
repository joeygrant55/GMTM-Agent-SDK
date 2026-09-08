// Actual Next development server, product middleware/RSC and candidate ASGI app.
// Clerk identity and backend services are synthetic. All overlays live outside
// the checkout; this does not prove real Clerk, MySQL, providers or deployment.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const net = require('node:net');
const { spawn } = require('node:child_process');
const readline = require('node:readline');

const frontend = path.resolve(__dirname, '..');
const repo = path.dirname(frontend);
const output = process.env.SPARQ_CANDIDATE_ARTIFACT_DIR;
if (!output || !path.isAbsolute(output) || fs.existsSync(output)) throw Error('Set a new absolute SPARQ_CANDIDATE_ARTIFACT_DIR; existing artifacts are never overwritten.');
const realOutput = path.join(fs.realpathSync(path.dirname(output)), path.basename(output));
const outputRelative = path.relative(fs.realpathSync(repo), realOutput);
if (!outputRelative.startsWith('..' + path.sep)) throw Error('Candidate artifacts and auth overlays must remain outside the repository.');
const deps = '/Users/joey/GMTM-Agent-SDK/frontend/node_modules';
const python = '/Users/joey/GMTM-Agent-SDK/backend/.venv/bin/python';
const playwrightPath = '/Users/joey/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright';
const sourceHashes = {}, checks = [], browserErrors = [], requests = [], blockedBrowser = [];
const httpChecks = [];
let backendSourceHashes = {};
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const writeJSON = (name, value) => fs.writeFileSync(path.join(output, name), JSON.stringify(value, null, 2) + '\n', { mode: 0o600 });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const cleanPath = url => new URL(url).pathname.replace(/\/(api\/)?claims?\/[^/]+/g, '/$1claim/[token]');
let fixture, next, browser, fixtureReady, commandId = 0, ownedPorts = [];
const pendingCommands = new Map();
let nextLog = '', fixtureLog = '', nextReady = false, result = { status: 'incomplete' };

async function unusedPort() {
  const server = net.createServer();
  await new Promise((resolve, reject) => { server.once('error', reject); server.listen(0, '127.0.0.1', resolve); });
  const port = server.address().port;
  await new Promise(resolve => server.close(resolve));
  return port;
}

function snapshot(dir, relative = '') {
  const roots = new Set(['app', 'components', 'lib', 'public']);
  const configs = new Set(['package.json', 'package-lock.json', 'tsconfig.json', 'next-env.d.ts', 'middleware.ts', 'middleware.js', 'next.config.js', 'next.config.mjs', 'next.config.ts', 'postcss.config.js', 'postcss.config.mjs', 'postcss.config.cjs', 'tailwind.config.ts', 'tailwind.config.js', 'eslint.config.mjs']);
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || ['node_modules', 'tests'].includes(entry.name)) continue;
    if (!relative && !(entry.isDirectory() ? roots.has(entry.name) : configs.has(entry.name))) continue;
    if (/secret|credential|service[-_]?account|private[-_]?key/i.test(entry.name)) throw Error('Secret-like source path requires review before copying: ' + entry.name);
    const name = path.join(relative, entry.name), input = path.join(dir, entry.name), destination = path.join(output, 'frontend', name);
    if (entry.isSymbolicLink()) throw Error('Unexpected source symlink: ' + name);
    if (entry.isDirectory()) { fs.mkdirSync(destination, { recursive: true }); snapshot(input, name); }
    else if (/\.(?:[cm]?js|jsx|[cm]?ts|tsx|json|css|svg|png|jpe?g|gif|ico|webp|woff2?|ttf)$/.test(entry.name)) {
      const bytes = fs.readFileSync(input); sourceHashes[name] = sha(bytes); fs.writeFileSync(destination, bytes);
    }
  }
}

function backendHashes(dir = path.join(repo, 'backend'), relative = '', result = {}) {
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || ['__pycache__', 'node_modules', 'venv'].includes(entry.name)) continue;
    const name = path.join(relative, entry.name), input = path.join(dir, entry.name);
    if (entry.isDirectory()) backendHashes(input, name, result);
    else if (entry.isFile() && /\.(py|json)$/.test(entry.name)) result[name] = sha(fs.readFileSync(input));
  }
  return result;
}

function nodeGuard(frontPort, backPort) {
  return `const fs=require('node:fs'),net=require('node:net'),dns=require('node:dns');
const allowed=new Set([${frontPort},${backPort}]);
const local=h=>!h||h==='127.0.0.1'||h==='localhost'||h==='::1';
function denied(kind){fs.appendFileSync(${JSON.stringify(path.join(output, 'network-denials.jsonl'))},JSON.stringify({kind,pid:process.pid})+'\\n');throw Error('Candidate network boundary: '+kind)}
const connect=net.Socket.prototype.connect;
net.Socket.prototype.connect=function(...args){const options=Array.isArray(args[0])?args[0][0]:net._normalizeArgs(args)[0];if(options.path||!local(options.host)||!allowed.has(Number(options.port)))return denied('socket');return connect.apply(this,args)};
const lookup=dns.lookup;dns.lookup=function(host,...args){if(!local(host))return denied('dns');return lookup.call(this,host,...args)};
for(const name of ['resolve','resolve4','resolve6','resolveAny','resolveCname','resolveMx','resolveNs','resolvePtr','resolveSoa','resolveSrv','resolveTxt','reverse'])if(dns[name])dns[name]=()=>denied('dns-resolve');
if(dns.promises){const p=dns.promises,original=p.lookup.bind(p);p.lookup=(host,...args)=>{if(!local(host))return denied('dns-promise');return original(host,...args)};for(const name of ['resolve','resolve4','resolve6','resolveAny','resolveCname','resolveMx','resolveNs','resolvePtr','resolveSoa','resolveSrv','resolveTxt','reverse'])if(p[name])p[name]=()=>denied('dns-promise-resolve');}
const dgram=require('node:dgram');dgram.Socket.prototype.send=()=>denied('udp');dgram.Socket.prototype.connect=()=>denied('udp');
const originalFetch=globalThis.fetch;if(originalFetch)globalThis.fetch=function(input,init){const url=new URL(typeof input==='string'||input instanceof URL?input:input.url);if(!local(url.hostname)||!allowed.has(Number(url.port)))return denied('fetch');return originalFetch.call(this,input,init)};
`;
}

function authOverlays(snapshotRoot, auth) {
  const dir = path.join(snapshotRoot, '.candidate-fixture'); fs.mkdirSync(dir);
  // Only minted fixture tokens are embedded. No real Clerk key/session is read.
  fs.writeFileSync(path.join(dir, 'auth.json'), JSON.stringify({ token: auth.token, clerkId: auth.clerk_id }));
  fs.writeFileSync(path.join(dir, 'client.tsx'), `'use client'
import React,{createContext,useContext,useEffect,useState} from 'react';
import fixture from './auth.json';
const initial={isLoaded:false,user:null as any};const Context=createContext(initial);
const signedIn=()=>document.cookie.split(';').some(x=>x.trim()==='sparq_fixture_auth=signed-in');
const getToken=async()=>signedIn()?fixture.token:null;
export function ClerkProvider({children}:any){const[state,setState]=useState(initial);useEffect(()=>{const update=()=>{(window as any).Clerk={session:{getToken}};setState({isLoaded:true,user:signedIn()?{id:fixture.clerkId,firstName:'Ava',fullName:'Ava Fixture',primaryEmailAddress:{emailAddress:'athlete@example.invalid'}}:null})};update();window.addEventListener('fixture-auth-change',update);return()=>window.removeEventListener('fixture-auth-change',update)},[]);return <Context.Provider value={state}>{children}</Context.Provider>}
export function useUser(){const value=useContext(Context);return {...value,isSignedIn:!!value.user}}
export function useAuth(){const value=useUser();return{isLoaded:value.isLoaded,isSignedIn:value.isSignedIn,userId:value.user?.id,getToken}}
export function UserButton(){return <button aria-label="Fixture account">Fixture account</button>}
export function SignIn(){return <main><h1>Fixture sign in</h1></main>}
export function SignUp(){return <main><h1>Fixture sign up</h1></main>}
`);
  const realMatcher = path.join(deps, '@clerk/nextjs/dist/esm/server/routeMatcher.js');
  fs.writeFileSync(path.join(dir, 'server.ts'), `import {NextResponse} from 'next/server';
import {cookies} from 'next/headers';
import fixture from './auth.json';
export {createRouteMatcher} from ${JSON.stringify(realMatcher)};
const identity=(value:string|undefined)=>({userId:value==='signed-in'?fixture.clerkId:null,getToken:async()=>value==='signed-in'?fixture.token:null});
export function clerkMiddleware(handler:any){return async(request:any,event:any)=>{const response=(await handler(async()=>identity(request.cookies.get('sparq_fixture_auth')?.value),request,event))||NextResponse.next();response.headers.set('x-candidate-fixture-auth','called');return response}}
export async function auth(){return identity(cookies().get('sparq_fixture_auth')?.value)}
`);
  const config = path.join(snapshotRoot, 'next.config.js');
  const original = fs.readFileSync(config, 'utf8');
  fs.appendFileSync(config, `\n// External fixture overlay only; not a deployable Clerk configuration.\nconst fixtureOriginal=module.exports;module.exports={...fixtureOriginal,webpack(config,context){if(fixtureOriginal.webpack)config=fixtureOriginal.webpack(config,context);config.resolve.alias={...config.resolve.alias,'@clerk/nextjs$':${JSON.stringify(path.join(dir, 'client.tsx'))},'@clerk/nextjs/server$':${JSON.stringify(path.join(dir, 'server.ts'))}};return config}};\n`);
  writeJSON('overlays.json', { scope: 'External snapshot only; real app source and middleware bytes preserved.', originalConfigSha256: sha(original), overlaidConfigSha256: sha(fs.readFileSync(config)), aliases: ['@clerk/nextjs', '@clerk/nextjs/server'], realRouteMatcher: realMatcher, limitations: ['Fixture identity replaces Clerk session resolution; not live Clerk acceptance.', 'Next dev is actual routing/RSC/hydration, not a production build.'] });
}

async function command(op, values = {}) {
  const id = ++commandId;
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { pendingCommands.delete(id); reject(Error('Fixture command timed out: ' + op)); }, 10000);
    pendingCommands.set(id, value => { clearTimeout(timer); value.ok ? resolve(value) : reject(Error('Fixture command failed: ' + op)); });
    fixture.stdin.write(JSON.stringify({ id, op, ...values }) + '\n');
  });
}

async function waitHTTP(origin) {
  const until = Date.now() + 90000;
  while (Date.now() < until) {
    if (next.exitCode !== null || next.signalCode !== null) throw Error('Next exited before readiness');
    if (!nextReady) { await delay(200); continue; }
    try { const response = await fetch(origin + '/sign-in', { signal: AbortSignal.timeout(12000) }); if (response.status === 200) return; } catch {}
    await delay(500);
  }
  throw Error('Next route did not become ready in 90 seconds');
}

async function stop(child) {
  if (!child) return { started: false, dead: true };
  const dead = () => child.exitCode !== null || child.signalCode !== null;
  const wait = () => new Promise(resolve => {
    if (dead()) return resolve();
    const done = () => { clearTimeout(timer); child.off('exit', done); resolve(); };
    const timer = setTimeout(done, 5000); child.once('exit', done);
  });
  const signal = value => { try { process.kill(-child.pid, value); } catch (error) { if (error.code !== 'ESRCH') throw error; } };
  if (!dead()) { signal('SIGTERM'); await wait(); }
  if (!dead()) { signal('SIGKILL'); await wait(); }
  return { started: true, pid: child.pid, dead: dead(), exitCode: child.exitCode, signal: child.signalCode };
}

async function stopFixture() {
  let ipcStop = false;
  if (fixtureReady && fixture && fixture.exitCode === null && fixture.signalCode === null) {
    try {
      await command('stop'); ipcStop = true;
      const until = Date.now() + 5000;
      while (fixture.exitCode === null && fixture.signalCode === null && Date.now() < until) await delay(50);
    } catch {}
  }
  return { ...await stop(fixture), ipcStop };
}

async function portClosed(port) {
  return new Promise(resolve => {
    const socket = net.createConnection({ host: '127.0.0.1', port });
    const finish = closed => { socket.destroy(); resolve({ port, closed }); };
    socket.once('connect', () => finish(false));
    socket.once('error', error => finish(error.code === 'ECONNREFUSED'));
    socket.setTimeout(1500, () => finish(false));
  });
}

(async () => {
  fs.mkdirSync(output, { recursive: true, mode: 0o700 });
  const frontPort = await unusedPort(); let backPort = await unusedPort();
  while (backPort === frontPort) backPort = await unusedPort();
  ownedPorts = [frontPort, backPort];
  const frontOrigin = `http://127.0.0.1:${frontPort}`, backOrigin = `http://127.0.0.1:${backPort}`;
  const snapshotRoot = path.join(output, 'frontend'); fs.mkdirSync(snapshotRoot); snapshot(frontend);
  fs.symlinkSync(deps, path.join(snapshotRoot, 'node_modules'), 'dir');
  writeJSON('source-hashes.json', sourceHashes);
  backendSourceHashes = backendHashes(); writeJSON('backend-source-hashes.json', backendSourceHashes);
  const versions = {};
  for (const name of ['next', 'react', 'react-dom', '@clerk/nextjs', 'tailwindcss', 'postcss', 'typescript']) versions[name] = JSON.parse(fs.readFileSync(path.join(deps, name, 'package.json'))).version;
  writeJSON('runtime.json', { node: process.version, dependencies: deps, versions, ports: { frontend: frontPort, backend: backPort }, nextConfig: 'next.config.js (Next14 supported .js/.mjs)', duplicateNextTS: fs.existsSync(path.join(snapshotRoot, 'next.config.ts')), postcssConfig: 'postcss.config.js (before .mjs)', duplicatePostCSSMJS: fs.existsSync(path.join(snapshotRoot, 'postcss.config.mjs')) });
  const guardPath = path.join(output, 'network-guard.cjs'); fs.writeFileSync(guardPath, nodeGuard(frontPort, backPort));
  require(guardPath);
  const environment = { PATH: '/usr/bin:/bin', PYTHONDONTWRITEBYTECODE: '1', SPARQ_FIXTURE_FRONTEND_PORT: String(frontPort), SPARQ_FIXTURE_BACKEND_PORT: String(backPort), SPARQ_FIXTURE_RECEIPT: path.join(output, 'backend-receipt.json') };
  fixture = spawn(python, [path.join(repo, 'backend/tests/run_candidate_fixture.py')], { cwd: repo, env: environment, detached: true, stdio: ['pipe', 'pipe', 'pipe'] });
  fixture.stderr.on('data', data => { fixtureLog += data.toString(); });
  fixtureReady = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(Error('Backend fixture startup timed out')), 30000);
    const lines = readline.createInterface({ input: fixture.stdout });
    lines.on('line', line => {
      if (!line.startsWith('CANDIDATE_FIXTURE ')) { fixtureLog += line + '\n'; return; }
      const data = JSON.parse(line.slice('CANDIDATE_FIXTURE '.length));
      if (data.event === 'ready') { clearTimeout(timer); resolve(data); }
      if (data.event === 'command') { const done = pendingCommands.get(data.id); pendingCommands.delete(data.id); done?.(data); }
    });
    fixture.once('exit', () => { clearTimeout(timer); reject(Error('Backend fixture exited before readiness')); });
  });
  assert(fixtureReady.token && fixtureReady.claim_token && fixtureReady.clerk_id);
  authOverlays(snapshotRoot, fixtureReady);
  const nextEnvironment = { PATH: path.dirname(process.execPath) + ':/usr/bin:/bin', NODE_ENV: 'development', NODE_OPTIONS: `--require=${guardPath}`, NEXT_TELEMETRY_DISABLED: '1', NEXT_PUBLIC_APP_SURFACE: 'combine', NEXT_PUBLIC_BACKEND_URL: backOrigin, NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: 'pk_test_fixture_only', CLERK_SECRET_KEY: 'sk_test_fixture_only' };
  next = spawn(process.execPath, [path.join(deps, 'next/dist/bin/next'), 'dev', '--hostname', '127.0.0.1', '--port', String(frontPort)], { cwd: snapshotRoot, env: nextEnvironment, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
  for (const stream of [next.stdout, next.stderr]) stream.on('data', data => { nextLog += data.toString(); nextReady = nextLog.includes('Ready in'); });
  await waitHTTP(frontOrigin);
  process.stdout.write('CANDIDATE_STAGE actual Next ready\n');
  const { chromium } = require(playwrightPath);
  browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, serviceWorkers: 'block' });
  await context.route('**/*', route => {
    const url = new URL(route.request().url());
    if (![frontOrigin, backOrigin].includes(url.origin)) { blockedBrowser.push({ origin: url.origin, path: cleanPath(url.href) }); return route.abort(); }
    requests.push({ origin: url.origin === frontOrigin ? 'frontend' : 'backend', method: route.request().method(), path: cleanPath(url.href), rsc: route.request().headers()['rsc'] === '1' });
    return route.continue();
  });
  const page = await context.newPage(); page.on('pageerror', error => browserErrors.push(error.message));
  const check = (condition, label) => { assert(condition, label); checks.push(label); };
  const cookie = async signedIn => context.addCookies([{ name: 'sparq_fixture_auth', value: signedIn ? 'signed-in' : 'signed-out', url: frontOrigin }]);
  await cookie(false);
  const authRedirect = await context.request.get(frontOrigin + '/home/inbox?event_id=1318', { maxRedirects: 0 });
  check([302, 307].includes(authRedirect.status()) && authRedirect.headers().location.includes('/sign-in'), 'Actual middleware rejects a missing fixture session');
  for (const route of ['/home/colleges', '/home/profile', '/home/outreach', '/athlete/7201', '/home/colleges/private.json', '/home/artifact/123.jpg', '/_next/image?url=https%3A%2F%2Fexample.invalid%2Fphoto.jpg&w=64&q=75', '/_next/image?url=%2Fsparq-logo.jpg&w=64&q=75', '/home/%63olleges', '/home%2fcolleges', '/api/combine/current', '/api/workspace/inbox/fixture', '/trpc/private']) {
    const response = await context.request.get(frontOrigin + route, { maxRedirects: 0 });
    httpChecks.push({ path: route, method: 'GET', status: response.status(), fixtureAuthCalled: !!response.headers()['x-candidate-fixture-auth'] });
    check(response.status() === 404 && !response.headers()['x-candidate-fixture-auth'], 'Next candidate denies before fixture auth: ' + route);
  }
  for (const method of ['POST', 'PUT', 'DELETE']) {
    const response = await context.request.fetch(frontOrigin + '/api/combine/current', { method, maxRedirects: 0 });
    check(response.status() === 404 && !response.headers()['x-candidate-fixture-auth'], 'Same-origin API method rejected before fixture auth: ' + method);
  }
  const spoofed = await context.request.get(frontOrigin + '/home/colleges', { headers: { 'x-middleware-subrequest': 'middleware:middleware:middleware:middleware:middleware' }, maxRedirects: 0 });
  check(spoofed.status() === 404, 'Middleware subrequest spoof cannot expose a denied legacy page');
  for (const route of ['/api/search', '/api/profile/connect', '/api/workspace/inbox/fixture']) {
    const response = await context.request.get(backOrigin + route);
    check(response.status() === 404, 'Candidate ASGI denies ' + route);
  }
  const mintDenied = await context.request.post(backOrigin + '/api/claims/mint');
  check([404, 405].includes(mintDenied.status()), 'Candidate ASGI exposes no claim mint operation');
  await cookie(true); await command('reset', { linked: false, workspace: false, submitted: 0 });
  await page.goto(frontOrigin + '/connect?event_id=1318');
  await page.getByRole('heading', { name: 'Check your existing connection' }).waitFor();
  await page.getByText(/No existing connection was found/).waitFor();
  check(await page.getByRole('button', { name: 'Check again', exact: true }).count() === 1, 'Unlinked recovery is explicit and read-only');
  await page.goto(frontOrigin + '/claim/' + fixtureReady.claim_token);
  await page.getByRole('heading', { name: /Hey Ava, connect your profile/ }).waitFor();
  check(true, 'Actual public claim RSC fetch renders synthetic organizer invitation');
  await page.goto(frontOrigin + '/claim/' + fixtureReady.claim_token + '/redeem');
  await page.waitForURL(url => url.pathname === '/home/inbox' && url.searchParams.get('event_id') === '1318');
  await page.getByText('0 of 9 activities submitted', { exact: true }).waitFor();
  check(await page.locator('#combine-workspace-main').count() === 1, 'Actual redemption creates synthetic link and lands in the focused adult workspace');
  check(await page.getByRole('link', { name: /college|profile|outreach/i }).count() === 0, 'Focused navigation excludes legacy college/profile/outreach surfaces');
  await command('submit', { submitted: 1 });
  await page.getByRole('button', { name: 'Refresh progress', exact: true }).click();
  await page.getByText('1 of 9 activities submitted', { exact: true }).waitFor();
  check(true, 'Real browser refresh reflects one newly saved synthetic source submission');
  await page.getByRole('button', { name: 'Help with this activity', exact: true }).first().click();
  await page.getByLabel('Your combine question').fill('What should I do next?');
  await page.getByRole('button', { name: 'Send', exact: true }).click();
  await page.getByRole('log', { name: 'Combine conversation' }).getByText(/Open GMTM to finish this activity/).waitFor();
  check(true, 'Explicit help traverses actual candidate preflight and SSE with a synthetic provider');
  await page.screenshot({ path: path.join(output, 'desktop.png'), fullPage: true });
  await page.goto(frontOrigin + '/connect?event_id=1318');
  await page.waitForURL(url => url.pathname === '/home/inbox' && url.searchParams.get('event_id') === '1318');
  await page.getByText('1 of 9 activities submitted', { exact: true }).waitFor();
  check(true, 'Existing-connection recovery returns to the selected adult combine');
  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload(); await page.getByText('1 of 9 activities submitted', { exact: true }).waitFor();
  check(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), 'Actual Next phone layout has no horizontal overflow');
  await page.screenshot({ path: path.join(output, 'phone.png'), fullPage: true });
  await page.getByRole('button', { name: 'Ask SPARQ', exact: true }).click();
  await page.getByLabel('Your combine question').waitFor({ state: 'visible' });
  check(await page.getByLabel('Your combine question').isVisible(), 'Phone help opens a visible question field');
  await page.screenshot({ path: path.join(output, 'phone-help.png'), fullPage: true });
  await page.keyboard.press('Escape');
  check(await page.getByRole('button', { name: 'Ask SPARQ', exact: true }).evaluate(element => document.activeElement === element), 'Escape closes phone help and returns focus to its trigger');
  await page.getByRole('button', { name: 'Menu', exact: true }).click();
  await page.getByRole('link', { name: 'My next move', exact: true }).click();
  await page.getByText('1 of 9 activities submitted', { exact: true }).waitFor();
  check(requests.some(request => request.rsc), 'Real Next client navigation issued an RSC request');
  await command('reset', { linked: false, workspace: false, submitted: 0, workspace_failure: true });
  await page.goto(frontOrigin + '/claim/' + fixtureReady.old_claim_token + '/redeem');
  await page.waitForURL(url => url.pathname === '/home/inbox' && !url.searchParams.has('event_id'));
  await page.getByRole('heading', { name: 'Choose your USA Football combine' }).waitFor();
  check(true, 'Older-event redemption with workspace failure lands in the focused combine chooser');
  check(!requests.some(request => request.origin === 'backend' && /workspace|artifacts|badges|search|agent\//.test(request.path)), 'Focused browser never calls legacy workspace/artifact/badge/search/agent APIs');
  check(blockedBrowser.every(request => ['https://fonts.googleapis.com', 'https://fonts.gstatic.com'].includes(request.origin)), 'Browser blocks external font assets and attempts no service origin');
  check(browserErrors.length === 0, 'No browser runtime errors');
  for (const [file, hash] of Object.entries(sourceHashes)) assert(sha(fs.readFileSync(path.join(frontend, file))) === hash, 'Source changed during harness: ' + file);
  check(true, 'All captured application source bytes remain unchanged');
  result = { status: 'passed', checks, requestCount: requests.length, requests, blockedBrowser, browserErrors, sourceFileCount: Object.keys(sourceHashes).length, limits: ['Synthetic Clerk identity, SQL stores and provider response.', 'Actual Next development routing/RSC and ASGI runtime; not a production build or deployment.', 'Fixture submission update is not a real GMTM submission.'] };
})().catch(error => { result = { status: 'failed', error: error.stack, checks, requests, blockedBrowser, browserErrors }; process.exitCode = 1; }).finally(async () => {
  const cleanup = await Promise.allSettled([
    Promise.resolve().then(async () => { if (browser) await browser.close(); return { closed: true }; }),
    stop(next), stopFixture(),
  ]);
  result.cleanup = cleanup;
  result.httpChecks = httpChecks;
  if (cleanup.some(item => item.status === 'rejected' || item.value.dead === false)) { result.status = 'failed'; process.exitCode = 1; }
  result.portsAfterCleanup = await Promise.all(ownedPorts.map(portClosed));
  if (result.portsAfterCleanup.some(port => !port.closed)) { result.status = 'failed'; process.exitCode = 1; }
  const redact = text => fixtureReady ? [fixtureReady.token, fixtureReady.claim_token, fixtureReady.old_claim_token].filter(Boolean).reduce((value, token) => value.split(token).join('[synthetic-token]'), text) : text;
  if (fs.existsSync(output)) {
    const deniedPath = path.join(output, 'network-denials.jsonl');
    result.nodeNetworkDenials = fs.existsSync(deniedPath) ? fs.readFileSync(deniedPath, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse) : [];
    result.networkGuardScope = 'Node DNS/socket/fetch/UDP instrumentation plus browser request interception, not an OS firewall.';
    const backendReceipt = path.join(output, 'backend-receipt.json');
    result.backendReceiptSha256 = fs.existsSync(backendReceipt) ? sha(fs.readFileSync(backendReceipt)) : null;
    result.safetyChecks = [];
    try {
      const receipt = JSON.parse(fs.readFileSync(backendReceipt, 'utf8'));
      assert.deepEqual(receipt.forbidden_attempts, {}, 'Backend attempted a forbidden operation');
      assert.equal(receipt.real_provider_attempts, 0, 'Backend attempted a real provider');
      assert.equal(receipt.all_synthetic_connections_closed, true, 'Synthetic connections leaked');
      assert.equal(receipt.status, 'stopped', 'Backend did not stop normally');
      if (result.status === 'passed') {
        assert.equal(receipt.synthetic_help_calls, 1, 'Expected exactly one synthetic help call');
        assert(receipt.fixture_connection_count > 0, 'No synthetic SQL work observed');
        for (const route of ['GET /api/combine/current', 'POST /api/combine/help', 'GET /api/profile/by-clerk/{clerk_id}', 'GET /api/claims/{token}', 'POST /api/claims/{token}/redeem']) assert(receipt.requests_by_route_template[route] > 0, 'Actual backend route was not exercised: ' + route);
      }
      assert.deepEqual(backendHashes(), backendSourceHashes, 'Backend source changed during harness');
      for (const [file, hash] of Object.entries(sourceHashes)) assert.equal(sha(fs.readFileSync(path.join(frontend, file))), hash, 'Frontend source changed: ' + file);
      result.safetyChecks = ['Backend forbidden attempts empty', 'No real provider attempts', 'All synthetic connections closed', 'Backend stopped normally', 'Frontend and backend source hashes unchanged'];
    } catch (error) { result.status = 'failed'; result.safetyError = error.message; process.exitCode = 1; }
    if (result.nodeNetworkDenials.length || !result.backendReceiptSha256) { result.status = 'failed'; process.exitCode = 1; }
    fs.writeFileSync(path.join(output, 'next.log'), redact(nextLog)); fs.writeFileSync(path.join(output, 'fixture.log'), redact(fixtureLog));
    writeJSON('receipt.json', result);
  }
  process.stdout.write('CANDIDATE_RESULT ' + JSON.stringify({ status: result.status, checks: checks.length, receipt: path.join(output, 'receipt.json') }) + '\n');
});
