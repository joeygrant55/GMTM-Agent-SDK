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
const files = ['app/home/components/ProfileWorkspace.tsx', 'app/home/components/ProfileWorkspaceShell.tsx', 'app/home/components/AthleteDebriefPanel.tsx', 'app/home/components/athleteDebrief.ts', 'app/home/components/profileEvidence.ts', 'app/home/components/ProfileMaterialsPanel.tsx', 'app/home/components/profileMaterials.ts', 'app/_lib/api.ts', 'lib/backend-config.cjs'];
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
window.__requests=[];window.__pending=[];window.__mode={};window.__materialsMode={};window.__debriefMode={status:503,body:{detail:'Fixture disabled'}};window.__clipboard=[];window.__clipboardMode='success';window.__copyPending=[];
Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:async text=>{window.__clipboard.push(text);if(window.__clipboardMode==='failure')throw Error('Fixture clipboard denial');if(window.__clipboardMode==='pending')return new Promise(resolve=>window.__copyPending.push(resolve))}}});
window.__now=1000000;window.__timers=new Map();let timerId=0;
window.setTimeout=(fn,ms=0,...args)=>{const id=++timerId;window.__timers.set(id,{at:window.__now+ms,fn:()=>fn(...args)});return id};
window.clearTimeout=id=>window.__timers.delete(id);
window.__advance=async ms=>{const end=window.__now+ms;for(const[id,t]of [...window.__timers]){if(t.at<=end){window.__timers.delete(id);t.fn();for(let n=0;n<15;n++)await Promise.resolve()}}window.__now=end};
function reply(mode={},request){if(mode.reject)throw Error('Fixture network failure');const response=new Response(mode.badJSON?'malformed-json':JSON.stringify(mode.body),{status:mode.status||200,headers:{'content-type':'application/json'}});if(mode.bodyPending)response.json=()=>new Promise(resolve=>window.__pending.push({stage:'body',resolve,request}));return response}
window.fetch=async(input,init={})=>{const u=new URL(String(input),location.origin);const isDebrief=u.pathname==='/api/athlete/debrief';if(u.origin!==location.origin||!['/api/athlete/evidence','/api/athlete/materials','/api/athlete/debrief'].includes(u.pathname)||u.search||(init.method||'GET')!==(isDebrief?'POST':'GET'))throw Error('Unexpected endpoint '+u);const headers=new Headers(init.headers);const request={path:u.pathname,method:init.method||'GET',signal:init.signal,authorization:headers.get('Authorization'),contentType:headers.get('Content-Type'),body:init.body,cache:init.cache};window.__requests.push(request);const mode=isDebrief?window.__debriefMode:u.pathname==='/api/athlete/materials'?window.__materialsMode:window.__mode;if(mode.pending)return new Promise(resolve=>window.__pending.push({stage:'response',resolve,request}));return reply(mode,request)};
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
window.__debriefHelpers=load('app/home/components/athleteDebrief');
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
const debriefQuestion = 'What can my evidence help me do?';
const debrief = (question=debriefQuestion,track='profile',action='prepare_summary') => {
  const official = {usaf_support:{id:'o2',href:'https://www.usafootball.com/contact-us',label:'Check the official support route'},usaf_development:{id:'o3',href:'https://usafootball.com/resources/app',label:'Explore USA Football development resources'}}[action];
  return {state:'ready',track,question,answer:{text:'Your recorded result can help you make a factual introduction.',refs:['f1']},insights:[{text:'The recorded dash has a source and a date.',refs:['f1']}],unknowns:[{text:'This evidence does not confirm a selection decision.',refs:['coverage']}],next_action:{id:action,kind:official?'open_source':action,label:official?official.label:action==='prepare_summary'?'Prepare my profile summary':'Prepare an introduction',href:official?official.href:null,reason:{text:official?'Use the official published route to learn more.':'Prepare text for a recipient or use you already know.',refs:[official?official.id:'f1']}},references:[{id:'f1',kind:'evidence',label:'Recorded dash',detail:'20-yard dash: 3.12 seconds; measurement verification is unconfirmed.',href:null,checked_at:null},{id:'coverage',kind:'coverage',label:'Coverage of this view',detail:'Selection and eligibility have not been established.',href:null,checked_at:null},...(official?[{id:official.id,kind:'official',label:'Official USA Football source',detail:'A reviewed published source; not a promise of review or selection.',href:official.href,checked_at:'2026-09-08T22:51:00Z'}]:[])],fetched_at:'2026-09-08T23:00:00Z'};
};
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
    const openComposer=async()=>{const summary=page.locator('summary').filter({hasText:'Prepare text yourself'});if(!(await summary.evaluate(el=>el.parentElement.open)))await summary.click()};
    const ready=async(open=true)=>{await page.getByRole('heading',{name:'What your profile records',exact:true}).waitFor();if(open)await openComposer()};
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
    check(await page.getByRole('navigation').count()===0&&await page.getByRole('textbox').count()===3&&await page.getByRole('heading',{name:'Combine help'}).count()===0,'Shell has no task navigation, chat panel or additional workspace request');

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
    await materialRegion().getByRole('checkbox',{name:/Include Submitted sprint/}).check();await materialRegion().getByRole('checkbox',{name:/Include Game footage/}).check();
    await page.locator('summary').filter({hasText:'Prepare text yourself'}).click();const returnToTools=materialRegion().getByRole('link',{name:'Back to guidance and text tools',exact:true});await returnToTools.click();
    check(await returnToTools.getAttribute('href')==='#profile-debrief-title'&&await page.evaluate(()=>location.hash==='#profile-debrief-title')&&await page.getByRole('heading',{name:'What comes next for you?',exact:true}).isVisible()&&!await goal().isVisible(),'Materials return link reaches the visible guidance panel when the manual composer is closed');
    await openComposer();await goal().fill('Prepare evidence for my next real application');await prepare();
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

    const question=()=>page.getByLabel('What would you like to figure out?',{exact:true});
    const track=()=>page.getByLabel('Your focus',{exact:true});
    const ask=()=>page.getByRole('button',{name:'Ask SPARQ',exact:true}).click();
    const answerRegion=()=>page.locator('[aria-label="SPARQ answer"]');
    const setDebriefMode=mode=>page.evaluate(mode=>{window.__debriefMode=mode},mode);
    const releaseDebrief=async mode=>{await page.evaluate(mode=>window.__release(mode,'/api/athlete/debrief'),mode);await settle()};
    const answerReady=()=>answerRegion().getByText(debrief().answer.text,{exact:false}).waitFor();
    const answerAction=()=>page.getByRole('button',{name:'Prepare my profile summary',exact:true});
    await reset();await ready(false);
    check(await page.getByRole('heading',{name:'What comes next for you?',exact:true}).isVisible()&&await question().isVisible()&&!(await goal().isVisible())&&await page.getByRole('button',{name:'Ask SPARQ',exact:true}).isDisabled(),'The primary panel asks a real question; manual preparation starts in a secondary disclosure');
    await question().fill('   ');await track().selectOption('national_team');await track().selectOption('profile');
    check(await page.evaluate(()=>window.__requests.length===2)&&await page.getByRole('button',{name:'Ask SPARQ',exact:true}).isDisabled()&&await question().getAttribute('maxlength')==='1000','Typing and changing focus never call a model; a nonempty bounded question is required');
    await question().fill('  '+debriefQuestion+'  ');await setDebriefMode({bodyPending:true,body:debrief()});await ask();await settle();
    check(await page.evaluate(()=>{const r=window.__requests.at(-1);return r.path==='/api/athlete/debrief'&&r.method==='POST'&&r.authorization==='Bearer fixture-athlete-a'&&r.cache==='no-store'&&r.contentType==='application/json'&&JSON.stringify(JSON.parse(r.body))===JSON.stringify({track:'profile',question:'What can my evidence help me do?'})}),'Explicit Ask sends only the trimmed question and track using the signed-in no-store transport');
    check(await answerRegion().count()===0&&await page.getByRole('button',{name:'Asking SPARQ…',exact:true}).isDisabled(),'No partial response renders while the complete JSON body is pending');
    await page.locator('#debrief-question').evaluate(el=>el.form.dispatchEvent(new Event('submit',{bubbles:true,cancelable:true})));await question().fill('A changed question');await settle();
    check(await page.evaluate(()=>window.__requests.filter(r=>r.path==='/api/athlete/debrief').length===1),'A second submit cannot overlap the active debrief request');
    await releaseDebrief({body:debrief()});await answerReady();
    check(await page.getByText(/Previous answer —/).isVisible()&&await answerAction().isDisabled(),'An answer arriving after question edits is marked previous and cannot trigger the old action');
    await question().fill(debriefQuestion);await track().selectOption('outreach');
    check(await page.getByText(/Previous answer —/).isVisible()&&await answerAction().isDisabled(),'Changing only the focus also marks the displayed answer stale');
    await track().selectOption('profile');await page.getByRole('button',{name:'Show sources for the answer',exact:true}).click();
    check(await answerRegion().getByText('20-yard dash: 3.12 seconds; measurement verification is unconfirmed.',{exact:true}).isVisible()&&await answerRegion().getByText('What remains unknown',{exact:true}).isVisible(),'Answer citations open their resolved source details and retain explicit unknowns');
    await page.getByRole('checkbox').nth(1).check();await answerAction().click();
    check(await goal().isVisible()&&(await goal().inputValue())===debriefQuestion&&await draft().count()===0&&!await page.getByRole('checkbox').first().isChecked()&&await page.getByRole('checkbox').nth(1).isChecked(),'Local action opens the composer and may fill an empty goal; it neither prepares a draft nor selects the model-cited fact');
    await prepare();await draft().fill('MY EXACT EDITED DRAFT');await goal().fill('My existing goal');await track().selectOption('outreach');await setDebriefMode({body:debrief(debriefQuestion,'outreach','prepare_introduction')});await ask();await answerReady();
    await page.getByRole('button',{name:'Prepare an introduction',exact:true}).click();
    check((await draft().inputValue())==='MY EXACT EDITED DRAFT'&&(await goal().inputValue())==='My existing goal'&&await page.getByLabel('Who is this for?',{exact:true}).inputValue()===''&&await page.getByRole('button',{name:'Rebuild from these details',exact:true}).isDisabled(),'Introduction action preserves exact edits and the existing goal, requiring a real recipient before explicit rebuild');
    await page.getByLabel('Who is this for?',{exact:true}).fill('Coach Fixture');await page.getByRole('button',{name:'Rebuild from these details',exact:true}).click();
    check((await draft().inputValue()).startsWith('Hello Coach Fixture,')&&(await draft().inputValue()).includes('Three-cone drill')&&!(await draft().inputValue()).includes('20-yard dash'),'Only explicit rebuild applies the action format, recipient and athlete-selected facts');
    const keptDraft=await draft().inputValue();await setDebriefMode({status:502,body:{detail:'PRIVATE PROVIDER DETAIL'}});await ask();await page.getByRole('alert').waitFor();
    check(await answerRegion().isVisible()&&await page.getByText(/Previous answer —/).isVisible()&&(await draft().inputValue())===keptDraft&&await page.getByText('PRIVATE PROVIDER DETAIL',{exact:false}).count()===0&&await page.getByRole('button',{name:'Prepare an introduction',exact:true}).isDisabled(),'A failed retry preserves the old answer and exact draft, identifies the earlier answer, and withholds provider detail');

    for(const [status,code,expected] of [[401,null,'Please sign in again before asking SPARQ.'],[409,null,'Your profile connection could not be confirmed'],[429,null,'SPARQ is at its request limit'],[503,null,'SPARQ is unavailable right now'],[503,'pathway_sources_expired','USA Football sources need a fresh review.']]){
      await reset();await ready(false);await question().fill(debriefQuestion);await setDebriefMode({status,body:{detail:'PRIVATE ERROR DETAIL',...(code?{code}:{})}});await ask();await page.getByRole('alert').waitFor();
      check((await page.getByRole('alert').innerText()).includes(expected)&&await answerRegion().count()===0&&await page.getByRole('heading',{name:'Alex Fixture',exact:true}).isVisible()&&await page.getByText('PRIVATE ERROR DETAIL',{exact:false}).count()===0,'Debrief failure '+(code||status)+' provides safe distinct recovery while retaining the profile');
    }
    await openComposer();await goal().fill('My manual next step');await prepare();
    check((await draft().inputValue()).includes('My manual next step'),'Manual preparation remains useful when AI or official sources are unavailable');

    await reset();await ready(false);await question().fill(debriefQuestion);await setDebriefMode({body:debrief()});await ask();await answerReady();
    await setDebriefMode({pending:true});await ask();await settle();await page.evaluate(()=>window.__advance(60000));await settle();await page.getByRole('alert').waitFor();
    check((await page.getByRole('alert').innerText()).includes('took too long')&&await answerRegion().isVisible()&&await page.getByText(/Previous answer —/).isVisible()&&await page.evaluate(()=>window.__requests.at(-1).signal.aborted&&window.__timers.size===0),'Debrief timeout aborts its request, clears its timer and preserves a clearly previous answer');
    const newer={...debrief(),answer:{text:'A fresh successful answer.',refs:['f1']}};await setDebriefMode({body:newer});await ask();await answerRegion().getByText('A fresh successful answer.',{exact:false}).waitFor();await releaseDebrief({body:debrief()});
    check(await answerRegion().getByText('A fresh successful answer.',{exact:false}).isVisible()&&await page.getByText(/Previous answer —/).count()===0,'Late timed-out debrief cannot overwrite a later successful answer');
    for(const mode of [{bodyPending:true,body:debrief()},{status:503,bodyPending:true,body:{detail:'Fixture'}}]){
      await reset();await ready(false);await question().fill(debriefQuestion);await setDebriefMode(mode);await ask();await settle();await page.evaluate(()=>window.__advance(60000));await settle();await page.getByRole('alert').waitFor();await releaseDebrief({body:debrief()});
      check(await answerRegion().count()===0&&await page.evaluate(()=>window.__requests.at(-1).signal.aborted&&window.__timers.size===0),'The same deadline covers a pending '+(mode.status?'error':'successful')+' response body without late text leakage');
    }

    const malformedDebriefs=[
      {...debrief(),extra:'unexpected'}, {...debrief(),state:'partial'}, {...debrief(),track:'outreach'}, {...debrief(),question:'Different question'},
      {...debrief(),fetched_at:'2026-02-30T00:00:00Z'}, {...debrief(),fetched_at:'2026-09-08T23:00:00'},
      {...debrief(),answer:{text:'UNVALIDATED ANSWER',refs:['unknown']}}, {...debrief(),answer:{text:'UNVALIDATED ANSWER',refs:['f1','f1']}},
      {...debrief(),answer:{text:'UNVALIDATED ANSWER',refs:[]}}, {...debrief(),answer:{text:'x'.repeat(701),refs:['f1']}},
      {...debrief(),answer:{text:'Visit https://example.invalid',refs:['f1']}}, {...debrief(),answer:{text:'Email person@example.invalid',refs:['f1']}},
      {...debrief(),answer:{text:'Visit example.invalid',refs:['f1']}}, {...debrief(),answer:{text:'javascript:alert(1)',refs:['f1']}},
      {...debrief(),answer:{text:'data:text/plain,example',refs:['f1']}}, {...debrief(),answer:{text:'tel:1234567890',refs:['f1']}},
      {...debrief(),answer:{text:'Hidden\u0000control',refs:['f1']}}, {...debrief(),answer:{text:'Hidden\rcarriage return',refs:['f1']}},
      {...debrief(),answer:{text:'UNVALIDATED ANSWER',refs:['f1'],html:'bad'}}, {...debrief(),insights:Array.from({length:4},()=>debrief().answer)},
      {...debrief(),unknowns:Array.from({length:3},()=>debrief().answer)}, {...debrief(),references:[...debrief().references,debrief().references[0]]},
      {...debrief(),references:[...debrief().references,{...debrief().references[0],id:'f2'}]},
      {...debrief(),references:debrief().references.map(r=>({...r,checked_at:'not-a-date'}))},
      {...debrief(),references:debrief().references.map(r=>r.id==='f1'?{...r,href:'https://gmtm.com/film/0'}:r)},
      {...debrief(),references:debrief().references.map(r=>r.id==='f1'?{...r,href:'https://gmtm.com/film/12?token=secret'}:r)},
      {...debrief(),references:debrief().references.map(r=>r.id==='f1'?{...r,href:'https://gmtm.com/film/9007199254740992'}:r)},
      {...debrief(),references:debrief().references.map(r=>r.id==='f1'?{...r,href:'javascript:alert(1)'}:r)},
      {...debrief(),references:debrief().references.map(r=>({...r,detail:'x'.repeat(701)}))},
      {...debrief(),next_action:{...debrief().next_action,id:'contact_every_coach'}},
      {...debrief(),next_action:{...debrief().next_action,href:'https://www.usafootball.com/contact-us'}},
      {...debrief(),next_action:{...debrief().next_action,kind:'open_source'}},
      {...debrief(),next_action:{...debrief().next_action,reason:{text:'UNVALIDATED REASON',refs:['unknown']}}},
    ];
    const parseFailures=await page.evaluate(bodies=>bodies.map(body=>{try{window.__debriefHelpers.readAthleteDebrief(body,{track:'profile',question:'What can my evidence help me do?'});return false}catch{return true}}),malformedDebriefs);
    for(const [index,rejected] of parseFailures.entries())check(rejected,'Complete debrief parser rejects invalid structure, scope, references or destinations: '+index);
    check(await page.evaluate(body=>Array.from({length:32},(_,code)=>{const candidate=structuredClone(body);candidate.answer.text='Before'+String.fromCharCode(code)+'after';try{window.__debriefHelpers.readAthleteDebrief(candidate,{track:'profile',question:body.question});return code===9||code===10}catch{return code!==9&&code!==10}}).every(Boolean),debrief()),'Generated paragraphs permit newline and tab but reject every other ASCII control character');
    await reset();await ready(false);await question().fill(debriefQuestion);await setDebriefMode({body:debrief()});await ask();await answerReady();
    for(const mode of [{body:malformedDebriefs[6]},{badJSON:true},{reject:true}]){
      await setDebriefMode(mode);await ask();await page.getByRole('alert').waitFor();
      check(await answerRegion().isVisible()&&await page.getByText(/Previous answer —/).isVisible()&&await page.getByText('UNVALIDATED ANSWER',{exact:false}).count()===0,'Rejected payload, JSON or transport failure preserves only the previous validated answer: '+JSON.stringify(Object.keys(mode)));
    }
    for(const mode of [{pending:true},{bodyPending:true,body:debrief()}]){
      await reset();await ready();await goal().fill('Private old goal');await prepare();await question().fill(debriefQuestion);await setDebriefMode(mode);await ask();await settle();await setMode({body:profile('Blair Fixture')});await switchAccount('athlete-b');await ready(false);await releaseDebrief({body:debrief()});
      check((await question().inputValue())===''&&await answerRegion().count()===0&&await draft().count()===0&&await page.evaluate(()=>window.__requests.find(r=>r.path==='/api/athlete/debrief').signal.aborted&&window.__timers.size===0),'Account switch clears question, answer and draft and rejects late debrief '+(mode.pending?'response':'body'));
    }
    await question().fill(debriefQuestion);await setDebriefMode({body:debrief()});await ask();await answerReady();
    check(await page.evaluate(()=>window.__requests.at(-1).authorization==='Bearer fixture-athlete-b'),'A new account submits its own debrief with its own credential');
    await setDebriefMode({pending:true});await ask();await settle();await page.getByRole('button',{name:'Refresh profile',exact:true}).click();await ready(false);await releaseDebrief({body:debrief()});
    check(await answerRegion().count()===0&&(await question().inputValue())===''&&await page.evaluate(()=>window.__requests.filter(r=>r.path==='/api/athlete/debrief').at(-1).signal.aborted),'Profile refresh aborts and clears private debrief without an automatic replacement request');
    await reset({body:profile()},undefined,false,{status:503,body:{detail:'Fixture unavailable'}});await ready();await goal().fill('Keep my manual draft');await prepare();await question().fill(debriefQuestion);await setDebriefMode({pending:true});await ask();await settle();await setMaterialsMode({body:materials()});await materialRegion().getByRole('button',{name:'Retry materials',exact:true}).click();await settle();await releaseDebrief({body:debrief()});
    check(await answerRegion().count()===0&&(await question().inputValue())===''&&(await draft().inputValue()).includes('Keep my manual draft')&&await page.evaluate(()=>window.__requests.find(r=>r.path==='/api/athlete/debrief').signal.aborted),'Materials retry clears and aborts debrief source context while preserving the independent manual draft');
    for(const leaving of ['logout','unmount']){
      await reset();await ready(false);await question().fill(debriefQuestion);await setDebriefMode({pending:true});await ask();await settle();if(leaving==='logout')await switchAccount(null);else{await page.evaluate(()=>window.__unmount());await settle()}await releaseDebrief({body:debrief()});
      check(await answerRegion().count()===0&&await question().count()===0&&await page.evaluate(()=>window.__requests.find(r=>r.path==='/api/athlete/debrief').signal.aborted&&window.__timers.size===0),'Debrief '+leaving+' aborts private work, clears the timer and ignores late responses');
    }
    for(const action of ['usaf_support','usaf_development']){
      await reset();await ready(false);await track().selectOption('national_team');await question().fill(debriefQuestion);const body=debrief(debriefQuestion,'national_team',action);await setDebriefMode({body});await ask();await answerReady();const link=page.getByRole('link',{name:body.next_action.label,exact:true});
      check(await link.getAttribute('href')===body.next_action.href&&await link.getAttribute('target')==='_blank'&&await link.getAttribute('rel')==='noopener noreferrer'&&await page.evaluate(()=>window.__requests.length===3),'Official '+action+' action is the exact reviewed plain anchor, with no automatic source/media request');
      await page.getByRole('button',{name:'Show sources for the next step',exact:true}).click();
      check(await answerRegion().getByText('Source reviewed Sep 8, 2026.',{exact:true}).isVisible(),'Official action retains its reviewed source and date: '+action);
      const badOfficial=structuredClone(body);badOfficial.next_action.href+='?unapproved=1';const wrongRef=structuredClone(body);wrongRef.references.at(-1).href='https://example.invalid';
      check(await page.evaluate(({badOfficial,wrongRef})=>[badOfficial,wrongRef].every(body=>{try{window.__debriefHelpers.readAthleteDebrief(body,{track:'national_team',question:'What can my evidence help me do?'});return false}catch{return true}}),{badOfficial,wrongRef}),'Official action and reference URL mismatches fail closed: '+action);
      await question().fill('A revised question');check(await page.getByRole('link',{name:body.next_action.label,exact:true}).count()===0,'A stale answer cannot present its earlier external action as current: '+action);
    }
    const literal='<img src=x onerror="window.__debriefXss=1">';await reset();await ready(false);await question().fill(literal);const escapedAnswer={...debrief(literal),answer:{text:literal,refs:['f1']}};await setDebriefMode({body:escapedAnswer});await ask();await answerRegion().waitFor();
    check(await answerRegion().getByText(literal,{exact:false}).count()>0&&await page.locator('img,iframe,video,audio').count()===0&&await page.evaluate(()=>window.__debriefXss===undefined&&localStorage.length===0&&sessionStorage.length===0),'Athlete and generated text render escaped without media, code execution or persisted conversation');
    check(await page.evaluate(body=>{body.references[0].href='https://gmtm.com/film/12';try{return !!window.__debriefHelpers.readAthleteDebrief(body,{track:'profile',question:body.question})}catch{return false}},debrief('Can I use https://gmtm.com in my introduction?')),'A question may contain a URL as quoted input; evidence links still require the canonical server-resolved film form');
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
