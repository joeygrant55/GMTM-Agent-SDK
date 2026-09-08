// Actual college component with React in an isolated browser. No Next server,
// live Clerk, backend, models, database, dotenv loading, or package installation.
// Timer controls exercise polling deterministically; no visual/layout claim.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');
const frontend = path.resolve(__dirname, '..');
const deps = process.env.SPARQ_TEST_NODE_MODULES;
const playwrightPath = process.env.SPARQ_TEST_PLAYWRIGHT;
const receiptPath = process.env.SPARQ_TEST_RECEIPT;
if (!deps || !playwrightPath || !receiptPath) throw Error('Set explicit SPARQ_TEST_NODE_MODULES, SPARQ_TEST_PLAYWRIGHT and SPARQ_TEST_RECEIPT.');
if (fs.existsSync(receiptPath)) throw Error('Refusing to overwrite an existing receipt.');
const ts = require(path.join(deps, 'typescript'));
const { chromium } = require(playwrightPath);
const sourceHashes = {};
let bundle = "const process={env:{NODE_ENV:'development',NEXT_PUBLIC_BACKEND_URL:'http://127.0.0.1:4321'}};const modules={},cache={};\n";
for (const file of ['app/home/colleges/page.tsx', 'app/home/components/currentCombine.ts', 'app/_lib/api.ts']) {
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
window.__now=1000000;Date.now=()=>window.__now;window.__timers=new Map();let timerId=0;
window.setTimeout=(fn,ms=0,...args)=>{const id=++timerId;window.__timers.set(id,{at:window.__now+ms,fn:()=>fn(...args)});return id};
window.clearTimeout=id=>window.__timers.delete(id);
window.setInterval=(fn,ms=0)=>{const id=++timerId;window.__timers.set(id,{at:window.__now+ms,fn,interval:ms});return id};
window.clearInterval=id=>window.__timers.delete(id);
const microtasks=async()=>{for(let n=0;n<15;n++)await Promise.resolve()};
window.__advance=async ms=>{const end=window.__now+ms;let count=0;while(true){const next=[...window.__timers.entries()].filter(([,t])=>t.at<=end).sort((a,b)=>a[1].at-b[1].at||a[0]-b[0])[0];if(!next)break;if(++count>1000)throw Error('Unbounded timer loop');const [id,t]=next;window.__now=t.at;window.__timers.delete(id);if(t.interval)window.__timers.set(id,{...t,at:t.at+t.interval});t.fn();await microtasks()}window.__now=end;await microtasks()};
window.__requests=[];window.__pending=[];window.__modes={};window.__proactive=[];
window.addEventListener('sparq:proactive-prompt',e=>window.__proactive.push(e.detail));
function reply(kind,mode={}){if(mode.reject)throw Error('Synthetic network rejection');const defaults={colleges:{colleges:[]},trigger:{status:'matching started',profile_id:51},status:{complete:false},update:{updated:true}};return new Response(mode.badJSON?'invalid-json':JSON.stringify(mode.body===undefined?defaults[kind]:mode.body),{status:mode.status||200,headers:{'content-type':'application/json'}})}
window.fetch=async(input,init={})=>{const u=new URL(String(input),location.origin);if(u.origin!==location.origin)throw Error('Blocked external fetch');const kind=u.pathname.includes('/trigger-matching/')?'trigger':u.pathname.includes('/enrichment-status/')?'status':u.pathname.endsWith('/status')?'update':u.pathname.includes('/workspace/colleges/')?'colleges':null;if(!kind)throw Error('Unexpected endpoint '+u.pathname);const request={kind,path:u.pathname,method:init.method||'GET',signal:init.signal,authorization:new Headers(init.headers).get('Authorization')};window.__requests.push(request);const mode=window.__modes[kind]||{};if(mode.pending)return new Promise(resolve=>window.__pending.push({kind,request,resolve}));return reply(kind,mode)};
window.__release=(kind,mode={})=>{const i=window.__pending.findIndex(p=>p.kind===kind);if(i<0)throw Error('No pending '+kind);window.__pending.splice(i,1)[0].resolve(reply(kind,mode))};
const jsx=(type,props,key)=>React.createElement(type,{...props,...(key!==undefined?{key}:{})});
function load(id,from=''){
 if(id==='react')return React;
 if(id==='react/jsx-runtime')return{jsx,jsxs:jsx,Fragment:React.Fragment};
 if(id==='@clerk/nextjs')return{useUser};
 if(id==='next/navigation')return{useSearchParams:()=>new URLSearchParams(window.__query||'')};
 if(id==='next/link')return{__esModule:true,default:({children,...props})=>React.createElement('a',props,children)};
 if(id==='next/dynamic')return{__esModule:true,default:loader=>{let component=null,promise=null;return function Dynamic(props){const[C,setC]=React.useState(()=>component);React.useEffect(()=>{let active=true;(promise||=loader()).then(m=>{component=m.default||m;if(active)setC(()=>component)});return()=>{active=false}},[]);return C?React.createElement(C,props):null}}};
 if(id.startsWith('@/'))id=id.slice(2);else if(id.startsWith('.')){const parts=(from.slice(0,from.lastIndexOf('/')+1)+id).split('/'),out=[];for(const part of parts){if(part==='..')out.pop();else if(part!=='.')out.push(part)}id=out.join('/')}
 if(cache[id])return cache[id].exports;const m={exports:{}};cache[id]=m;if(!modules[id])throw Error('Missing module '+id);modules[id](x=>load(x,id),m,m.exports);return m.exports;
}
const root=ReactDOM.createRoot(document.getElementById('root'));
window.__mount=()=>root.render(React.createElement(load('app/home/colleges/page').default));
window.__unmount=()=>root.render(null);
`;
const origin = 'http://127.0.0.1:4321';
const assets = {
  '/': '<!doctype html><html><head><meta charset="utf-8"></head><body><div id="root"></div><script src="/react.js"></script><script src="/react-dom.js"></script><script src="/app.js"></script></body></html>',
  '/react.js': fs.readFileSync(path.join(deps, 'react/umd/react.development.js'), 'utf8'),
  '/react-dom.js': fs.readFileSync(path.join(deps, 'react-dom/umd/react-dom.development.js'), 'utf8'),
  '/app.js': bundle,
};
const college = (name='Saved College A', reasons=null) => ({id:81,college_name:name,college_city:'Fixture City',college_state:'TX',division:'D1',fit_score:88,status:'Interested',fit_reasons:reasons});
const checks=[], errors=[];
(async()=>{
  const browser=await chromium.launch({headless:true});
  try {
    const page=await browser.newPage();page.on('pageerror',e=>errors.push(String(e)));
    await page.route('**/*',route=>{const u=new URL(route.request().url());if(u.origin!==origin||!(u.pathname in assets))return route.abort();return route.fulfill({status:200,contentType:u.pathname.endsWith('.js')?'application/javascript':'text/html',body:assets[u.pathname]})});
    const check=(condition,name)=>{assert(condition,name);checks.push(name)};
    const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const reset=async(modes={},query='')=>{await page.goto(origin);await page.evaluate(({modes,query})=>{window.__modes=modes;window.__query=query;window.__mount()},{modes,query});await settle()};
    const ready=()=>page.getByRole('heading',{name:'Your College Matches',exact:true}).waitFor();
    const advance=async ms=>{await page.evaluate(ms=>window.__advance(ms),ms);await settle()};
    const setMode=async(kind,mode)=>page.evaluate(({kind,mode})=>{window.__modes[kind]=mode},{kind,mode});
    const count=kind=>page.evaluate(kind=>window.__requests.filter(r=>r.kind===kind).length,kind);
    const timers=()=>page.evaluate(()=>window.__timers.size);
    const request=()=>page.getByRole('button',{name:'Refresh Matches',exact:true}).click();
    const idle=()=>page.getByRole('button',{name:'Refresh Matches',exact:true}).waitFor();
    const release=async(kind,mode={})=>{await page.evaluate(({kind,mode})=>window.__release(kind,mode),{kind,mode});await settle()};

    await reset();await ready();
    check(await page.getByText('No college matches are saved.',{exact:true}).isVisible()&&await page.getByRole('link',{name:'My next move',exact:true}).getAttribute('href')==='/home/inbox','Empty saved matches explain combine continuity without claiming onboarding or research');
    await advance(240000);check(await count('trigger')===0&&await count('status')===0&&await timers()===0,'Mount and complete=false assumptions never automatically start or poll research');

    await reset({},'event_id=1318&unrelated=ignored');await ready();
    check(await page.getByRole('link',{name:'My next move',exact:true}).getAttribute('href')==='/home/inbox?event_id=1318','Combine recovery retains explicit supported adult context only');
    await reset({},'event_id=999');await ready();
    check(await page.getByRole('link',{name:'My next move',exact:true}).getAttribute('href')==='/home/inbox','Unsupported event is not forwarded as a combine selection');

    await reset({colleges:{body:{colleges:[college()]}}});await ready();await advance(1200);
    check(await page.getByText('Detailed fit research is not available for this program.',{exact:true}).isVisible()&&await page.getByText('Researching this program for you...',{exact:true}).count()===0,'Missing detailed fit reasons do not fabricate active research');
    check(await page.evaluate(()=>window.__proactive.length)===0&&await count('trigger')===0,'Opening existing matches emits no automatic AI prompt or research request');
    check(await page.evaluate(()=>window.__requests[0].authorization)==='Bearer fixture-athlete-a','Saved match lookup uses the current account token');

    await reset({colleges:{status:503}});await ready();
    check(await page.getByRole('alert').innerText().then(t=>t.includes('could not load'))&&await page.getByText('No college matches are saved.',{exact:true}).count()===0,'Failed GET is unavailable data rather than an invented empty list');
    await setMode('colleges',{body:{colleges:[college('Recovered College')]}});await page.getByRole('button',{name:'Reload saved matches',exact:true}).click();await page.getByText('Recovered College',{exact:true}).waitFor();
    check(await page.getByRole('alert').count()===0&&await count('trigger')===0,'Loading saved matches can recover without starting paid research');

    for(const status of [422,401,500]){
      await reset({trigger:{status,body:{detail:'PRIVATE SERVER DETAIL'}}});await ready();await request();await idle();
      check(await page.getByRole('alert').isVisible()&&await page.getByText(/Matching request accepted/).count()===0&&await count('status')===0&&await timers()===0,'HTTP '+status+' cannot announce acceptance or start polling');
      check(await page.getByText('PRIVATE SERVER DETAIL',{exact:false}).count()===0,'HTTP '+status+' does not expose raw server details');
      if(status===422)check((await page.getByRole('alert').innerText()).includes('sport in your recruiting profile'),'HTTP422 provides actionable sport-context recovery');
    }
    for(const mode of [{body:{status:'ok',profile_id:51}},{badJSON:true},{reject:true}]){
      await reset({trigger:mode});await ready();await request();await idle();
      check((await page.getByRole('alert').innerText()).includes('could not confirm')&&await count('status')===0&&await timers()===0,'Unconfirmed acceptance stops before polling: '+JSON.stringify(mode));
    }

    await reset({trigger:{pending:true}});await ready();await request();await settle();
    check(await page.getByRole('button',{name:'Requesting research…',exact:true}).isDisabled()&&await page.getByText(/Matching request accepted/).count()===0&&await count('status')===0,'Pending POST shows only requesting and cannot claim started work');
    await release('trigger');await page.getByText(/Matching request accepted/).waitFor();
    check(await page.getByRole('button',{name:'Checking saved research…',exact:true}).isDisabled()&&await timers()===2,'Accepted POST enables one polling timer and its bounded deadline');
    await advance(15000);check(await count('status')===1&&await timers()===2,'False completion schedules one subsequent check without claiming a durable job state');
    await setMode('status',{body:{complete:true}});await setMode('colleges',{body:{colleges:[college('Saved Research College',['A saved detailed fit explanation with sufficient context to display.'])]}});await advance(15000);
    check(await page.getByText('Saved Research College',{exact:true}).isVisible()&&await page.getByText(/Saved college research is available/).isVisible(),'Complete flag reloads and displays saved research');
    check(await page.getByText(/Research complete|Matches refreshed|Finding matches/).count()===0&&await timers()===0,'Legacy complete flag does not claim this request finished and stops all polling');
    await advance(240000);check(await count('status')===2&&await page.evaluate(()=>window.__proactive.length)===0,'Completion refresh neither polls again nor emits an automatic AI prompt');

    await reset({trigger:{pending:true}});await ready();await request();await settle();await advance(30000);await idle();
    check((await page.getByRole('alert').innerText()).includes('could not confirm')&&await page.evaluate(()=>window.__pending[0].request.signal.aborted)&&await timers()===0,'Hung acceptance expires and aborts without claiming research failed or started');
    await release('trigger');check(await count('status')===0&&await page.getByText(/Matching request accepted/).count()===0,'Late acceptance after timeout cannot restart polling');

    await reset({status:{status:503}});await ready();await request();await page.getByText(/Matching request accepted/).waitFor();await advance(15000);await idle();
    check((await page.getByRole('alert').innerText()).includes('could not check')&&await timers()===0,'Polling HTTP failure stops and reports uncertainty');
    await reset({status:{body:{complete:'yes'}}});await ready();await request();await page.getByText(/Matching request accepted/).waitFor();await advance(15000);await idle();
    check(await page.getByRole('alert').isVisible()&&await timers()===0,'Malformed completion cannot become success');

    await reset({colleges:{body:{colleges:[college()]}},status:{pending:true}});await ready();await request();await page.getByText(/Matching request accepted/).waitFor();await advance(45000);
    check(await count('status')===1,'Slow polling requests do not overlap');
    await advance(135000);await idle();
    check(await page.getByText(/We stopped checking after three minutes/).isVisible()&&await timers()===0&&await page.evaluate(()=>window.__pending[0].request.signal.aborted),'Three-minute deadline aborts a hung poll and clears all timers');
    await release('status',{body:{complete:true}});await advance(60000);
    check(await count('colleges')===1&&await count('status')===1&&await page.getByText('Saved College A',{exact:true}).isVisible(),'Late completion after deadline cannot reload or erase existing matches');

    await reset({colleges:{pending:true}});await setMode('colleges',{body:{colleges:[college('Account B College')]}});await page.evaluate(()=>window.__setIdentity({isLoaded:true,user:{id:'athlete-b'}}));await ready();await release('colleges',{body:{colleges:[college('PRIVATE OLD ACCOUNT COLLEGE')]}});
    check(await page.getByText('Account B College',{exact:true}).isVisible()&&await page.getByText('PRIVATE OLD ACCOUNT COLLEGE',{exact:true}).count()===0&&await page.evaluate(()=>window.__requests[0].signal.aborted),'Account switch aborts and ignores old saved-match responses');

    for (const oldMode of [{body:{colleges:[college('OLDER STALE COLLEGE')]}},{status:503}]) {
      await reset({colleges:{body:{colleges:[college()]}}});await ready();await request();await page.getByText(/Matching request accepted/).waitFor();
      await setMode('colleges',{pending:true});await page.getByRole('button',{name:'Reload saved matches',exact:true}).click();await settle();
      await setMode('colleges',{body:{colleges:[college('Newest Saved College')]}});await page.getByRole('button',{name:'Reload saved matches',exact:true}).click();await page.getByText('Newest Saved College',{exact:true}).waitFor();await release('colleges',oldMode);
      check(await page.getByText('Newest Saved College',{exact:true}).isVisible()&&await page.getByText('OLDER STALE COLLEGE',{exact:true}).count()===0&&await page.getByRole('alert').count()===0,'Superseded saved-match '+(oldMode.status?'failure':'success')+' cannot overwrite a newer successful reload');
    }
    await reset({colleges:{body:{colleges:[college()]}}});await ready();await request();await page.getByText(/Matching request accepted/).waitFor();
    await setMode('colleges',{pending:true});await page.getByRole('button',{name:'Reload saved matches',exact:true}).click();await settle();
    await setMode('colleges',{status:503});await page.getByRole('button',{name:'Reload saved matches',exact:true}).click();await page.getByRole('alert').waitFor();await release('colleges',{body:{colleges:[college('OLDER STALE COLLEGE')]}});
    check(await page.getByRole('alert').isVisible()&&await page.getByText('Saved College A',{exact:true}).isVisible()&&await page.getByText('OLDER STALE COLLEGE',{exact:true}).count()===0,'An older success cannot clear the latest reload failure or replace the last valid snapshot');

    await reset({colleges:{body:{colleges:[college()]}},status:{body:{complete:true}}});await ready();await request();await page.getByText(/Matching request accepted/).waitFor();
    await setMode('colleges',{pending:true});await advance(15000);
    await setMode('colleges',{body:{colleges:[college('Manual Reload Won')]}});await page.getByRole('button',{name:'Reload saved matches',exact:true}).click();await page.getByText('Manual Reload Won',{exact:true}).waitFor();await release('colleges',{status:503});await idle();
    check(await page.getByText('Manual Reload Won',{exact:true}).isVisible()&&await page.getByRole('alert').count()===0&&await timers()===0,'Superseded poll reload finishes neutrally when a newer manual reload wins');

    await reset({trigger:{pending:true}});await ready();await request();await settle();await page.evaluate(()=>window.__setIdentity({isLoaded:true,user:{id:'athlete-b'}}));await ready();await release('trigger');await advance(180000);
    check(await count('status')===0&&await timers()===0&&await page.evaluate(()=>window.__requests.find(r=>r.kind==='trigger').signal.aborted),'Account switch during acceptance cannot start old-owner polling');
    check(await page.evaluate(()=>window.__requests.filter(r=>r.kind==='colleges').at(-1).authorization)==='Bearer fixture-athlete-b','New account loads saved matches with its own token');

    await reset({status:{pending:true}});await ready();await request();await page.getByText(/Matching request accepted/).waitFor();await advance(15000);await page.evaluate(()=>window.__unmount());await settle();
    check(await timers()===0&&await page.evaluate(()=>window.__pending[0].request.signal.aborted),'Unmount aborts the pending poll and clears the deadline');
    await release('status',{body:{complete:true}});await advance(240000);
    check(await count('status')===1&&await count('colleges')===1,'Unmounted requests cannot schedule more work or reload saved matches');
    check(errors.length===0,'No browser runtime errors');
    fs.writeFileSync(receiptPath,JSON.stringify({status:'pass',checks,sourceHashes,scope:'Actual React component and API helper with synthetic Clerk/Next/API, fully intercepted browser networking and controlled timers. No layout/full Next/real service acceptance.'},null,2)+'\n');
    process.stdout.write(JSON.stringify({status:'pass',checks:checks.length,receipt:receiptPath})+'\n');
  } finally {await browser.close()}
})().catch(error=>{fs.writeFileSync(receiptPath,JSON.stringify({status:'failed',checks,error:String(error.stack||error),sourceHashes},null,2)+'\n');process.stderr.write(String(error.stack||error)+'\n');process.exitCode=1});
