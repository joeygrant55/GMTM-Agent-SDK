// Real Next production compile and unauthenticated next-start smoke.
// Copies allowlisted, byte-identical source outside the checkout. Real Clerk
// packages stay intact; all configuration is synthetic and outbound I/O blocked.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const net = require('node:net');
const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');

const frontend = path.resolve(__dirname, '..');
const repo = path.dirname(frontend);
const surface = process.env.SPARQ_BUILD_SURFACE || 'combine';
if (!['combine', 'profile'].includes(surface)) throw Error('Unsupported build surface');
const output = process.env.SPARQ_PRODUCTION_BUILD_ARTIFACT_DIR;
if (!output || !path.isAbsolute(output) || fs.existsSync(output)) throw Error('Set a new absolute SPARQ_PRODUCTION_BUILD_ARTIFACT_DIR.');
const realOutput = path.join(fs.realpathSync(path.dirname(output)), path.basename(output));
if (!path.relative(fs.realpathSync(repo), realOutput).startsWith('..' + path.sep)) throw Error('Build artifacts must remain outside the checkout.');
const deps = '/Users/joey/GMTM-Agent-SDK/frontend/node_modules';
const snapshotRoot = path.join(output, 'frontend');
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const sourceHashes = {}, children = [], log = { build: '', start: '' }, smoke = [];
let port, interrupted = false, server;
let result = { status: 'incomplete', authOverlays: false, surface };
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const writeJSON = (name, value) => fs.writeFileSync(path.join(output, name), JSON.stringify(value, null, 2) + '\n', { mode: 0o600 });

function copySource(dir = frontend, relative = '') {
  const roots = new Set(['app', 'components', 'lib', 'public']);
  const configs = new Set(['package.json', 'package-lock.json', 'tsconfig.json', 'next-env.d.ts', 'middleware.ts', 'middleware.js', 'next.config.js', 'next.config.mjs', 'postcss.config.js', 'postcss.config.mjs', 'postcss.config.cjs', 'tailwind.config.ts', 'tailwind.config.js', 'eslint.config.mjs']);
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') || ['node_modules', 'tests'].includes(entry.name)) continue;
    if (!relative && !(entry.isDirectory() ? roots.has(entry.name) : configs.has(entry.name))) continue;
    if (/secret|credential|service[-_]?account|private[-_]?key/i.test(entry.name)) throw Error('Secret-like source path requires review: ' + entry.name);
    const name = path.join(relative, entry.name), input = path.join(dir, entry.name), destination = path.join(snapshotRoot, name);
    if (entry.isSymbolicLink()) throw Error('Unexpected source symlink: ' + name);
    if (entry.isDirectory()) { fs.mkdirSync(destination, { recursive: true }); copySource(input, name); }
    else if (/\.(?:[cm]?js|jsx|[cm]?ts|tsx|json|css|svg|png|jpe?g|gif|ico|webp|woff2?|ttf)$/.test(entry.name)) {
      const bytes = fs.readFileSync(input); sourceHashes[name] = sha(bytes); fs.writeFileSync(destination, bytes);
    }
  }
}

async function unusedPort() {
  const probe = net.createServer();
  await new Promise((resolve, reject) => { probe.once('error', reject); probe.listen(0, '127.0.0.1', resolve); });
  const value = probe.address().port;
  await new Promise(resolve => probe.close(resolve));
  return value;
}

function guardSource() {
  return `const fs=require('node:fs'),net=require('node:net'),dns=require('node:dns'),path=require('node:path');
function deny(kind){fs.appendFileSync(${JSON.stringify(path.join(output, 'denials.jsonl'))},JSON.stringify({kind,pid:process.pid})+'\\n');throw Error('Production build boundary: '+kind)}
const local=h=>h==='127.0.0.1'||h==='localhost'||h==='::1';
const connect=net.Socket.prototype.connect;net.Socket.prototype.connect=function(...args){const o=Array.isArray(args[0])?args[0][0]:net._normalizeArgs(args)[0];if(o.path||!local(o.host||'localhost')||Number(o.port)!==${port})return deny('socket');return connect.apply(this,args)};
const lookup=dns.lookup;dns.lookup=function(host,...args){if(!local(host))return deny('dns');return lookup.call(this,host,...args)};
const methods=['resolve','resolve4','resolve6','resolveAny','resolveCname','resolveMx','resolveNs','resolvePtr','resolveSoa','resolveSrv','resolveTxt','reverse'];for(const name of methods)if(dns[name])dns[name]=()=>deny('dns-resolve');
if(dns.promises){const p=dns.promises,lookup=p.lookup.bind(p);p.lookup=(host,...args)=>{if(!local(host))return deny('dns-promise');return lookup(host,...args)};for(const name of methods)if(p[name])p[name]=()=>deny('dns-promise-resolve');}
const dgram=require('node:dgram');dgram.Socket.prototype.send=dgram.Socket.prototype.connect=()=>deny('udp');
const fetch=globalThis.fetch;if(fetch)globalThis.fetch=function(input,init){const u=new URL(typeof input==='string'||input instanceof URL?input:input.url);if(!local(u.hostname)||Number(u.port)!==${port})return deny('fetch');return fetch.call(this,input,init)};
function checkFile(value){if(typeof value==='string'||value instanceof URL){const name=value instanceof URL?value.pathname:value;if(path.basename(name).startsWith('.env'))deny('env-file-read');}}
for(const key of ['readFileSync','readFile','openSync','open']){const original=fs[key];fs[key]=function(file,...args){checkFile(file);return original.call(this,file,...args)}}
for(const key of ['readFile','open']){const original=fs.promises[key].bind(fs.promises);fs.promises[key]=function(file,...args){checkFile(file);return original(file,...args)}}
`;
}

const dead = child => !child || child.exitCode !== null || child.signalCode !== null;
function groupAlive(child) {
  if (!child?.pid) return false;
  try { process.kill(-child.pid, 0); return true; } catch (error) { if (error.code === 'ESRCH') return false; throw error; }
}
function signal(child, name) {
  if (!child?.pid) return;
  try { process.kill(-child.pid, name); } catch (error) { if (error.code !== 'ESRCH') throw error; }
}
async function stop(child) {
  if (!child) return { started: false, dead: true };
  for (const name of ['SIGTERM', 'SIGKILL']) {
    if (dead(child) && !groupAlive(child)) break;
    signal(child, name);
    const until = Date.now() + 5000;
    while ((!dead(child) || groupAlive(child)) && Date.now() < until) await delay(50);
  }
  return { pid: child.pid, dead: dead(child), groupDead: !groupAlive(child), exitCode: child.exitCode, signal: child.signalCode };
}
for (const name of ['SIGINT', 'SIGTERM']) process.once(name, () => {
  interrupted = true; process.exitCode = 130;
  children.forEach(child => signal(child, 'SIGTERM'));
  setTimeout(() => children.forEach(child => signal(child, 'SIGKILL')), 3000).unref();
});

function startChild(phase, args, env) {
  if (interrupted) throw Error('Verification interrupted');
  const child = spawn(process.execPath, [path.join(deps, 'next/dist/bin/next'), ...args], { cwd: snapshotRoot, env, detached: true, stdio: ['ignore', 'pipe', 'pipe'] });
  children.push(child);
  child.on('error', error => { log[phase] += `\nChild startup error: ${error.code || error.name}\n`; });
  for (const stream of [child.stdout, child.stderr]) stream.on('data', data => {
    log[phase] += data.toString();
    fs.writeFileSync(path.join(output, `${phase}.log`), log[phase]);
    if (phase === 'build' && data.toString().includes('Compiled successfully')) process.stdout.write('PRODUCTION_BUILD_STAGE webpack-compiled\n');
  });
  writeJSON('owned-processes.json', { port, children: children.map(item => ({ pid: item.pid })) });
  return child;
}

async function waitExit(child, timeout) {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => { signal(child, 'SIGTERM'); reject(Error('Production build exceeded its time budget')); }, timeout);
    child.once('error', error => { clearTimeout(timer); reject(error); });
    child.once('exit', (code, signal) => { clearTimeout(timer); resolve({ code, signal }); });
  });
}

async function waitReady(child) {
  const until = Date.now() + 30000;
  while (Date.now() < until) {
    if (dead(child)) throw Error('Production server exited before readiness');
    if (log.start.includes('Ready in')) return;
    await delay(100);
  }
  throw Error('Production server did not become ready');
}

async function portClosed() {
  if (!port) return null;
  return new Promise(resolve => {
    const socket = net.createConnection({ host: '127.0.0.1', port });
    const finish = closed => { socket.destroy(); resolve(closed); };
    socket.once('connect', () => finish(false));
    socket.once('error', error => finish(error.code === 'ECONNREFUSED'));
    socket.setTimeout(1500, () => finish(false));
  });
}

(async () => {
  fs.mkdirSync(output, { recursive: true, mode: 0o700 }); fs.mkdirSync(snapshotRoot);
  const harness = fs.readFileSync(__filename); fs.writeFileSync(path.join(output, 'harness.cjs'), harness);
  copySource(); fs.symlinkSync(deps, path.join(snapshotRoot, 'node_modules'), 'dir');
  port = await unusedPort();
  writeJSON('source-hashes.json', sourceHashes);
  const versions = {};
  for (const name of ['next', 'react', 'react-dom', '@clerk/nextjs', 'tailwindcss', 'postcss', 'typescript']) versions[name] = JSON.parse(fs.readFileSync(path.join(deps, name, 'package.json'))).version;
  writeJSON('runtime.json', { node: process.version, executable: process.execPath, dependencies: deps, versions, originalConfigHash: sourceHashes['next.config.js'], harnessSha256: sha(harness), authOverlays: false, port });
  const guardPath = path.join(output, 'guard.cjs'); fs.writeFileSync(guardPath, guardSource()); require(guardPath);
  const env = { PATH: path.dirname(process.execPath) + ':/usr/bin:/bin', NODE_ENV: 'production', NODE_OPTIONS: `--require=${guardPath}`, NEXT_TELEMETRY_DISABLED: '1', NEXT_PUBLIC_APP_SURFACE: surface, NEXT_PUBLIC_BACKEND_URL: 'https://candidate-backend.example.invalid', NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY: 'pk_test_' + Buffer.from('clerk.example.invalid$').toString('base64'), CLERK_SECRET_KEY: 'sk_test_synthetic_build_only_not_a_credential' };
  process.stdout.write('PRODUCTION_BUILD_STAGE compile-started\n');
  const build = startChild('build', ['build'], env);
  const buildExit = await waitExit(build, 240000);
  result.buildExit = buildExit;
  if (interrupted) throw Error('Verification interrupted');
  if (buildExit.code !== 0) throw Error('Unmodified Next production build failed; see build.log');
  const manifests = {};
  for (const name of ['BUILD_ID', 'routes-manifest.json', 'prerender-manifest.json', 'build-manifest.json', 'server/middleware-manifest.json', 'server/app-paths-manifest.json']) {
    const file = path.join(snapshotRoot, '.next', name); assert(fs.existsSync(file), 'Missing production output ' + name); manifests[name] = sha(fs.readFileSync(file));
  }
  result.productionManifests = manifests;
  process.stdout.write('PRODUCTION_BUILD_STAGE compile-passed; unauthenticated-smoke-started\n');
  server = startChild('start', ['start', '--hostname', '127.0.0.1', '--port', String(port)], env);
  await waitReady(server);
  const origin = `http://127.0.0.1:${port}`;
  for (const route of ['/home/colleges', '/home/artifact/123.jpg', '/api/combine/current', '/api/demo-chat', '/_next/image?url=%2Fsparq-logo.jpg&w=64&q=75']) {
    const response = await fetch(origin + route, { redirect: 'manual', signal: AbortSignal.timeout(10000) });
    smoke.push({ path: route, status: response.status }); assert.equal(response.status, 404, 'Production route boundary: ' + route);
  }
  const response = await fetch(origin + '/home/inbox?event_id=1318', { redirect: 'manual', signal: AbortSignal.timeout(10000) });
  const location = response.headers.get('location');
  smoke.push({ path: '/home/inbox?event_id=1318', status: response.status, redirectPath: location ? new URL(location, origin).pathname : null });
  if (![302, 303, 307, 308].includes(response.status) || !location || new URL(location, origin).pathname !== '/sign-in') throw Error('Real Clerk unauthenticated redirect unconfirmed; inspect start.log and denials.');
  result.status = 'passed';
})().catch(error => { result.status = interrupted ? 'interrupted' : 'failed'; result.error = error.message; process.exitCode = 1; }).finally(async () => {
  result.cleanup = await Promise.allSettled(children.map(stop));
  result.portClosedAfterCleanup = await portClosed();
  result.smoke = smoke;
  result.sourceChangedDuringRun = Object.entries(sourceHashes).filter(([name, hash]) => sha(fs.readFileSync(path.join(frontend, name))) !== hash).map(([name]) => name);
  result.snapshotInputsChangedByBuild = Object.entries(sourceHashes).filter(([name, hash]) => sha(fs.readFileSync(path.join(snapshotRoot, name))) !== hash).map(([name]) => name);
  const denialPath = path.join(output, 'denials.jsonl');
  result.denials = fs.existsSync(denialPath) ? fs.readFileSync(denialPath, 'utf8').trim().split('\n').filter(Boolean).map(JSON.parse) : [];
  if (result.denials.length || result.sourceChangedDuringRun.length || result.snapshotInputsChangedByBuild.length || result.portClosedAfterCleanup === false || result.cleanup.some(item => item.status === 'rejected' || !item.value.dead || !item.value.groupDead)) { result.status = 'failed'; process.exitCode = 1; }
  result.limits = ['Real Next production build/start with real Clerk packages and synthetic configuration; no signed-in production journey or live identity/database/provider acceptance.', 'Network instrumentation is not an OS firewall. The retained build points to a deliberately nonexistent backend and is not a deployment artifact.', 'Uses the existing explicitly recorded dependency tree, not a fresh lockfile installation.'];
  if (fs.existsSync(output)) { fs.writeFileSync(path.join(output, 'build.log'), log.build); fs.writeFileSync(path.join(output, 'start.log'), log.start); writeJSON('receipt.json', result); }
  process.stdout.write('PRODUCTION_BUILD_RESULT ' + JSON.stringify({ status: result.status, buildExit: result.buildExit, receipt: path.join(output, 'receipt.json') }) + '\n');
});
