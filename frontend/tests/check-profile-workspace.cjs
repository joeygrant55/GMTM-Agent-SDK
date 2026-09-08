// Actual source components, React and API transport in an intercepted browser.
// No application server, real auth/data/provider, installation, or full Next/layout claim.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const net = require('node:net');
const frontend = path.resolve(__dirname, '..');
const deps = process.env.SPARQ_TEST_NODE_MODULES;
const playwrightPath = process.env.SPARQ_TEST_PLAYWRIGHT;
const receiptPath = process.env.SPARQ_TEST_RECEIPT;
if (!deps || !playwrightPath || !receiptPath) throw Error('Set explicit SPARQ_TEST_NODE_MODULES, SPARQ_TEST_PLAYWRIGHT and SPARQ_TEST_RECEIPT.');
if (fs.existsSync(receiptPath)) throw Error('Refusing to overwrite an existing receipt.');
const lifecyclePath = receiptPath + '.lifecycle.jsonl';
if (fs.existsSync(lifecyclePath)) throw Error('Refusing to overwrite existing lifecycle evidence.');
const startedAt = Date.now(), runId = crypto.randomUUID(), runBudgetMs = 90000, cleanupBudgetMs = 60000;
let browser, browserServer, browserLaunch, browserProcess, browserPort, released = false;
let stopping = false, interruption = null, runTimer, cleanupTimer, rejectInterrupted, outcome = { status: 'incomplete' };
const interrupted = new Promise((_, reject) => { rejectInterrupted = reject; });
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
function lifecycle(event, detail = {}) {
  const fd = fs.openSync(lifecyclePath, 'a', 0o600);
  try { fs.writeSync(fd, JSON.stringify({ at: new Date().toISOString(), runId, harnessPid: process.pid, event, ...detail }) + '\n'); fs.fsyncSync(fd); }
  finally { fs.closeSync(fd); }
}
function assertRunning() { if (stopping) throw Error(interruption || 'Component verification is stopping'); }
function groupAlive() {
  if (!browserProcess?.pid || released) return false;
  try { process.kill(-browserProcess.pid, 0); return true; }
  catch (error) { if (error.code === 'ESRCH') return false; throw error; }
}
function signalBrowser(signal) {
  if (!browserProcess?.pid || released) return;
  try { process.kill(-browserProcess.pid, signal); lifecycle('owned_group_signalled', { role: 'chromium', pgid: browserProcess.pid, signal }); }
  catch (error) { if (error.code !== 'ESRCH') throw error; }
}
function interrupt(reason) {
  if (stopping) return;
  stopping = true; interruption = reason;
  lifecycle('interrupted', { reason }); rejectInterrupted(Error(reason));
}
for (const name of ['SIGINT', 'SIGTERM', 'SIGHUP']) process.on(name, () => interrupt('Received ' + name));
process.on('exit', () => { try { if (groupAlive()) signalBrowser('SIGKILL'); } catch {} });
async function within(promise, timeout, label) {
  let timer;
  try { return await Promise.race([promise, new Promise((_, reject) => { timer = setTimeout(() => reject(Error(label + ' timed out')), timeout); })]); }
  finally { clearTimeout(timer); }
}
function writeReceipt() {
  fs.writeFileSync(receiptPath, JSON.stringify({ ...outcome, lifecycle: { runId, harnessPid: process.pid, browserPid: browserProcess?.pid || null, browserPort, runBudgetMs, cleanupBudgetMs, elapsedMs: Date.now() - startedAt, interruption, evidence: lifecyclePath, scope: 'Only this invocation\'s ephemeral Chromium POSIX group and loopback control port. External SIGKILL, host shutdown or a blocked JS event loop require an external supervisor.' } }, null, 2) + '\n', { mode: 0o600 });
}
function emergencyStop(error) {
  outcome = { ...outcome, status: 'failed', lifecycleError: error, cleanupVerified: false };
  try { if (groupAlive()) signalBrowser('SIGKILL'); } catch {}
  lifecycle('emergency_cleanup', { error, verifiedComplete: false }); writeReceipt(); process.exit(1);
}
async function cleanupBrowser() {
  const closeErrors = [];
  if (browserLaunch) { try { await within(browserLaunch, 35000, 'Browser launch settlement'); } catch (error) { closeErrors.push(error.message); } }
  if (browser) { try { await within(browser.close(), 5000, 'Browser close'); } catch (error) { closeErrors.push(error.message); } }
  if (browserServer) { try { await within(browserServer.close(), 5000, 'Browser server close'); } catch (error) { closeErrors.push(error.message); } }
  const leaderDead = () => !browserProcess || browserProcess.exitCode !== null || browserProcess.signalCode !== null;
  for (const signal of ['SIGTERM', 'SIGKILL']) {
    if (leaderDead() && !groupAlive()) break;
    signalBrowser(signal);
    const until = Date.now() + 5000;
    while ((!leaderDead() || groupAlive()) && Date.now() < until) await delay(50);
  }
  const cleanup = { role: 'chromium', pid: browserProcess?.pid || null, pgid: browserProcess?.pid || null, dead: leaderDead(), groupDead: !groupAlive(), closed: !browser?.isConnected(), ownershipConfirmed: !browserLaunch || !!browserProcess, closeErrors };
  if (cleanup.groupDead) released = true;
  cleanup.portClosed = !browserPort || await new Promise(resolve => {
    const socket = net.createConnection({ host: '127.0.0.1', port: browserPort });
    const finish = closed => { socket.destroy(); resolve(closed); };
    socket.once('connect', () => finish(false));
    socket.once('error', error => finish(error.code === 'ECONNREFUSED'));
    socket.setTimeout(1500, () => finish(false));
  });
  lifecycle('owned_process_cleanup', cleanup);
  return cleanup;
}
const ts = require(path.join(deps, 'typescript'));
const { chromium } = require(playwrightPath);
const sourceHashes = {};
const files = ['app/home/components/ProfileWorkspace.tsx', 'app/home/components/ProfileWorkspaceShell.tsx', 'app/home/components/profileEvidence.ts', 'app/home/components/ProfileMaterialsPanel.tsx', 'app/home/components/profileMaterials.ts', 'app/_lib/api.ts', 'lib/backend-config.cjs'];
let bundle = "const process={env:{NODE_ENV:'development',NEXT_PUBLIC_APP_SURFACE:'profile',NEXT_PUBLIC_BACKEND_URL:'http://127.0.0.1:4321'}};const modules={},cache={};\n";
for (const file of files) {
  const source = fs.readFileSync(path.join(frontend, file), 'utf8');
  sourceHashes[file] = crypto.createHash('sha256').update(source).digest('hex');
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true }}).outputText;
  bundle += `modules[${JSON.stringify(file.replace(/\.tsx?$/, ''))}]=function(require,module,exports){\n${code}\n};\n`;
}
bundle += `
window.__identity={isLoaded:true,user:{id:'athlete-a'}};window.__listeners=new Set();
window.__setIdentity=value=>{window.__identity=value;window.__listeners.forEach(fn=>fn())};
const useUser=()=>React.useSyncExternalStore(fn=>{window.__listeners.add(fn);return()=>window.__listeners.delete(fn)},()=>window.__identity);
window.Clerk={session:{getToken:async()=>window.__identity.user?'fixture-'+window.__identity.user.id:null}};
window.__requests=[];window.__pending=[];window.__mode={};window.__materialsMode={};window.__clipboard=[];window.__clipboardMode='success';window.__copyPending=[];
Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.__clipboard.push(text);if(window.__clipboardMode==='failure')throw Error('Fixture clipboard denial');if(window.__clipboardMode==='pending')return new Promise(resolve=>window.__copyPending.push(resolve))}}});
window.__now=1000000;window.__timers=new Map();let timerId=0;
window.setTimeout=(fn,ms=0,...args)=>{const id=++timerId;window.__timers.set(id,{at:window.__now+ms,fn:()=>fn(...args)});return id};
window.clearTimeout=id=>window.__timers.delete(id);
window.__advance=async ms=>{const end=window.__now+ms;for(const[id,t]of [...window.__timers]){if(t.at<=end){window.__timers.delete(id);t.fn();for(let n=0;n<15;n++)await Promise.resolve()}}window.__now=end};
function reply(mode={},request){if(mode.reject)throw Error('Fixture network failure');const response=new Response(mode.badJSON?'malformed-json':JSON.stringify(mode.body),{status:mode.status||200,headers:{'content-type':'application/json'}});if(mode.bodyPending)response.json=()=>new Promise(resolve=>window.__pending.push({stage:'body',resolve,request}));return response}
window.fetch=async(input,init={})=>{const u=new URL(String(input),location.origin);if(u.origin!==location.origin||!['/api/athlete/evidence','/api/athlete/materials'].includes(u.pathname)||u.search||(init.method||'GET')!=='GET')throw Error('Unexpected endpoint '+u);const request={path:u.pathname,method:init.method||'GET',signal:init.signal,authorization:new Headers(init.headers).get('Authorization'),cache:init.cache};window.__requests.push(request);const mode=u.pathname==='/api/athlete/materials'?window.__materialsMode:window.__mode;if(mode.pending)return new Promise(resolve=>window.__pending.push({stage:'response',resolve,request}));return reply(mode,request)};
window.__release=(mode={},path)=>{const index=path?window.__pending.findIndex(p=>p.request?.path===path):0;const pending=index>=0?window.__pending.splice(index,1)[0]:null;if(!pending)throw Error('No pending read');pending.resolve(pending.stage==='body'?mode.body:reply(mode,pending.request))};
const jsx=(type,props,key)=>React.createElement(type,{...props,...(key!==undefined?{key}:{})});
function load(id,from=''){
 if(id==='react')return React;
 if(id==='react/jsx-runtime')return{jsx,jsxs:jsx,Fragment:React.Fragment};
 if(id==='@clerk/nextjs')return{useUser,UserButton:()=>React.createElement('button',{'aria-label':'Fixture account'},'Account')};
 if(id==='next/link')return{__esModule:true,default:({children,...props})=>React.createElement('a',props,children)};
 if(id.startsWith('@/'))id=id.slice(2);else if(id.startsWith('.')){const parts=(from.slice(0,from.lastIndexOf('/')+1)+id).split('/'),out=[];for(const part of parts){if(part==='..')out.pop();else if(part!=='.')out.push(part)}id=out.join('/')}
 if(cache[id])return cache[id].exports;const m={exports:{}};cache[id]=m;if(!modules[id])throw Error('Missing module '+id);modules[id](x=>load(x,id),m,m.exports);return m.exports;
}
window.__helpers=load('app/home/components/profileEvidence');
window.__materialHelpers=load('app/home/components/profileMaterials');
const root=ReactDOM.createRoot(document.getElementById('root'));
window.__mount=(strict=false)=>{const app=React.createElement(load('app/home/components/ProfileWorkspaceShell').default,null,React.createElement(load('app/home/components/ProfileWorkspace').default));root.render(strict?React.createElement(React.StrictMode,null,app):app)};
window.__unmount=()=>root.render(null);
`;
const origin = 'http://127.0.0.1:4321';
const assets = {
  '/': '<!doctype html><html><head><meta charset="utf-8"></head><body><div id="root"></div><script src="/react.js"></script><script src="/react-dom.js"></script><script src="/app.js"></script></body></html>',
  '/react.js': fs.readFileSync(path.join(deps, 'react/umd/react.development.js'), 'utf8'),
  '/react-dom.js': fs.readFileSync(path.join(deps, 'react-dom/umd/react-dom.development.js'), 'utf8'),
  '/app.js': bundle,
};
const athlete = name => ({ name, sport: 'Flag football', position: 'Receiver', school: 'Fixture School', city: 'Fixture City', state: 'FL', graduation_year: null });
const result = (id, label, value) => ({ id, label, value, unit: 'seconds', recorded_at: '2026-08-20T00:00:00Z', source_label: 'Recorded GMTM metric', verification: 'unconfirmed', event_name: 'Fixture Adult Combine' });
const profile = (name='Alex Fixture') => ({ state: 'ready', athlete: athlete(name), evidence: [result('m1','20-yard dash',3.12),result('m2','Three-cone drill',7.34)], observations: [{ title: 'Two recorded results', detail: 'These records have a source and a date. They do not establish selection.', evidence_ids:['m1','m2'] }], limitations: ['Verification has not been confirmed.'], fetched_at:'2026-09-08T17:00:00Z' });
const emptyState = state => ({ state, athlete:null, evidence:[], observations:[], limitations:[], fetched_at:'2026-09-08T17:00:00Z' });
const materialResult = (id='submission-1', extra={}) => ({id,kind:'submitted_result',title:'Submitted sprint',source_label:'Fixture combine · Sprint exercise',recorded_at:'2026-08-21T12:00:00',date_label:'Submitted',result:{value:4.8,unit:'seconds'},source_url:null,can_include:true,availability:'recorded',...extra});
const materialFilm = (id='film-12', extra={}) => ({id,kind:'footage',title:'Game footage',source_label:'GMTM footage record',recorded_at:'2026-08-22',date_label:'Published',result:null,source_url:'https://gmtm.com/film/12',can_include:true,availability:'unchecked',...extra});
const materials = (items=[],state='ready') => ({state,items,limitations:['Only supported existing records are in this view.'],fetched_at:'2026-09-08T17:00:00Z'});
const checks=[], errors=[], denied=[];
const work = (async()=>{
    lifecycle('run_started', { runBudgetMs, cleanupBudgetMs });
    runTimer = setTimeout(() => interrupt('Component verification exceeded its 90-second run budget'), Math.max(1, runBudgetMs - (Date.now() - startedAt)));
    assert(process.platform !== 'win32', 'Owned process-group cleanup requires POSIX');
    assertRunning();
    browserLaunch = chromium.launchServer({ headless:true, host:'127.0.0.1', port:0, timeout:30000, handleSIGINT:false, handleSIGTERM:false, handleSIGHUP:false }).then(server => {
      browserServer = server; browserProcess = server.process(); browserPort = Number(new URL(server.wsEndpoint()).port);
      assert(Number.isSafeInteger(browserProcess?.pid) && browserProcess.pid > 1, 'Browser ownership unavailable');
      lifecycle('owned_process_started', { role:'chromium', pid:browserProcess.pid, pgid:browserProcess.pid, port:browserPort });
      browserProcess.once('exit', (code, signal) => lifecycle('owned_leader_exited', { role:'chromium', pid:browserProcess.pid, code, signal }));
      return server;
    });
    await browserLaunch; assertRunning();
    browser = await chromium.connect({ wsEndpoint:browserServer.wsEndpoint(), timeout:10000 }); assertRunning();
    const context=await browser.newContext({serviceWorkers:'block',timezoneId:'America/Los_Angeles'});
    context.setDefaultTimeout(10000); context.setDefaultNavigationTimeout(10000);
    const page=await context.newPage();page.on('pageerror',e=>errors.push(String(e)));
    await context.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==origin||!(u.pathname in assets)){denied.push(u.origin+u.pathname);return route.abort()}return route.fulfill({status:200,contentType:u.pathname.endsWith('.js')?'application/javascript':'text/html',body:assets[u.pathname]})});
    const check=(condition,name)=>{assert(condition,name);checks.push(name)};
    const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const reset=async(mode={body:profile()},identity={isLoaded:true,user:{id:'athlete-a'}},strict=false,materialMode={body:materials()})=>{await page.goto(origin);await page.evaluate(({mode,identity,strict,materialMode})=>{window.__mode=mode;window.__materialsMode=materialMode;window.__setIdentity(identity);window.__mount(strict)},{mode,identity,strict,materialMode});await settle()};
    const ready=()=>page.getByRole('heading',{name:'What your profile records',exact:true}).waitFor();
    const setMode=async mode=>page.evaluate(mode=>{window.__mode=mode},mode);
    const setMaterialsMode=async mode=>page.evaluate(mode=>{window.__materialsMode=mode},mode);
    const switchAccount=async id=>{await page.evaluate(id=>window.__setIdentity({isLoaded:true,user:id?{id}:null}),id);await settle()};
    const release=async mode=>{await page.evaluate(mode=>window.__release(mode),mode);await settle()};
    const releaseMaterials=async mode=>{await page.evaluate(mode=>window.__release(mode,'/api/athlete/materials'),mode);await settle()};
    const goal=()=>page.getByLabel('What are you working toward?',{exact:true});
    const draft=()=>page.getByLabel('Your text — ready to edit',{exact:true});
    const prepare=()=>page.getByRole('button',{name:'Prepare my text',exact:true}).click();

    await reset();await ready();
    check(await page.getByRole('heading',{name:'Alex Fixture',exact:true}).isVisible(),'Ready profile displays the current source identity');
    check(await page.getByRole('checkbox').count()===2&&await page.locator('input[type=checkbox]:checked').count()===0,'Only real returned evidence appears and selection is explicit');
    check(await page.getByText('3.12 seconds',{exact:true}).isVisible()&&await page.getByText(/Recorded GMTM metric · Aug 20, 2026/).count()===2,'Results retain exact value, unit, source and date');
    check(await page.getByText('Two recorded results',{exact:true}).isVisible()&&await page.getByText('Based on: 20-yard dash, Three-cone drill',{exact:true}).isVisible(),'Backend observations retain evidence attribution');
    check(await page.getByRole('button',{name:'Prepare my text',exact:true}).isDisabled(),'A real stated goal is required before output preparation');
    check(await page.evaluate(()=>window.__requests.length===2&&window.__requests.map(r=>r.path).join(',')==='/api/athlete/evidence,/api/athlete/materials'&&window.__requests.every(r=>r.authorization==='Bearer fixture-athlete-a'&&r.cache==='no-store'&&r.method==='GET')),'Only the two authenticated no-store evidence GETs run, without caller athlete IDs');
    check(await page.getByRole('navigation').count()===0&&await page.getByRole('textbox').count()===2&&await page.getByRole('heading',{name:'Combine help'}).count()===0,'Shell has no task navigation, chat panel or additional workspace request');

    await page.getByRole('checkbox').first().check();await goal().fill('Prepare for a specific adult team trial');await page.getByLabel('Intended use (optional)',{exact:true}).fill('My trial application');await prepare();
    let output=await draft().inputValue();
    check(output.includes('Alex Fixture')&&output.includes('20-yard dash: 3.12 seconds')&&!output.includes('Three-cone drill'),'Prepared text uses the athlete and selected evidence only');
    check(output.includes('Recorded GMTM metric')&&output.includes('Aug 20, 2026')&&output.includes('Measurement verification is unconfirmed'),'Copied-ready evidence retains provenance and uncertainty');
    check(output.includes('My trial application')&&output.includes('Prepare for a specific adult team trial')&&!output.includes('https://'),'Summary reflects the real goal/use without inventing a public profile link');
    await draft().fill('My exact edited introduction.\nSecond line <literal> & punctuation.');await page.getByRole('button',{name:'Copy text',exact:true}).click();await page.getByText('Copied to clipboard. Nothing has been sent.',{exact:true}).waitFor();
    check(await page.evaluate(()=>window.__clipboard.at(-1))==='My exact edited introduction.\nSecond line <literal> & punctuation.','Copy sends the exact current edited plain text to the clipboard');
    await page.getByRole('checkbox').nth(1).check();
    check(await page.getByText(/Your selections changed/).isVisible()&&(await draft().inputValue()).startsWith('My exact edited'),'Selection changes do not silently replace athlete edits');
    await page.getByRole('button',{name:'Rebuild from these details',exact:true}).click();
    check((await draft().inputValue()).includes('Three-cone drill: 7.34 seconds'),'Explicit rebuild picks up the changed selection');
    await page.getByLabel('Introduction',{exact:true}).check();
    check(await page.getByLabel('Who is this for?',{exact:true}).inputValue()===''&&await page.getByRole('button',{name:'Rebuild from these details'}).isDisabled(),'Introduction requires an explicitly provided recipient, not the earlier intended-use text');
    await page.getByLabel('Who is this for?',{exact:true}).fill('Coach Fixture');await page.getByRole('button',{name:'Rebuild from these details'}).click();
    check((await draft().inputValue()).startsWith('Hello Coach Fixture,')&&!(await draft().inputValue()).includes('guaranteed'),'Introduction names only the recipient supplied by the athlete');
    check(await page.evaluate(()=>window.__requests.length===2&&window.__requests.map(r=>r.path).join(',')==='/api/athlete/evidence,/api/athlete/materials'&&localStorage.length===0&&sessionStorage.length===0),'Selection, preparation, editing and copying add no API calls beyond the two initial reads and persist no browser storage');

    await page.evaluate(()=>{window.__clipboardMode='failure'});await page.getByRole('button',{name:'Copy text',exact:true}).click();await page.getByText(/Clipboard access is unavailable/).waitFor();
    check(await page.getByText('Copied to clipboard. Nothing has been sent.',{exact:true}).count()===0,'Clipboard denial never reports copy success');
    await page.getByRole('button',{name:'Select all text',exact:true}).click();
    check(await draft().evaluate(el=>document.activeElement===el&&el.selectionStart===0&&el.selectionEnd===el.value.length),'Manual fallback selects the entire current editable text');
    await page.evaluate(()=>{Object.defineProperty(navigator,'clipboard',{configurable:true,value:undefined})});await page.getByRole('button',{name:'Copy text',exact:true}).click();await page.getByText(/Clipboard access is unavailable/).waitFor();
    check(await page.getByText(/Clipboard access is unavailable/).isVisible(),'Unavailable clipboard API gets the same honest manual fallback');

    await reset();await ready();await goal().fill('An actual goal');await prepare();await page.evaluate(()=>{window.__clipboardMode='pending'});await page.getByRole('button',{name:'Copy text',exact:true}).click();await draft().fill('A newer edited version');await page.evaluate(()=>window.__copyPending.shift()());await settle();
    check(await page.getByText('Copied to clipboard. Nothing has been sent.',{exact:true}).count()===0&&(await draft().inputValue())==='A newer edited version','Late clipboard completion cannot claim that a newly edited version was copied');
    await setMode({pending:true});await page.getByRole('button',{name:'Refresh profile',exact:true}).click();await settle();
    check(await draft().count()===0&&await page.getByRole('button',{name:'Copy text',exact:true}).count()===0,'Starting a source refresh immediately removes the old draft and copy action');
    await release({body:profile()});await ready();
    await setMode({body:profile('Blair Fixture')});await switchAccount('athlete-b');await ready();
    check(await draft().count()===0&&(await goal().inputValue())===''&&await page.getByRole('heading',{name:'Alex Fixture',exact:true}).count()===0,'Account switch immediately removes the old identity, goal and draft');
    check(await page.evaluate(()=>window.__requests.at(-1).authorization)==='Bearer fixture-athlete-b','New account loads with its own credential');

    for (const pendingMode of [{pending:true},{bodyPending:true,body:profile()}]) {
      await reset(pendingMode);await setMode({body:profile('Blair Fixture')});await switchAccount('athlete-b');await ready();await release({body:profile('PRIVATE OLD ATHLETE')});
      check(await page.getByRole('heading',{name:'Blair Fixture',exact:true}).isVisible()&&await page.getByText('PRIVATE OLD ATHLETE',{exact:true}).count()===0&&await page.evaluate(()=>window.__requests[0].signal.aborted),'Late '+(pendingMode.pending?'response':'body')+' cannot enter the new account');
    }
    await reset({pending:true});await switchAccount(null);await release({body:profile('PRIVATE LOGGED OUT ATHLETE')});
    check(await page.getByRole('heading',{name:'Your profile is private.',exact:true}).isVisible()&&await page.getByText('PRIVATE LOGGED OUT ATHLETE',{exact:true}).count()===0,'Logout cancels the read and hides private profile evidence');
    await reset({body:profile()},{isLoaded:false,user:null});
    check(await page.getByText('Loading your account…',{exact:true}).isVisible()&&await page.evaluate(()=>window.__requests.length)===0,'No profile fetch occurs before Clerk account readiness');

    for (const [status,title] of [[401,'Please sign in again.'],[403,'This profile is not available to this account.'],[409,'Your profile connection needs review.'],[503,'Your profile is temporarily unavailable.']]) {
      await reset({status,body:{detail:'PRIVATE SERVER DETAIL'}});
      await page.getByRole('heading',{name:title,exact:true}).waitFor();
      check(await page.getByRole('alert').isVisible()&&await draft().count()===0&&await page.getByText('PRIVATE SERVER DETAIL',{exact:false}).count()===0,'HTTP '+status+' has distinct safe recovery without source-detail leakage or fallback data');
    }
    await setMode({body:profile('Recovered Fixture')});await page.getByRole('button',{name:'Try again',exact:true}).click();await ready();
    check(await page.getByRole('heading',{name:'Recovered Fixture',exact:true}).isVisible()&&await page.getByRole('alert').count()===0,'Retry replaces unavailable state with a confirmed source read');
    await goal().fill('Preserve until refreshed');await prepare();await setMode({status:409,body:{}});await page.getByRole('button',{name:'Refresh profile'}).click();await page.getByRole('alert').waitFor();
    check(await draft().count()===0&&await page.getByText('Recovered Fixture',{exact:true}).count()===0,'A denied refresh removes formerly visible evidence and draft');

    await reset({body:emptyState('unlinked')});
    check(await page.getByRole('heading',{name:'Bring your GMTM profile with you.',exact:true}).isVisible()&&await page.getByRole('link',{name:'Check connection',exact:true}).getAttribute('href')==='/connect'&&await goal().count()===0,'Unlinked state offers existing connection recovery without fabricated athlete data');
    await reset({body:emptyState('source_unavailable')});
    check(await page.getByText('We could not read your source profile. This does not mean your results are missing.',{exact:true}).isVisible()&&await goal().count()===0,'Source unavailable is different from an empty metric list');
    const noMetrics={...profile(),evidence:[],observations:[]};await reset({body:noMetrics});await ready();await goal().fill('Prepare my profile for a real application');await prepare();
    check(await page.getByRole('heading',{name:'Alex Fixture',exact:true}).isVisible()&&await page.getByRole('checkbox').count()===0&&!(await draft().inputValue()).includes('Selected results')&&(await draft().inputValue()).includes('Flag football'),'A valid profile without numeric results still produces factual identity/goal text');
    const nullFields={...noMetrics,athlete:{name:null,sport:null,position:null,school:null,city:null,state:null,graduation_year:null}};await reset({body:nullFields});await ready();await goal().fill('Understand my next step');await prepare();
    check((await draft().inputValue())==='Athlete profile\n\nMy goal: Understand my next step','Nullable source fields do not become invented identity, metrics or eligibility claims');

    const badPayloads=[{...profile(),athlete:null},{...emptyState('unlinked'),athlete:athlete('PRIVATE INVALID OWNER')},{...profile(),evidence:[{...result('m1','Dash',3.12),verification:'verified'}]},{...profile(),observations:[{title:'Unsupported',detail:'Wrong evidence',evidence_ids:['other-athlete']}]},{...profile(),evidence:[result('m1','Dash',3.12),result('m1','Duplicate',4)]},{...profile(),fetched_at:'invalid-date'},{...profile(),athlete:{...athlete('Fixture'),'school':'x'.repeat(161)}},{...profile(),evidence:Array.from({length:21},(_,i)=>result('m'+i,'Dash',3))},{...profile(),fetched_at:'2026-09-08T17:00:00'},{...profile(),evidence:[{...result('m1','Dash',3),recorded_at:'2026-02-30T23:30:00'}]}];
    for (const body of badPayloads) {await reset({body});await page.getByRole('alert').waitFor();check(await goal().count()===0&&await page.getByText('PRIVATE INVALID OWNER',{exact:true}).count()===0,'Malformed/contradictory source fails closed: '+badPayloads.indexOf(body))}
    for (const length of [161,300,301]) {
      const body=profile();body.evidence[0].event_name='E'.repeat(length);await reset({body});
      if(length<=300){await ready();await page.getByRole('checkbox').first().check();await goal().fill('Use my actual event evidence');await prepare();check((await draft().inputValue()).includes('E'.repeat(length)),'Valid backend event name length '+length+' stays available in the profile and draft')}
      else {await page.getByRole('alert').waitFor();check(await goal().count()===0,'Event names exceeding the backend 300-character bound fail closed')}
    }
    for (const mode of [{badJSON:true},{reject:true}]) {await reset(mode);await page.getByRole('alert').waitFor();check(await page.getByRole('checkbox').count()===0,'Malformed JSON/network failure never invents empty or sample results')}

    await reset({pending:true});await page.evaluate(()=>window.__advance(30000));await settle();await page.getByRole('heading',{name:'Your profile took too long to load.',exact:true}).waitFor();
    check(await page.evaluate(()=>window.__requests[0].signal.aborted&&window.__timers.size===0),'A hung request times out, aborts and leaves a retryable visible state');
    await setMode({body:profile('Latest Fixture')});await page.getByRole('button',{name:'Try again',exact:true}).click();await ready();await release({body:profile('LATE EXPIRED PROFILE')});
    check(await page.getByRole('heading',{name:'Latest Fixture',exact:true}).isVisible()&&await page.getByText('LATE EXPIRED PROFILE',{exact:true}).count()===0,'Timed-out response cannot replace a later successful retry');
    await reset({pending:true});await page.evaluate(()=>window.__unmount());await settle();
    check(await page.evaluate(()=>window.__requests[0].signal.aborted&&window.__timers.size===0),'Unmount aborts its read and clears its timer');await release({body:profile()});
    check(await page.locator('#root').innerHTML()==='','Unmounted late response cannot repopulate the page');
    await reset({body:profile()},{isLoaded:true,user:{id:'athlete-a'}},true);await ready();
    check(await page.getByRole('alert').count()===0&&await page.evaluate(()=>window.__requests.some(r=>r.signal.aborted)),'StrictMode cleanup cannot overwrite its fresh read with an abort error');

    const hostile='<img src=x onerror="window.__xss=1">';const escaped=profile(hostile);escaped.evidence[0].label=hostile;escaped.observations[0].detail=hostile;await reset({body:escaped});await ready();await page.getByRole('checkbox').first().check();await goal().fill(hostile);await prepare();
    check(await page.locator('img,iframe').count()===0&&await page.evaluate(()=>window.__xss===undefined)&&(await draft().inputValue()).includes(hostile),'Source and athlete-provided HTML stay escaped text in presentation and output');
    const exact=await page.evaluate(()=>window.__helpers.evidenceValue({value:0.00000000003,unit:'seconds'}));check(exact==='3e-11 seconds','Numeric presentation does not round a small recorded measurement into zero');
    const many=profile();many.evidence=Array.from({length:20},(_,i)=>result('m'+i,'Recorded test '+(i+1),i+1));many.observations=[];
    await reset({body:many});await ready();
    check(await page.getByRole('checkbox').count()===3,'A full profile initially shows only three results so the useful action remains near the evidence');
    await page.getByRole('button',{name:'Show all 20 results',exact:true}).click();
    check(await page.getByRole('checkbox').count()===20,'Every returned result remains available through explicit expansion');
    await page.getByRole('checkbox').last().check();await page.getByRole('button',{name:'Show fewer results',exact:true}).click();await goal().fill('My real goal');await prepare();
    check(await page.getByRole('checkbox').count()===3&&(await draft().inputValue()).includes('Recorded test 20: 20 seconds'),'Collapsing the list preserves the athlete selection in the prepared text');
    await page.getByRole('button',{name:'Show all 20 results',exact:true}).click();
    check(await page.getByRole('checkbox').last().isChecked(),'Re-expansion restores the selected result control');

    const dates=await page.evaluate(()=>['2026-08-01T23:30:00','2026-08-01','2026-08-01T23:30:00-04:00'].map(value=>window.__helpers.evidenceDate(value)));
    check(dates[0]==='Aug 1, 2026'&&dates[1]==='Aug 1, 2026','Naive and date-only source timestamps retain their calendar date in a non-UTC browser');
    check(dates[2]==='Aug 2, 2026','Explicit-offset timestamps normalize to the stated UTC display date');
    const naiveProfile=profile();naiveProfile.evidence[0].recorded_at='2026-08-01T23:30:00';await reset({body:naiveProfile});await ready();await page.getByRole('checkbox').first().check();await goal().fill('An actual goal');await prepare();
    check((await draft().inputValue()).includes('Aug 1, 2026')&&await page.getByText(/Recorded GMTM metric · Aug 1, 2026/).isVisible(),'The actual rendered record and prepared draft both preserve the naive source date');

    const materialRegion=()=>page.getByRole('region',{name:'Your submitted results and footage',exact:true});
    const richMaterials=materials([materialResult(),materialFilm(),materialResult('private-result',{title:'Private submitted result',can_include:false}),materialFilm('processing-film',{title:'Processing footage',availability:'processing',can_include:false,source_url:null})]);
    await reset({body:profile()},undefined,false,{body:richMaterials});await ready();
    await materialRegion().getByText('2 submitted results and 2 footage records in this view.',{exact:true}).waitFor();
    check(await page.evaluate(()=>!!(document.getElementById('profile-output-title').compareDocumentPosition(document.getElementById('profile-materials-title'))&Node.DOCUMENT_POSITION_FOLLOWING))&&await page.getByRole('link',{name:'Explore submitted results and footage (4)',exact:true}).getAttribute('href')==='#profile-materials-title','Composer precedes the material list in phone reading order with a direct evidence jump');
    check(await materialRegion().getByRole('article').count()===3&&await materialRegion().getByRole('checkbox').count()===2,'Three materials appear initially and private records have no include control');
    check(await materialRegion().getByText(/Submitted: Aug 21, 2026/).count()===2&&await materialRegion().getByText(/Published: Aug 22, 2026/).count()===1,'Submission and publication dates are explicitly distinguished from measurement dates');
    const filmLink=materialRegion().getByRole('link',{name:/View footage on GMTM: Game footage/});
    check(await filmLink.getAttribute('href')==='https://gmtm.com/film/12'&&await filmLink.getAttribute('target')==='_blank'&&await filmLink.getAttribute('rel')==='noopener noreferrer','Footage offers only its explicit generated GMTM page link');
    check(await page.locator('img,video,audio,iframe,source').count()===0&&await page.evaluate(()=>window.__requests.length===2),'Viewing material records loads no media, preview, provider or extra endpoint');
    await materialRegion().getByRole('checkbox',{name:/Include Submitted sprint/}).check();await materialRegion().getByRole('checkbox',{name:/Include Game footage/}).check();await goal().fill('Prepare evidence for my next real application');await prepare();
    const materialDraft=await draft().inputValue();
    check(materialDraft.includes('Submitted sprint: 4.8 seconds')&&materialDraft.includes('Fixture combine · Sprint exercise; Submitted: Aug 21, 2026')&&materialDraft.includes('https://gmtm.com/film/12 (Playback not checked.)')&&!materialDraft.includes('Private submitted result'),'Selected public results and film references keep source, date and uncertainty; private material never enters the draft');
    await draft().fill('My own edited text');await materialRegion().getByRole('checkbox',{name:/Include Game footage/}).uncheck();
    check((await draft().inputValue())==='My own edited text'&&await page.getByText(/Your selections changed/).isVisible(),'Changing material selection marks an edited draft stale without replacing it');
    await page.getByRole('button',{name:'Rebuild from these details',exact:true}).click();
    check((await draft().inputValue()).includes('Submitted sprint')&&!(await draft().inputValue()).includes('/film/12'),'Only explicit rebuild applies the changed material selection');
    await materialRegion().getByRole('button',{name:'Show all 4 materials',exact:true}).click();
    check(await materialRegion().getByRole('article').count()===4&&await materialRegion().getByText('Processing not confirmed in GMTM. View only; this record will not be included in your text.',{exact:true}).isVisible(),'Expanded processing footage is visible as source context and cannot enter text');
    await materialRegion().getByRole('button',{name:'Show fewer materials',exact:true}).click();
    check(await materialRegion().getByRole('checkbox',{name:/Include Submitted sprint/}).isChecked(),'Collapsing materials preserves selected public evidence');
    await page.getByLabel('Introduction',{exact:true}).check();await page.getByLabel('Who is this for?',{exact:true}).fill('Coach Example');await page.getByRole('button',{name:'Rebuild from these details',exact:true}).click();
    const introduction=await draft().inputValue();
    check(introduction.startsWith('Hello Coach Example,')&&introduction.indexOf('Additional evidence')<introduction.indexOf('Thank you for your time.')&&introduction.endsWith('Alex Fixture'),'Material facts are inserted before the existing introduction closing');
    await setMaterialsMode({body:materials()});await page.getByRole('button',{name:'Refresh profile',exact:true}).click();await ready();
    check(await draft().count()===0&&await materialRegion().getByRole('checkbox').count()===0&&await page.locator('input[type=checkbox]:checked').count()===0,'Main refresh clears material records, selections and the draft before the new source view');

    for(const materialMode of [{status:503,body:{detail:'PRIVATE MATERIAL ERROR'}},{body:materials([],'source_unavailable')},{reject:true},{badJSON:true}]){
      await reset({body:profile()},undefined,false,materialMode);await ready();await materialRegion().getByRole('alert').waitFor();await goal().fill('Use my available profile measurements');await page.getByRole('checkbox').first().check();await prepare();
      check((await draft().inputValue()).includes('20-yard dash: 3.12 seconds')&&await page.getByRole('heading',{name:'Alex Fixture',exact:true}).isVisible()&&await page.getByText('PRIVATE MATERIAL ERROR',{exact:false}).count()===0,'Failed materials read preserves usable base profile and composer: '+JSON.stringify(Object.keys(materialMode)));
    }
    await setMaterialsMode({body:richMaterials});await materialRegion().getByRole('button',{name:'Retry materials',exact:true}).click();await materialRegion().getByRole('checkbox').first().waitFor();
    check((await draft().inputValue()).includes('20-yard dash: 3.12 seconds')&&await materialRegion().getByRole('alert').count()===0,'Materials retry restores source cards without erasing an existing base-evidence draft');
    await reset({body:profile()},undefined,false,{body:materials()});await ready();
    check(await materialRegion().getByText(/No supported submissions or footage were returned in this view/).isVisible()&&await materialRegion().getByRole('alert').count()===0,'An empty material view is distinct from source failure and does not claim the overall profile is empty');
    await reset({body:profile()},undefined,false,{body:materials([],'unlinked')});await ready();
    check(await materialRegion().getByText(/Your connection could not be confirmed for these materials/).isVisible()&&await materialRegion().getByRole('checkbox').count()===0,'Unconfirmed material ownership displays no source records while retaining the independently read base profile');

    const malformedMaterials=[
      materials([materialFilm('film-1',{source_url:'https://cdn.example.invalid/raw.mp4'})]),
      materials([materialFilm('film-1',{source_url:'https://gmtm.com/film/1?token=private'})]),
      materials([materialFilm('film-1',{source_url:'https://gmtm.com/film/0'})]),
      materials([materialFilm('film-1',{source_url:'javascript:alert(1)'})]),
      materials([materialFilm('film-1',{availability:'processing',can_include:true})]),
      materials([materialFilm('film-1',{availability:'unchecked',source_url:null,can_include:true})]),
      materials([materialResult('r',{result:null})]),
      materials([materialResult('r',{date_label:'Published'})]),
      materials([materialResult('r',{recorded_at:'2026-02-30'})]),
      materials([materialResult('duplicate'),materialResult('duplicate')]),
      materials([materialFilm()],'unlinked'),
      materials(Array.from({length:21},(_,i)=>materialResult('r'+i))),
      materials(Array.from({length:11},(_,i)=>materialFilm('f'+i))),
    ];
    for(const [index,body] of malformedMaterials.entries()){
      await reset({body:profile()},undefined,false,{body});await ready();await materialRegion().getByRole('alert').waitFor();
      check(await materialRegion().getByRole('checkbox').count()===0&&await materialRegion().getByRole('link').count()===0&&await page.getByRole('heading',{name:'Alex Fixture',exact:true}).isVisible(),'Unsafe or contradictory material response is withheld without erasing base evidence: '+index);
    }
    const hostileMaterial=materialResult('hostile',{title:'<img src=x onerror="window.__materialXss=1">'});
    await reset({body:profile()},undefined,false,{body:materials([hostileMaterial])});await ready();await materialRegion().getByRole('checkbox').first().check();await goal().fill('A genuine use for my recorded evidence');await prepare();
    check(await page.locator('img,iframe,video').count()===0&&await page.evaluate(()=>window.__materialXss===undefined)&&(await draft().inputValue()).includes(hostileMaterial.title),'Material labels render and copy as escaped plain text without media or code execution');

    await reset({body:profile()},undefined,false,{pending:true});await ready();await goal().fill('Continue while materials load');await prepare();await page.evaluate(()=>window.__advance(30000));await settle();await materialRegion().getByRole('alert').waitFor();
    check((await draft().inputValue()).includes('Continue while materials load')&&await page.evaluate(()=>window.__requests.find(r=>r.path==='/api/athlete/materials').signal.aborted),'Materials timeout aborts only its request and keeps the base-evidence draft usable');
    await setMaterialsMode({body:materials([materialFilm('new-film',{title:'Latest footage'})])});await materialRegion().getByRole('button',{name:'Retry materials',exact:true}).click();await materialRegion().getByRole('heading',{name:'Latest footage',exact:true}).waitFor();await releaseMaterials({body:materials([materialFilm('old-film',{title:'LATE OLD FOOTAGE'})])});
    check(await materialRegion().getByRole('heading',{name:'Latest footage',exact:true}).isVisible()&&await page.getByText('LATE OLD FOOTAGE',{exact:true}).count()===0,'Timed-out materials cannot overwrite a newer successful retry');
    for(const mode of [{pending:true},{bodyPending:true,body:richMaterials}]){
      await reset({body:profile()},undefined,false,mode);await ready();await setMaterialsMode({body:materials([materialFilm('new-account-film',{title:'New account footage'})])});await setMode({body:profile('Blair Fixture')});await switchAccount('athlete-b');await ready();await releaseMaterials({body:materials([materialFilm('old-account-film',{title:'PRIVATE OLD FOOTAGE'})])});
      check(await materialRegion().getByRole('heading',{name:'New account footage',exact:true}).isVisible()&&await page.getByText('PRIVATE OLD FOOTAGE',{exact:true}).count()===0&&await page.evaluate(()=>window.__requests.filter(r=>r.path==='/api/athlete/materials').at(-1).authorization==='Bearer fixture-athlete-b'),'Account switch aborts stale material '+(mode.pending?'response':'body')+' and reads with the new credential');
    }
    await reset({body:profile()},undefined,false,{pending:true});await ready();await switchAccount(null);await releaseMaterials({body:richMaterials});
    check(await materialRegion().count()===0&&await page.getByText('Game footage',{exact:true}).count()===0&&await page.evaluate(()=>window.__timers.size===0),'Logout removes materials and late responses cannot reintroduce private records');
    await reset({body:profile()},undefined,false,{pending:true});await ready();await page.evaluate(()=>window.__unmount());await settle();await releaseMaterials({body:richMaterials});
    check(await page.locator('#root').innerHTML()===''&&await page.evaluate(()=>window.__requests.find(r=>r.path==='/api/athlete/materials').signal.aborted&&window.__timers.size===0),'Unmount cancels the materials read and clears its timer');
    check(errors.length===0,'No browser runtime errors');check(denied.length===0,'No attempted browser requests outside the intercepted fixture assets');
    const changed=files.filter(file=>crypto.createHash('sha256').update(fs.readFileSync(path.join(frontend,file))).digest('hex')!==sourceHashes[file]);check(changed.length===0,'Captured application inputs remain unchanged during the check');
    assertRunning();
    outcome = {status:'pass',checks,sourceHashes,errors,denied,scope:'Actual source components and API transport with synthetic Clerk/evidence/clipboard and intercepted browser networking; no full Next, CSS/layout, real identity/data/provider or system clipboard acceptance.'};
})();
Promise.race([work, interrupted]).catch(error => {
  outcome = {status:'failed',checks,error:String(error.stack||error),sourceHashes,errors,denied}; process.exitCode = 1;
}).finally(async () => {
  stopping = true; clearTimeout(runTimer); lifecycle('cleanup_started', { interruption });
  cleanupTimer = setTimeout(() => emergencyStop('Cleanup exceeded its 60-second budget'), cleanupBudgetMs);
  outcome.cleanup = await cleanupBrowser();
  outcome.cleanupVerified = outcome.cleanup.dead && outcome.cleanup.groupDead && outcome.cleanup.closed && outcome.cleanup.ownershipConfirmed && outcome.cleanup.portClosed;
  if (!outcome.cleanupVerified) { outcome.status = 'failed'; process.exitCode = 1; }
  lifecycle('cleanup_finished', { status: outcome.status, cleanupVerified: outcome.cleanupVerified });
  writeReceipt(); clearTimeout(cleanupTimer);
  process.stdout.write(JSON.stringify({status:outcome.status,checks:checks.length,receipt:receiptPath})+'\n');
  process.exit(process.exitCode || 0);
}).catch(error => emergencyStop(error.message));
