// Isolated actual-component checks. No Next server, real session, backend, model or email.
// Run with an existing dependency tree; never install packages or read .env here.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

const frontend = path.resolve(__dirname, '..');
const deps = process.env.SPARQ_TEST_NODE_MODULES;
const playwrightPath = process.env.SPARQ_TEST_PLAYWRIGHT;
const receiptPath = process.env.SPARQ_TEST_RECEIPT;
if (!deps || !playwrightPath || !receiptPath) throw Error('Set explicit SPARQ_TEST_NODE_MODULES, SPARQ_TEST_PLAYWRIGHT and SPARQ_TEST_RECEIPT.');
const ts = require(path.join(deps, 'typescript'));
const { chromium } = require(playwrightPath);
const files = [
  'app/home/components/CombineHelpProvider.tsx', 'app/home/components/CombineHelpPanel.tsx',
  'app/home/components/ActivityRequirements.tsx', 'app/home/components/currentCombine.ts',
  'app/_lib/profileConnection.ts', 'app/quick-scan/QuickScanClient.tsx',
  'app/home/outreach/draft/page.tsx', 'app/home/components/WorkspaceAIPanel.tsx',
  'app/home/components/IterationBanner.tsx', 'app/home/components/artifactStatus.ts', 'app/_lib/api.ts', 'lib/backend-config.cjs',
];
const sourceHashes = {};
let bundle = "const process={env:{NODE_ENV:'development',NEXT_PUBLIC_BACKEND_URL:'http://127.0.0.1:4319'}};const modules={},cache={};\n";
for (const file of files) {
  const source = fs.readFileSync(path.join(frontend, file), 'utf8');
  sourceHashes[file] = crypto.createHash('sha256').update(source).digest('hex');
  const code = ts.transpileModule(source, { compilerOptions: {
    module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true,
  }}).outputText;
  bundle += `modules[${JSON.stringify(file.replace(/\.tsx?$/, ''))}]=function(require,module,exports){\n${code}\n};\n`;
}
bundle += `
window.__identity={isLoaded:true,user:{id:'athlete-a'}};window.__listeners=new Set();
window.__setIdentity=value=>{window.__identity=value;window.__listeners.forEach(fn=>fn())};
const useUser=()=>React.useSyncExternalStore(fn=>{window.__listeners.add(fn);return()=>window.__listeners.delete(fn)},()=>window.__identity);
window.__tokenPending=[];window.__jsonPending=[];
const token=async()=>{const mode=window.__tokenMode;if(mode?.pending)return new Promise(resolve=>window.__tokenPending.push(resolve));if(mode&&'value' in mode)return mode.value;return window.__identity.user?'fixture-'+window.__identity.user.id:null};

window.__navigation=[];const router={push:url=>window.__navigation.push(url),replace:url=>window.__navigation.push(url)};
window.__params={token:'fixture-invitation'};
window.__connectEventId=null;window.__searchParams={};
window.__events=[];window.addEventListener('sparq:artifact-updated',e=>window.__events.push(e.detail));
window.__requests=[];window.__pending=[];window.__streams=[];
window.__modes={};
const sse=(events)=>events.map(event=>'data: '+JSON.stringify(event)+'\\n\\n').join('');
function reply(kind,mode){
 if(mode.reject)throw Error('Synthetic network failure');
 if(mode.jsonPending)return {ok:true,status:200,json:()=>new Promise(resolve=>window.__jsonPending.push({kind,resolve}))};
 if(kind==='stream'){
  if(mode.streaming)return new Response(new ReadableStream({start(controller){controller.enqueue(new TextEncoder().encode(sse([{type:'text',text:'PRIVATE STREAM A'}])));window.__streams.push(controller)}}),{headers:{'content-type':'text/event-stream'}});
  return new Response(sse(mode.events||[{type:'session',session_id:mode.session||201},{type:'text',text:mode.text||'Synthetic answer'},{type:'done'}]),{status:mode.status||200,headers:{'content-type':'text/event-stream'}});
 }
 const defaults={workspaceProfile:{clerk_id:window.__identity.user?.id,maxpreps_data:null},colleges:{colleges:[]},dashboard:{first_name:'Jordan',last_name:'Synthetic',metrics:[]},profile:{found:false,has_sparq_profile:false,user_id:null},connect:{connected:true,user_id:4521,clerk_id:'athlete-a'},fork:{session_id:401,fork_scenario:'D3 only'},iteration:{child_id:32,explanation:'Synthetic revision'},claim:{valid:true,first_name:'Jordan',event_name:'Fixture Combine',claimed:false},redeem:{connected:true,clerk_id:window.__identity.user?.id,workspace_ready:true,user_id:4521}};
 return new Response(mode.badJSON?'not-json':JSON.stringify(mode.body===undefined?defaults[kind]:mode.body),{status:mode.status||200,headers:{'content-type':'application/json'}});
}
window.fetch=async(input,init={})=>{
 let url=new URL(String(input),location.origin);if(url.origin!==location.origin)throw Error('Blocked external fetch: '+url.origin);const __proxied=url.pathname.startsWith('/api/sparq/proxy/');const __auth=__proxied?(window.__identity.user?'Bearer fixture-'+window.__identity.user.id:null):new Headers(init.headers).get('Authorization');if(__proxied){const __o=url.pathname;url=new URL(__o.slice('/api/sparq/proxy'.length)+url.search,location.origin)}
 const request={url:url.href,path:url.pathname,method:init.method||'GET',body:init.body?JSON.parse(init.body):null,authorization:__auth,signal:init.signal};window.__requests.push(request);
 if(url.pathname==='/api/athlete/4521')return new Response(JSON.stringify({user_id:4521,first_name:'Jordan',last_name:'Fixture'}),{headers:{'content-type':'application/json'}});
 let kind=url.pathname.includes('/workspace/profile/')?'workspaceProfile':url.pathname.includes('/workspace/colleges/')?'colleges':url.pathname.includes('/dashboard/')?'dashboard':url.pathname.includes('/profile/by-owner/')?'profile':url.pathname.includes('/profile/connect')?'connect':url.pathname.includes('/iterate-via-agent')?'iteration':url.pathname.includes('/agent/stream')?'stream':url.pathname.includes('/agent/fork')?'fork':url.pathname.endsWith('/redeem')?'redeem':url.pathname.includes('/claims/')?'claim':null;
 if(!kind)throw Error('Unexpected synthetic endpoint '+url.pathname);
 const mode=window.__modes[kind]||{};
 if(mode.pending)return new Promise(resolve=>window.__pending.push({kind,resolve}));
 return reply(kind,mode);
};
window.__release=(kind,mode={})=>{const i=window.__pending.findIndex(p=>p.kind===kind);if(i<0)throw Error('No pending '+kind);window.__pending.splice(i,1)[0].resolve(reply(kind,mode))};
window.__endStreams=()=>{for(const controller of window.__streams){controller.enqueue(new TextEncoder().encode(sse([{type:'session',session_id:999},{type:'text',text:'LATE PRIVATE ANSWER'}])));controller.close()}window.__streams=[]};
const jsx=(type,props,key)=>React.createElement(type,{...props,...(key!==undefined?{key}:{})});
function load(id,from=''){
 if(id==='react')return React;
 if(id==='react/jsx-runtime')return {jsx,jsxs:jsx,Fragment:React.Fragment};
 if(id==='@/app/_lib/useSparqSession')return{useSparqSession:useUser,signOutOfSparq:async()=>{}};
 if(id==='@/components/SignOutButton')return{__esModule:true,default:()=>React.createElement('button',{'aria-label':'Sign out'},'Sign out')};
 if(id==='next/navigation')return {useRouter:()=>router,useParams:()=>window.__params};
 if(id==='next/dynamic')return {__esModule:true,default:loader=>{let component=null,promise=null;return function Dynamic(props){const [C,setC]=React.useState(()=>component);React.useEffect(()=>{let active=true;(promise||=(loader())).then(m=>{component=m.default||m;if(active)setC(()=>component)});return()=>{active=false}},[]);return C?React.createElement(C,props):null}}};
 if(id==='next/link')return {__esModule:true,default:({children,...props})=>React.createElement('a',props,children)};
 if(id==='react-markdown')return {__esModule:true,default:({children})=>React.createElement('div',null,children)};
 if(id.startsWith('@/'))id=id.slice(2);else if(id.startsWith('.')){const parts=(from.slice(0,from.lastIndexOf('/')+1)+id).split('/');const out=[];for(const part of parts){if(part==='..')out.pop();else if(part!=='.')out.push(part)}id=out.join('/')}
 if(cache[id])return cache[id].exports;const m={exports:{}};cache[id]=m;if(!modules[id])throw Error('Unknown module '+id);modules[id](x=>load(x,id),m,m.exports);return m.exports;
}
const root=ReactDOM.createRoot(document.getElementById('root'));
window.__mount=async(kind)=>{const id={quickscan:'app/quick-scan/QuickScanClient',outreach:'app/home/outreach/draft/page',workspace:'app/home/components/WorkspaceAIPanel'}[kind];const Component=load(id).default;const props=kind==='connect'?{eventId:window.__connectEventId}:kind==='connectPage'?{searchParams:window.__searchParams}:undefined;const content=kind==='claim'?await Component({params:window.__params}):React.createElement(Component,props);root.render(window.__strictMode?React.createElement(React.StrictMode,null,content):content)};
`;

const checks = [];
const origin = 'http://127.0.0.1:4319';
const assets = {
  '/': '<!DOCTYPE html><html><head><meta charset="utf-8"></head><body><div id="root"></div><script src="/react.js"></script><script src="/react-dom.js"></script><script src="/app.js"></script></body></html>',
  '/react.js': fs.readFileSync(path.join(deps, 'react/umd/react.development.js'), 'utf8'),
  '/react-dom.js': fs.readFileSync(path.join(deps, 'react-dom/umd/react-dom.development.js'), 'utf8'),
  '/app.js': bundle,
};

(async () => {
  const browser = await chromium.launch({ headless: true });
  let page;
  const errors = [];
  try {
    page = await browser.newPage();
    page.on('pageerror', e => errors.push(String(e)));
    await page.route('**/*', route => {
      const url = new URL(route.request().url());
      if (url.origin !== origin || !(url.pathname in assets)) return route.abort();
      return route.fulfill({ status: 200, contentType: url.pathname.endsWith('.js') ? 'application/javascript' : 'text/html', body: assets[url.pathname] });
    });
    const reset = async (kind = 'workspace', modes = {}, storage = {}, tokenMode = undefined, strictMode = false, connectContext = {}) => {
      await page.goto(origin);
      await page.evaluate(async ({ kind, modes, storage, tokenMode, strictMode, connectContext }) => {
        localStorage.clear();for(const [key,value] of Object.entries(storage))localStorage.setItem(key,value);
        window.__modes=modes;window.__tokenMode=tokenMode;window.__strictMode=strictMode;window.__connectEventId=connectContext.eventId??null;window.__searchParams=connectContext.searchParams||{};await window.__mount(kind);
      }, { kind, modes, storage, tokenMode, strictMode, connectContext });
    };
    const check = (condition, name) => { assert(condition, name); checks.push(name); };
    const settle = () => page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    const switchAccount = async (id = 'athlete-b') => {
      await page.evaluate(id => window.__setIdentity({ isLoaded: true, user: id ? { id } : null }), id);
      await settle();
    };
    const send = async text => {
      await page.locator('textarea').fill(text);
      await page.getByRole('button', { name: 'Send', exact: true }).click();
    };
    const previewConnection = async () => {
      await page.getByRole('button', { name: /I Know My Athlete Number/ }).click();
      await page.getByPlaceholder('e.g. 67782').fill('4521');
      await page.getByRole('button', { name: 'Find', exact: true }).click();
      await page.getByRole('button', { name: 'Check connection', exact: true }).waitFor();
    };

    const connectionFailures = [
      ['HTTP 401', {status:401}], ['HTTP 409', {status:409}], ['HTTP 503', {status:503}],
      ['network failure', {reject:true}], ['bad JSON', {badJSON:true}],
      ['missing fields', {body:{found:false}}],
      ['string found', {body:{found:'false',has_sparq_profile:false,user_id:null}}],
      ['missing profile flag', {body:{found:true,user_id:4521}}],
      ['zero athlete id', {body:{found:true,has_sparq_profile:true,user_id:0}}],
      ['string athlete id', {body:{found:true,has_sparq_profile:true,user_id:'4521'}}],
      ['unsafe athlete id', {body:{found:true,has_sparq_profile:true,user_id:9007199254740992}}],
      ['unlinked with athlete id', {body:{found:false,has_sparq_profile:false,user_id:4521}}],
    ];

    for(const kind of ['quickscan','outreach']){
      for(const [name,mode] of connectionFailures){
        await reset(kind,{profile:mode});
        await page.getByText(/Sign in again to check|connection needs review|could not|Synthetic network failure/).first().waitFor().catch(async e=>{throw Error(kind+' '+name+': '+await page.locator('body').innerText()+'; runtime '+errors.join('; '))});
        check(await page.getByRole('heading',{name:'Connect Your Athlete Profile',exact:true}).count()===0&&await page.getByText('Complete onboarding first to draft outreach emails.',{exact:true}).count()===0,kind+' '+name+' remains an unconfirmed lookup rather than a new-athlete/onboarding assertion');
        check(await page.evaluate(()=>!window.__requests.some(r=>r.path.includes('/dashboard/')||r.method!=='GET')),kind+' '+name+' does not fetch an athlete dashboard or perform writes');
      }
      await reset(kind,{profile:{pending:true}});await page.waitForFunction(()=>window.__pending.some(p=>p.kind==='profile'));
      await page.evaluate(()=>window.__modes.profile={status:409});await switchAccount();
      await page.getByText(/connection needs review/).waitFor();
      await page.evaluate(()=>window.__release('profile',{body:{found:true,has_sparq_profile:true,user_id:4521}}));await settle();
      check(await page.getByText(/connection needs review/).isVisible()&&await page.evaluate(()=>!window.__requests.some(r=>r.path.includes('/dashboard/'))),kind+' ignores old-account successful connection lookup after identity changes');
    }

    await reset('outreach',{profile:{body:{found:true,has_sparq_profile:true,user_id:4521}},colleges:{body:{colleges:[{id:501,college_name:'PRIVATE COLLEGE A'}]}},workspaceProfile:{body:{clerk_id:'athlete-a',maxpreps_data:{name:'CURRENT OWNER A',position:'QB'}}}});
    await page.getByRole('textbox',{name:'Email draft',exact:true}).waitFor();
    await page.getByRole('textbox',{name:'Email draft',exact:true}).fill('PRIVATE DRAFT A');
    await page.evaluate(()=>window.__modes.profile={status:409});await switchAccount();
    await page.getByText(/connection needs review/).waitFor();
    check(await page.getByRole('textbox',{name:'Email draft',exact:true}).count()===0&&await page.getByRole('option',{name:'PRIVATE COLLEGE A'}).count()===0&&await page.getByRole('button',{name:'Copy Email',exact:true}).count()===0,'Outreach A success then B conflict clears private draft/college and disables write action');

    await reset('outreach',{profile:{pending:true},colleges:{body:{colleges:[{id:502,college_name:'Synthetic College'}]}},workspaceProfile:{body:{clerk_id:'athlete-a',maxpreps_data:{name:'CURRENT OWNER A',position:'QB'}}}});
    await page.waitForFunction(()=>window.__pending.some(p=>p.kind==='profile'));
    await page.evaluate(()=>{sessionStorage.setItem('sparq.onboarding.maxprepsData',JSON.stringify({name:'STALE PRIVATE ATHLETE'}));window.__release('profile',{body:{found:true,has_sparq_profile:true,user_id:4521}})});
    await page.getByRole('textbox',{name:'Email draft',exact:true}).waitFor();
    check((await page.getByRole('textbox',{name:'Email draft',exact:true}).inputValue()).includes('CURRENT OWNER A')&&!(await page.getByRole('textbox',{name:'Email draft',exact:true}).inputValue()).includes('STALE PRIVATE ATHLETE'),'Outreach draft uses caller-confirmed workspace profile instead of unowned sessionStorage');

    await page.evaluate(()=>{window.__modes.profile={body:{found:true,has_sparq_profile:true,user_id:4522}};window.__modes.workspaceProfile={body:{clerk_id:'athlete-b',maxpreps_data:{name:'CURRENT OWNER B',position:'WR'}}};window.__modes.colleges={body:{colleges:[{id:503,college_name:'COLLEGE B'}]}}});
    await switchAccount();
    await page.getByRole('textbox',{name:'Email draft',exact:true}).waitFor();
    const ownerBDraft=await page.getByRole('textbox',{name:'Email draft',exact:true}).inputValue();
    check(ownerBDraft.includes('CURRENT OWNER B')&&!ownerBDraft.includes('CURRENT OWNER A')&&!ownerBDraft.includes('STALE PRIVATE ATHLETE'),'Successful account switch uses only owner B saved profile');

    await reset('outreach',{profile:{body:{found:true,has_sparq_profile:true,user_id:4521}},workspaceProfile:{body:{clerk_id:'athlete-b',maxpreps_data:{name:'WRONG OWNER PRIVATE'}}}});
    await page.getByRole('alert').waitFor();
    check((await page.getByRole('alert').innerText()).includes('confirm the owner')&&await page.getByRole('textbox',{name:'Email draft',exact:true}).count()===0&&!(await page.locator('body').innerText()).includes('WRONG OWNER PRIVATE'),'Wrong-owner workspace response never enters the outreach draft');
    await page.evaluate(()=>window.__modes.workspaceProfile={body:{clerk_id:'athlete-a',maxpreps_data:{name:'RETRIED OWNER A'}}});
    await page.getByRole('button',{name:'Retry profile check',exact:true}).click();
    await page.getByRole('textbox',{name:'Email draft',exact:true}).waitFor();
    check(await page.evaluate(()=>window.__requests.every(r=>r.method==='GET')),'Outreach retry reconfirms profile with reads only');

    await reset('quickscan',{profile:{status:503}});
    await page.getByRole('button',{name:'Retry profile check',exact:true}).waitFor();
    await page.evaluate(()=>window.__modes.profile={body:{found:false,has_sparq_profile:false,user_id:null}});
    await page.getByRole('button',{name:'Retry profile check',exact:true}).click();
    await page.getByRole('heading',{name:'Connect Your Athlete Profile',exact:true}).waitFor();
    check(await page.evaluate(()=>window.__requests.filter(r=>r.path.includes('/profile/by-owner/')).length===2&&window.__requests.every(r=>r.method==='GET')),'QuickScan retry can confirm unlinked state without writes');

    await reset('outreach',{profile:{body:{found:true,has_sparq_profile:true,user_id:4521}},colleges:{body:{colleges:[{id:504,college_name:'Synthetic Clipboard College'}]}}});
    await page.getByRole('textbox',{name:'Email draft',exact:true}).waitFor();
    await page.evaluate(()=>Object.defineProperty(navigator,'clipboard',{configurable:true,value:{writeText:()=>new Promise(resolve=>{window.__releaseClipboard=resolve})}}));
    await page.getByRole('button',{name:'Copy Email',exact:true}).click();
    await page.waitForFunction(()=>!!window.__releaseClipboard);
    await page.evaluate(()=>window.__modes.profile={status:409});await switchAccount();
    await page.getByRole('alert').waitFor();
    await page.evaluate(()=>window.__releaseClipboard());await settle();
    check(await page.evaluate(()=>!window.__requests.some(r=>r.method==='POST'))&&await page.getByRole('textbox',{name:'Email draft',exact:true}).count()===0,'Account change during clipboard wait suppresses old-account outreach POST and draft');

    await reset('workspace', { stream: { streaming: true } }, { 'sparq_conv_athlete-a': '101' });
    await send('PRIVATE REQUEST A');await page.getByText('PRIVATE STREAM A', { exact: true }).waitFor();
    check(await page.evaluate(() => new URL(window.__requests.find(r => r.path.includes('/agent/stream')).url).searchParams.get('conversation_id')) === '101', 'Chat restores only this account’s stored conversation ID');
    await switchAccount();await page.evaluate(() => window.__endStreams());await settle();
    check(await page.getByText('PRIVATE REQUEST A', { exact: true }).count() === 0 && await page.getByText('PRIVATE STREAM A', { exact: true }).count() === 0 && await page.getByText('LATE PRIVATE ANSWER', { exact: true }).count() === 0, 'Account switch clears visible chat and ignores late stream chunks');
    check(await page.evaluate(() => window.__requests[0].signal.aborted && localStorage.getItem('sparq_conv_athlete-a') === '101'), 'Account switch aborts stream and prevents late conversation persistence');
    await page.evaluate(() => window.__modes.stream = {});await send('NEW ACCOUNT QUESTION');await page.getByText('Synthetic answer', { exact: true }).waitFor();
    check(await page.evaluate(() => { const r=window.__requests.at(-1),u=new URL(r.url);return u.searchParams.get('athlete_id')==='athlete-b'&&!u.searchParams.has('conversation_id')&&r.authorization==='Bearer fixture-athlete-b'; }), 'New account cannot inherit old conversation and uses its own token');
    await switchAccount(null);check(await page.getByText('Sign in to use your recruiting AI.', { exact: true }).isVisible() && await page.getByText('Synthetic answer', { exact: true }).count() === 0, 'Signout hides all workspace chat state');

    await reset('workspace', { fork: { pending: true } });
    await page.getByRole('button', { name: /What if/ }).click();
    await page.getByPlaceholder('e.g. I switched to tight end...').fill('D3 only');await page.getByRole('button', { name: 'Explore scenario →', exact: true }).click();
    await switchAccount();await page.evaluate(() => window.__release('fork'));await settle();
    check(await page.evaluate(() => window.__requests.find(r => r.path.includes('/agent/fork')).signal.aborted) && await page.getByText(/different lens/).count() === 0, 'Account switch cancels pending fork and ignores its response');
    await send('After canceled fork');await page.getByText('Synthetic answer', { exact: true }).waitFor();
    check(await page.evaluate(() => !new URL(window.__requests.at(-1).url).searchParams.has('fork_scenario')), 'New account has no inherited fork scenario');
    await reset();await page.getByRole('button', { name: /What if/ }).click();await page.getByPlaceholder('e.g. I switched to tight end...').fill('D3 only');await page.getByRole('button', { name: 'Explore scenario →', exact: true }).click();await page.getByText(/different lens/).waitFor();
    await send('Question in fork');await page.getByText('Synthetic answer', { exact: true }).waitFor();
    check(await page.evaluate(() => {const p=new URL(window.__requests.at(-1).url).searchParams;return p.get('conversation_id')==='401'&&p.get('fork_scenario')==='D3 only'}), 'Confirmed fork uses its own conversation and scenario');
    await switchAccount();check(await page.getByText(/different lens/).count() === 0 && await page.getByText(/What if: D3 only/).count() === 0, 'Account switch clears an established fork and its messages');

    const scopeArtifact = () => page.evaluate(() => window.dispatchEvent(new CustomEvent('sparq:artifact-opened', { detail: { artifactId: 31, type: 'outreach_draft', title: 'PRIVATE DRAFT A', agent_id: 'drafter' } })));
    await reset();await scopeArtifact();await send('Make it shorter');await page.getByText('Synthetic revision', { exact: true }).waitFor();
    check(await page.evaluate(() => {const r=window.__requests.at(-1);return r.path==='/api/artifacts/31/iterate-via-agent'&&r.authorization==='Bearer fixture-athlete-a'&&r.body.performed_by==='athlete-a'&&window.__events[0].childId===32}), 'Artifact iteration uses authenticated helper and confirms returned child');
    await reset('workspace', { iteration: { status: 403 } });await scopeArtifact();await send('Try revision');await page.getByText("I couldn't rewrite that — try again, or rephrase.", { exact: true }).waitFor();
    check(await page.evaluate(() => window.__events.length) === 0, 'Failed artifact iteration shows error without navigation event');
    await reset('workspace', { iteration: { pending: true } });await scopeArtifact();await send('Delayed revision');await switchAccount();await page.evaluate(() => window.__release('iteration'));await settle();
    check(await page.evaluate(() => window.__requests.at(-1).signal.aborted && window.__events.length === 0) && await page.getByText(/PRIVATE DRAFT A/).count() === 0, 'Account switch clears artifact scope and suppresses late iteration event');

    for (const [name, mode] of [['HTTP failure', { status: 401 }], ['SSE error', { events: [{ type: 'error', message: 'Synthetic provider failure' }] }]]) {
      await reset('workspace', { stream: mode });await send('Question');await page.getByText("I'm having trouble connecting right now. Please try again in a moment.", { exact: true }).waitFor();
      check(await page.getByRole('button', { name: /Which college should I contact first/ }).count() === 0, `Chat reports ${name} instead of a blank success`);
    }
    await reset('workspace', { stream: { pending: true } });await settle();
    await page.evaluate(() => {for(let i=0;i<2;i++)window.dispatchEvent(new CustomEvent('sparq:proactive-prompt', { detail: { prompt: 'Synthetic proactive request' } }))});
    await page.waitForFunction(() => window.__pending.length === 1);
    check(await page.evaluate(() => window.__requests.filter(r => r.path.includes('/agent/stream')).length) === 1, 'Concurrent proactive events start at most one request');
    await page.evaluate(() => window.__release('stream'));await page.getByText('Synthetic answer', { exact: true }).waitFor();

    check(errors.length === 0, 'No component runtime errors in synthetic cases');
    fs.writeFileSync(receiptPath, JSON.stringify({ status: 'pass', checks, sourceHashes,
      scope: 'Actual source compiled with TypeScript and rendered with React 18 in Chromium. Synthetic SPARQ session, Next navigation, plain-text Markdown and in-memory fetch responses; browser network intercepted. No Next middleware/layout, live identity/backend/provider, production or full-mobile acceptance.',
    }, null, 2) + '\n');
    console.log(JSON.stringify({ status: 'pass', count: checks.length, checks }, null, 2));
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode = 1; });
