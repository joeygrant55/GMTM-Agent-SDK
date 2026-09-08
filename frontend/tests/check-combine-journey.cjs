// Actual source + React + generated Tailwind CSS in Chromium, with synthetic identity/API.
// No Next server, live requests, environment files, installs or external services.
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
  'app/home/HomeClient.tsx', 'app/home/layout.tsx', 'app/home/components/WorkspaceShell.tsx', 'app/home/components/CombineWorkspaceShell.tsx',
  'app/home/components/CurrentCombineCard.tsx', 'app/home/components/currentCombine.ts',
  'app/home/components/ActivityRequirements.tsx',
  'app/home/components/InboxFeed.tsx', 'app/home/components/AthleteStartingPoint.tsx',
  'app/home/components/WorkspaceSidebar.tsx', 'app/home/components/WorkspaceAIPanel.tsx',
  'app/home/components/IterationBanner.tsx', 'app/home/components/ArtifactCard.tsx',
  'app/home/components/ArtifactStatusPill.tsx', 'app/home/components/SpecialistAvatar.tsx',
  'app/home/components/artifactStatus.ts', 'app/athlete/[id]/components/CombineResultsCard.tsx',
  'app/athlete/[id]/components/combineResults.ts', 'app/_lib/api.ts', 'lib/backend-config.cjs', 'app/claim/[token]/redeem/page.tsx',
];
const sourceHashes = {}, rawSources = [];
let bundle = "const process={env:{NODE_ENV:'development',NEXT_PUBLIC_BACKEND_URL:'http://127.0.0.1:4320'}};const modules={},cache={};\n";
for (const file of files) {
  const source = fs.readFileSync(path.join(frontend, file), 'utf8');
  sourceHashes[file] = crypto.createHash('sha256').update(source).digest('hex');
  rawSources.push({ raw: source, extension: 'tsx' });
  const code = ts.transpileModule(source, { compilerOptions: { module: ts.ModuleKind.CommonJS, target: ts.ScriptTarget.ES2020, jsx: ts.JsxEmit.ReactJSX, esModuleInterop: true }}).outputText;
  bundle += `modules[${JSON.stringify(file.replace(/\.tsx?$/, ''))}]=function(require,module,exports){\n${code}\n};\n`;
}
const fixtureFile = path.join(frontend, '../backend/tests/fixtures/usaf_2027_combine2_public.json');
const publicFixture = JSON.parse(fs.readFileSync(fixtureFile, 'utf8'));
sourceHashes['../backend/tests/fixtures/usaf_2027_combine2_public.json'] = crypto.createHash('sha256').update(fs.readFileSync(fixtureFile)).digest('hex');
bundle += `
const definitions=${JSON.stringify(publicFixture.events)};
window.__identity={isLoaded:true,user:{id:'athlete-a',firstName:'Jordan'}};window.__listeners=new Set();
window.__setIdentity=value=>{window.__identity=value;window.__listeners.forEach(fn=>fn())};
const subscribe=fn=>{window.__listeners.add(fn);return()=>window.__listeners.delete(fn)};
const useUser=()=>React.useSyncExternalStore(subscribe,()=>window.__identity);
window.__route={pathname:'/home/inbox',query:'event_id=1317'};window.__routeListeners=new Set();
window.__setRoute=url=>{const u=new URL(url,location.origin);window.__route={pathname:u.pathname,query:u.search.slice(1)};history.pushState({},'',url);window.__routeListeners.forEach(fn=>fn())};
const useRoute=()=>React.useSyncExternalStore(fn=>{window.__routeListeners.add(fn);return()=>window.__routeListeners.delete(fn)},()=>window.__route);
window.__navigation=[];const router={push:url=>{window.__navigation.push(url);window.__setRoute(url)},replace:url=>{window.__navigation.push(url);window.__setRoute(url)}};
const token=async()=>window.__identity.user?'fixture-'+window.__identity.user.id:null;window.Clerk={session:{getToken:token}};
window.__params={token:'fixture-claim'};window.__requests=[];window.__pending=[];window.__mode={};window.__external=[];
window.__nowOffset=0;const realNow=Date.now;Date.now=()=>realNow()+window.__nowOffset;
document.addEventListener('click',event=>{const a=event.target.closest('a');if(a&&a.href.startsWith('https://')){event.preventDefault();window.__external.push(a.href)}});
function snapshot(owner,eventId,mode={}){
 const choices=definitions.map(d=>({event_id:d.event.event_id,name:d.event.name,division:d.event.event_id===1317?'Junior':'Adult',continuation_url:'https://gmtm.com/virtuals/'+d.event.event_id}));
 const selected=eventId||mode.claimEvent||null;const d=definitions.find(d=>d.event.event_id===selected);const linked=!mode.unlinked;
 const activities=d?d.tasks.map(t=>{const required=t.questions.filter(q=>q.required);const complete=(mode.present||[]).includes(t.task_id);const submitted=complete||(mode.submitted||[]).includes(t.task_id);return{task_id:t.task_id,event_id:t.event_id,title:t.title,order:t.list_order,kind:t.list_order===0?'background':t.list_order===1?'highlight':'exercise',description:'Synthetic organizer instruction for '+t.title+'. Record the requested evidence in GMTM.',continuation_url:'https://gmtm.com/virtuals/'+selected,submission_state:!linked?'unavailable':submitted?'submitted':'not_submitted',evidence_state:!linked||(mode.unknown||[]).includes(t.task_id)?'unknown':complete?'fields_present':'missing_fields',missing_fields:!linked||complete?[]:required.map(q=>q.title),required_field_count:required.length,required_fields:required.map(q=>({type:q.type,title:q.title})),submitted_at:submitted?'2026-09-06T12:00:00Z':null}}):[];
 return{schema_version:1,clerk_id:owner,athlete_id:linked?(owner==='athlete-a'?4521:4522):null,state:!linked?'link_required':d?'ready':'choose_event',events:choices,selected_event:d?{...choices.find(e=>e.event_id===selected),deadline_display:'September 21, 2026',deadline_source_url:'https://usafootball.com/national-team/digital-combine',configured_end:d.event.end_date}:null,activities,counts:{activities:activities.length,submitted:linked&&d?activities.filter(a=>a.submission_state==='submitted').length:null,fields_present:linked&&d?activities.filter(a=>a.evidence_state==='fields_present').length:null},fetched_at:'2026-09-06T12:00:00Z',athlete_id_status:'unknown'};
}
window.__snapshot=snapshot;
window.fetch=async(input,init={})=>{
 const url=new URL(String(input),location.origin);if(url.origin!==location.origin)throw Error('Blocked external fetch');
 const owner=window.__identity.user?.id;const kind=url.pathname==='/api/combine/current'?'combine':url.pathname.includes('/workspace/profile/')?'profile':url.pathname.includes('/workspace/inbox/')?'inbox':url.pathname.includes('/workspace/badges/')?'badges':url.pathname.endsWith('/redeem')?'redeem':null;
 if(!kind)throw Error('Unexpected API request '+url.pathname);
 const eventId=Number(url.searchParams.get('event_id'))||null;const mode=window.__mode[kind]||{};
 const body=mode.body!==undefined?mode.body:kind==='combine'?snapshot(owner,eventId,mode):kind==='profile'?{clerk_id:owner,combine_results:[],hudl_url:null}:kind==='inbox'?{artifacts:[]}:kind==='badges'?{}:{connected:true,clerk_id:owner,user_id:4521,workspace_ready:false,event_id:1317};
 const request={kind,eventId,owner,url:url.href,method:init.method||'GET',authorization:new Headers(init.headers).get('Authorization'),signal:init.signal};window.__requests.push(request);
 const reply=()=>{if(mode.reject)throw Error('Synthetic request failure');return new Response(JSON.stringify(body),{status:mode.status||200,headers:{'content-type':'application/json'}})};
 if(mode.pending)return new Promise(resolve=>window.__pending.push({request,resolve,reply}));
 if(mode.jsonPending)return{ok:true,status:200,json:()=>new Promise(resolve=>window.__pending.push({request,resolve,reply:()=>body}))};
 return reply();
};
window.__release=()=>{const p=window.__pending.shift();if(!p)throw Error('No pending response');p.resolve(p.reply())};
const jsx=(type,props,key)=>React.createElement(type,{...props,...(key!==undefined?{key}:{})});
function load(id,from=''){
 if(id==='react')return React;
 if(id==='react/jsx-runtime')return{jsx,jsxs:jsx,Fragment:React.Fragment};
 if(id==='@clerk/nextjs')return{useUser,UserButton:()=>React.createElement('button',{'aria-label':'Account'},'Account'),useAuth:()=>{const s=useUser();return{isLoaded:s.isLoaded,isSignedIn:!!s.user,userId:s.user?.id,getToken:token}}};
 if(id==='next/navigation')return{useRouter:()=>router,useParams:()=>window.__params,usePathname:()=>useRoute().pathname,useSearchParams:()=>new URLSearchParams(useRoute().query)};
 if(id==='next/link')return{__esModule:true,default:({children,...props})=>React.createElement('a',{...props,onClick:e=>{props.onClick?.(e);if(!e.defaultPrevented){e.preventDefault();router.push(props.href)}}},children)};
 if(id==='next/dynamic')return{__esModule:true,default:loader=>{let component=null,promise=null;return function Dynamic(props){const [C,setC]=React.useState(()=>component);React.useEffect(()=>{let active=true;(promise||=(loader())).then(m=>{component=m.default||m;if(active)setC(()=>component)});return()=>{active=false}},[]);return C?React.createElement(C,props):null}}};
 if(id==='react-markdown')return{__esModule:true,default:({children})=>React.createElement('div',null,children)};
 if(id.startsWith('@/'))id=id.slice(2);else if(id.startsWith('.')){const parts=(from.slice(0,from.lastIndexOf('/')+1)+id).split('/'),out=[];for(const part of parts){if(part==='..')out.pop();else if(part!=='.')out.push(part)}id=out.join('/')}
 if(cache[id])return cache[id].exports;const m={exports:{}};cache[id]=m;if(!modules[id])throw Error('Unknown module '+id);modules[id](x=>load(x,id),m,m.exports);return m.exports;
}
const root=ReactDOM.createRoot(document.getElementById('root'));
window.__mount=(kind='shell',strict=false)=>{const id=kind==='home'?'app/home/HomeClient':kind==='redeem'?'app/claim/[token]/redeem/page':kind==='card'?'app/home/components/CurrentCombineCard':'app/home/layout';const C=load(id).default;const child=kind==='shell'?React.createElement(load('app/home/components/InboxFeed').default):null;const content=React.createElement(C,null,child);root.render(strict?React.createElement(React.StrictMode,null,content):content)};
`;

(async () => {
  const postcss = require(path.join(deps, 'postcss'));
  const tailwind = require(path.join(deps, 'tailwindcss'));
  const loadConfig = require(path.join(deps, 'tailwindcss/lib/lib/load-config.js')).loadConfig;
  const config = loadConfig(path.join(frontend, 'tailwind.config.ts'));
  sourceHashes['tailwind.config.ts'] = crypto.createHash('sha256').update(fs.readFileSync(path.join(frontend, 'tailwind.config.ts'))).digest('hex');
  const css = (await postcss([tailwind({ ...config, content: rawSources })]).process('@tailwind base;@tailwind components;@tailwind utilities;', { from: undefined })).css;
  const origin='http://127.0.0.1:4320';
  const assets={
    '/':'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/style.css"></head><body><div id="root"></div><script src="/react.js"></script><script src="/react-dom.js"></script><script src="/app.js"></script></body></html>',
    '/style.css':css,'/app.js':bundle,'/sparq-logo.jpg':fs.readFileSync(path.join(frontend,'public/sparq-logo.jpg')),
    '/react.js':fs.readFileSync(path.join(deps,'react/umd/react.development.js'),'utf8'),
    '/react-dom.js':fs.readFileSync(path.join(deps,'react-dom/umd/react-dom.development.js'),'utf8'),
  };
  const browser=await chromium.launch({headless:true});
  const checks=[],errors=[],screenshots=[];
  try {
    const page=await browser.newPage({viewport:{width:390,height:844}});
    page.on('pageerror',e=>errors.push(String(e)));
    await page.route('**/*',route=>{const u=new URL(route.request().url());const key=u.pathname.startsWith('/home')?'/':u.pathname;if(u.origin!==origin||!(key in assets))return route.abort();return route.fulfill({status:200,contentType:key.endsWith('.js')?'application/javascript':key.endsWith('.css')?'text/css':key.endsWith('.jpg')?'image/jpeg':'text/html',body:assets[key]})});
    const check=(condition,name)=>{assert(condition,name);checks.push(name)};
    const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const reset=async({kind='shell',query='event_id=1317',modes={},user='athlete-a',strict=false}={})=>{await page.goto(origin);await page.evaluate(({kind,query,modes,user,strict})=>{window.__setRoute('/home/inbox'+(query?'?'+query:''));window.__mode=modes;window.__setIdentity({isLoaded:true,user:user?{id:user,firstName:'Jordan'}:null});window.__mount(kind,strict)}, {kind,query,modes,user,strict})};
    const ready=()=>page.getByRole('button',{name:'Refresh progress',exact:true}).waitFor();
    const switchAccount=async id=>{await page.evaluate(id=>window.__setIdentity({isLoaded:true,user:id?{id}:null}),id);await settle()};
    const refresh=async(mode={},auto=false)=>{await page.evaluate(({mode,auto})=>{window.__mode.combine=mode;window.__nowOffset+=1100;if(auto){window.dispatchEvent(new Event('focus'));document.dispatchEvent(new Event('visibilitychange'));window.dispatchEvent(new Event('pageshow'))}}, {mode,auto});if(!auto)await page.getByRole('button',{name:'Refresh progress',exact:true}).click();await ready()};
    const activity=title=>page.getByRole('list',{name:'Combine activities'}).locator(':scope > li').filter({has:page.getByRole('heading',{name:new RegExp(title)})});
    const noOverflow=()=>page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth&&document.getElementById('workspace-main').scrollWidth<=document.getElementById('workspace-main').clientWidth);
    await reset({modes:{profile:{status:503},inbox:{status:503}}});await ready();
    check(await page.getByRole('list',{name:'Combine activities'}).locator(':scope > li').count()===9,'Zero-result combine renders nine real-config activities despite failed profile and inbox');
    check(await page.getByText('0 of 9 activities submitted',{exact:true}).isVisible(),'Zero submissions stay distinct from missing numeric results');
    check(await page.getByText('Next: Athlete Background',{exact:true}).isVisible(),'Background requirements are the first grounded action before results');
    check(await page.locator('#workspace-main').getByRole('link',{name:'Continue in GMTM',exact:false}).getAttribute('href')==='https://gmtm.com/virtuals/1317','Primary continuation is the verified GMTM event');
    check(await page.getByRole('link',{name:'Add your highlight link',exact:true}).count()===0,'No duplicate film starter displaces current-combine action');
    check(await page.getByText(/Published deadline:/).innerText().then(t=>t.includes('September 21, 2026')&&!t.includes('September 22')),'Deadline is official date-only without configured countdown');
    check(await page.getByText(/Athlete ID validity is not checked here/).count()===1,'Athlete ID validity remains explicitly unknown');
    check(await page.evaluate(()=>window.__requests.find(r=>r.kind==='combine').authorization)==='Bearer fixture-athlete-a','Combine read uses the authenticated helper');
    await page.locator('#workspace-main').getByRole('link',{name:'Continue in GMTM',exact:false}).click();
    check(await page.evaluate(()=>window.__external[0])==='https://gmtm.com/virtuals/1317'&&await page.getByText('0 of 9 activities submitted',{exact:true}).count()===1,'Opening GMTM does not mark progress or call a write endpoint');
    check(await page.evaluate(()=>window.__requests.every(r=>r.method==='GET')),'Current-combine flow makes only reads');

    await reset({query:''});await ready();
    check(await page.getByRole('combobox',{name:'Combine division'}).inputValue()===''&&await page.getByRole('list',{name:'Combine activities'}).count()===0,'No event or numeric result guess: explicit division choice');
    await page.getByRole('combobox',{name:'Combine division'}).selectOption('1318');await ready();
    check(await page.getByRole('heading',{name:/Adult Digital Combine/}).isVisible()&&await page.evaluate(()=>window.__route.query)==='event_id=1318','Adult selection is reflected in URL and correct source event');
    check((await activity('20-Yard Dash').getByText(/^Still needed:/).innerText()).includes('20-yard dash time'),'Missing progress uses the actual 20-yard activity distance');
    await activity('20-Yard Dash').locator('summary').click();
    const dashFields=activity('20-Yard Dash').getByRole('group',{name:'What you’ll submit'});
    check(await dashFields.getByText('40 Yard Dash Time',{exact:true}).isVisible()&&await dashFields.getByText('20 Yard Dash',{exact:true}).isVisible()&&await dashFields.getByText('Video',{exact:true}).isVisible(),'Organizer form retains exact dash labels and separate video requirement');
    check(await dashFields.getByText(/known mismatch/).isVisible(),'Exact incorrect caption is explained as 20-yard dash, not a second distance');
    await reset({query:'event_id=999',modes:{combine:{claimEvent:1317}}});await ready();check(await page.getByRole('alert').innerText().then(t=>t.includes('not available'))&&await page.getByRole('combobox').inputValue()===''&&await page.getByRole('list',{name:'Combine activities'}).count()===0,'Unsupported event suppresses a saved-claim default and shows an explicit public chooser');
    await reset({query:'',modes:{combine:{claimEvent:1317}}});await ready();check(await page.getByRole('combobox').inputValue()==='1317','One backend-confirmed redeemed claim may supply event context');

    await reset({query:'event_id=1318',modes:{combine:{claimEvent:1317}}});await ready();
    await page.getByRole('button',{name:'Menu',exact:true}).click();
    await page.getByRole('link',{name:'⚡ My next move',exact:true}).click();await ready();
    check(await page.getByRole('heading',{name:/Adult Digital Combine/}).count()===1&&await page.getByRole('combobox',{name:'Combine division'}).inputValue()==='1318'&&await page.evaluate(()=>window.__route.query)==='event_id=1318','My next move preserves an explicit adult selection despite a saved junior claim');

    await reset({modes:{combine:{unlinked:true}}});await ready();
    check(await page.getByRole('list',{name:'Combine activities'}).locator(':scope > li').count()===9&&await page.getByText(/9 organizer activities · personal progress unavailable/).count()===1,'Unlinked athlete can read public requirements without fake zero personal counts');
    check(await page.getByText('Progress unavailable',{exact:true}).count()===9&&await page.getByRole('link',{name:'Check an existing connection'}).isVisible(),'Unlinked activity state and secure recovery are visible');
    await activity('Stick Overhead Squat').locator('summary').click();
    const unlinkedFields=activity('Stick Overhead Squat').getByRole('group',{name:'What you’ll submit'});
    check(await unlinkedFields.getByText('Video',{exact:true}).isVisible()&&await unlinkedFields.getByText('Stick Overhead Squat',{exact:true}).isVisible(),'Unlinked athlete sees video-only public requirement despite no personal progress');
    check(await unlinkedFields.getByText('Measurement or count',{exact:true}).count()===0,'Video-only squat does not invent a numeric result field');
    await reset({query:'',modes:{combine:{unlinked:true}}});await ready();check(await page.getByRole('combobox').inputValue()===''&&await page.getByRole('list',{name:'Combine activities'}).count()===0,'Unlinked athlete without event receives public choices and no invented progress');

    await reset({modes:{combine:{present:[4906],submitted:[4900,4901],unknown:[4901]}}});await ready();
    check(await page.getByText('3 of 9 activities submitted',{exact:true}).isVisible()&&await page.getByText('Required information saved for 1 activities',{exact:true}).isVisible(),'Submission count and activities with required fields present are separate');
    check(await activity('Stick Overhead Squat').getByText('Saved information found').count()===1,'Video-only squat can have all required fields without a numeric result');
    check(await activity('Highlight Reel').getByText(/Additional playing footage/).count()===1&&await activity('Highlight Reel').getByText('Submitted',{exact:true}).count()===1,'Separate playing-footage activity retains its own submission state');
    check(await activity('Max. Push-Ups').getByText(/Some saved information could not be checked/).count()===1,'Malformed submission evidence stays submitted but unknown');
    check((await activity('5-10-5 Shuttle Run').getByText(/^Still needed:/).innerText()).includes('Starting to the Right')&&(await activity('5-10-5 Shuttle Run').getByText(/^Still needed:/).innerText()).includes('Starting to the Left'),'Both directional shuttle field labels are retained');
    await activity('Stick Overhead Squat').locator('summary').click();check(await activity('Stick Overhead Squat').getByText(/Synthetic organizer instruction/).isVisible(),'Contextual organizer instructions expand within the real activity');
    const before=await page.evaluate(()=>window.__requests.filter(r=>r.kind==='combine').length);
    await refresh({status:503},true);
    check(await page.getByRole('alert').innerText().then(t=>t.includes('last successful check'))&&await page.getByText('3 of 9 activities submitted',{exact:true}).count()===1,'Failed return refresh keeps the previous snapshot with a visible stale warning');
    check(await page.evaluate(()=>window.__requests.filter(r=>r.kind==='combine').length)===before+1,'Focus visibility and pageshow refreshes are deduplicated and throttled');
    await refresh({present:[4896,4900,4906]});check(await page.getByText('Required information saved for 3 activities',{exact:true}).count()===1&&await page.getByRole('alert').count()===0,'Manual refresh updates authoritative fixture progress and clears the stale warning');
    await refresh({present:publicFixture.events[0].tasks.map(t=>t.task_id)});
    check(await page.getByText('9 of 9 activities submitted',{exact:true}).count()===1&&await page.getByRole('link',{name:'Review your athlete profile',exact:true}).count()===1,'All submitted activities lead to continuing profile review without selection or completion claims');

    for(const stage of ['pending','jsonPending']){
      await reset({kind:'card',modes:{combine:{[stage]:true}}});await page.waitForFunction(()=>window.__pending.length===1);
      await page.evaluate(()=>window.__mode.combine={});await switchAccount('athlete-b');await ready();await page.evaluate(()=>window.__release());await settle();
      check(await page.evaluate(()=>window.__requests[0].signal.aborted)&&await page.getByText('0 of 9 activities submitted',{exact:true}).count()===1, 'Account switch aborts and ignores a late valid '+stage+' snapshot');
      check(await page.evaluate(()=>window.__requests.at(-1).authorization)==='Bearer fixture-athlete-b','New account '+stage+' uses its own token');
      check(await page.getByRole('alert').count()===0,'Late old-account '+stage+' cannot inject an error into the new account');
    }
    await reset({kind:'card'});await ready();
    await page.evaluate(()=>{window.__mode.combine={pending:true,present:[4896,4900,4906]};window.__nowOffset+=1100;window.dispatchEvent(new Event('focus'))});await page.waitForFunction(()=>window.__pending.length===1);
    check(await page.getByText('0 of 9 activities submitted',{exact:true}).count()===1&&await page.getByRole('button',{name:'Refreshing…',exact:true}).isDisabled(),'In-flight return refresh retains old snapshot and disables duplicate manual refresh');
    await page.evaluate(()=>{window.dispatchEvent(new Event('focus'));document.dispatchEvent(new Event('visibilitychange'))});check(await page.evaluate(()=>window.__pending.length)===1,'An in-flight return refresh is not duplicated by focus or visibility');
    await page.evaluate(()=>{window.__mode.combine={};window.__setRoute('/home/inbox?event_id=1318')});await ready();await page.evaluate(()=>window.__release());await settle();
    check(await page.getByRole('heading',{name:/Adult Digital Combine/}).isVisible()&&await page.getByText('0 of 9 activities submitted',{exact:true}).count()===1&&await page.getByText('3 of 9 activities submitted',{exact:true}).count()===0,'Event switch rejects old-event progress from an in-flight return refresh');
    await reset({kind:'card',modes:{combine:{pending:true}}});await page.waitForFunction(()=>window.__pending.length===1);
    await page.evaluate(()=>{window.__mode.combine={};window.__setRoute('/home/inbox?event_id=1318')});await ready();await page.evaluate(()=>window.__release());await settle();
    check(await page.getByRole('heading',{name:/Adult Digital Combine/}).isVisible()&&await page.evaluate(()=>window.__requests[0].signal.aborted),'Event switch aborts prior fetch and ignores valid late junior data');
    await switchAccount(null);check(await page.getByRole('list',{name:'Combine activities'}).count()===0,'Signout removes all personal progress immediately');
    await reset({kind:'card',strict:true});await ready();check(await page.getByText('0 of 9 activities submitted',{exact:true}).count()===1,'StrictMode setup cleanup setup resolves with no permanent busy state');

    await reset({kind:'card'});await ready();
    for(const [name,transform] of [
      ['non-list public definitions',s=>{s.activities[0].required_fields='video';return s}],
      ['mismatched public definition count',s=>{s.activities[0].required_fields=[];return s}],
      ['null public definition entry',s=>{s.activities[0].required_fields[0]=null;return s}],
      ['non-text public type',s=>{s.activities[0].required_fields[0].type={private:'value'};return s}],
      ['blank public label',s=>{s.activities[0].required_fields[0].title=' ';return s}],
      ['oversized public label',s=>{s.activities[0].required_fields[0].title='x'.repeat(2001);return s}],
      ['wrong account',s=>({...s,clerk_id:'athlete-other'})],
      ['wrong event',s=>({...s,selected_event:{...s.selected_event,event_id:1318}})],
      ['null activity',s=>({...s,activities:[null,...s.activities.slice(1)]})],
      ['false selected event',s=>({...s,selected_event:false})],
      ['inconsistent counts',s=>({...s,counts:{...s.counts,submitted:9}})],
      ['unsafe continuation',s=>({...s,selected_event:{...s.selected_event,continuation_url:'javascript:alert(1)'}})],
      ['linked activity progress unavailable',s=>{s.activities[0].submission_state='unavailable';s.activities[0].evidence_state='unknown';return s}],
      ['fields present without a submission',s=>{s.activities[0].evidence_state='fields_present';s.activities[0].missing_fields=[];s.counts.fields_present=1;return s}],
      ['fields present with zero required fields',s=>{Object.assign(s.activities[0],{submission_state:'submitted',evidence_state:'fields_present',required_field_count:0,missing_fields:[]});s.counts.submitted=1;s.counts.fields_present=1;return s}],
      ['fields present with missing fields',s=>{Object.assign(s.activities[0],{submission_state:'submitted',evidence_state:'fields_present'});s.counts.submitted=1;s.counts.fields_present=1;return s}],
      ['unlinked missing field claims',s=>{s.athlete_id=null;s.state='link_required';s.counts.submitted=null;s.counts.fields_present=null;for(const a of s.activities)Object.assign(a,{submission_state:'unavailable',evidence_state:'unknown',missing_fields:[]});s.activities[0].missing_fields=['Unconfirmed field'];return s}],
      ['unlinked submission timestamp',s=>{s.athlete_id=null;s.state='link_required';s.counts.submitted=null;s.counts.fields_present=null;for(const a of s.activities)Object.assign(a,{submission_state:'unavailable',evidence_state:'unknown',missing_fields:[]});s.activities[0].submitted_at='2026-09-06T12:00:00Z';return s}],
    ]){
      const body=await page.evaluate(()=>window.__snapshot('athlete-a',1317));await refresh({body:transform(body)});
      check(await page.getByRole('alert').count()===1&&await page.getByText('0 of 9 activities submitted',{exact:true}).count()===1,'Rejects '+name+' while retaining last confirmed snapshot');
    }
    for(const legacy of ['absent','null','unknown']){
      const body=await page.evaluate(legacy=>{const s=window.__snapshot('athlete-a',1317);for(const a of s.activities){if(legacy==='absent')delete a.required_fields;else if(legacy==='null')a.required_fields=null;else a.required_fields=a.required_fields.map(f=>({...f,type:'__proto__'}))}return s},legacy);
      await refresh({body});
      const first=activity('Athlete Background');if(!await first.locator('details').evaluate(e=>e.open))await first.locator('summary').click();
      const fields=first.getByRole('group',{name:'What you’ll submit'});
      check(await page.getByRole('alert').count()===0&&(legacy==='unknown'?await fields.getByText('Format unconfirmed',{exact:true}).first().isVisible():await fields.getByText(/Field requirements could not be confirmed/).isVisible()),legacy+' metadata keeps continuation with explicit uncertainty instead of invented formats');
    }
    const unsafe=await page.evaluate(()=>{const s=window.__snapshot('athlete-a',1317);s.activities[0].description='<img src=x onerror="window.__unsafe=true"><script>window.__unsafe=true</script>';return s});
    await refresh({body:unsafe});if(!await page.locator('details').first().evaluate(e=>e.open))await page.locator('summary').first().click();check(await page.evaluate(()=>!window.__unsafe)&&await page.locator('ol img, ol script').count()===0,'Organizer instructions are escaped plain text, never raw HTML');

    await reset({kind:'redeem'});await page.waitForFunction(()=>window.__navigation.length>0);check(await page.evaluate(()=>window.__navigation[0])==='/home/inbox?event_id=1317','Verified claim retains event into inbox even when workspace bootstrap is not ready');
    await reset({kind:'home',query:'event_id=1318'});await page.waitForFunction(()=>window.__navigation.length>0);check(await page.evaluate(()=>window.__navigation[0])==='/home/inbox?event_id=1318'&&await page.evaluate(()=>window.__requests.length)===0,'Actual home entry preserves event and requires no profile bootstrap request');
    await reset({kind:'home',query:'event_id=999',modes:{combine:{claimEvent:1317}}});await page.waitForFunction(()=>window.__navigation.length>0);
    check(await page.evaluate(()=>window.__navigation[0])==='/home/inbox?event_id=999','Actual home entry preserves invalid event for explicit card recovery');
    await page.evaluate(()=>window.__mount('card'));await ready();check(await page.getByRole('combobox').inputValue()===''&&await page.getByRole('list',{name:'Combine activities'}).count()===0,'Home invalid event reaches chooser instead of silently falling back to saved claim');
    await reset({kind:'home',user:null});await page.getByRole('link',{name:'Sign in to your workspace'}).waitFor();check(await page.evaluate(()=>window.__navigation.length)===0,'Signed-out home does not route into a workspace');

    fs.mkdirSync(path.dirname(receiptPath),{recursive:true});
    for(const width of [360,390,430]){
      await page.setViewportSize({width,height:844});await reset();await ready();
      check(await noOverflow()&&await page.getByRole('button',{name:'Menu',exact:true}).isVisible()&&!await page.getByRole('heading',{name:'Combine help'}).isVisible(),'Phone '+width+' has full-width content and collapsed navigation/chat without horizontal scrolling');
      check(await page.locator('#workspace-main').getByRole('link',{name:'Continue in GMTM',exact:false}).evaluate(e=>{const r=e.getBoundingClientRect();return r.top>=0&&r.bottom<=innerHeight}),'Phone '+width+' primary task action is visible in the first viewport');
      await page.getByRole('button',{name:'Menu',exact:true}).click();check(await page.getByRole('link',{name:/My next move/}).isVisible()&&!await page.locator('#workspace-main').isVisible(),'Phone '+width+' menu is accessible and does not squeeze the task list');
      await page.keyboard.press('Escape');check(await page.getByRole('button',{name:'Menu',exact:true}).evaluate(e=>e===document.activeElement),'Phone '+width+' Escape closes menu and restores trigger focus');
      await page.getByRole('button',{name:'Ask SPARQ',exact:true}).click();await page.getByRole('heading',{name:'Combine help'}).waitFor();check(await page.locator('textarea').isVisible()&&await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),'Phone '+width+' help and input fit within the screen');
      await page.keyboard.press('Escape');await page.locator('#workspace-main').evaluate(e=>e.scrollTop=0);
      if(width===390){const screenshot=path.join(path.dirname(receiptPath),'combine-phone-390.png');await page.screenshot({path:screenshot});screenshots.push(screenshot);await page.locator('#workspace-main').getByRole('link',{name:'Continue in GMTM',exact:false}).scrollIntoViewIfNeeded();const task=path.join(path.dirname(receiptPath),'combine-phone-390-action.png');await page.screenshot({path:task});screenshots.push(task)}
    }
    await page.setViewportSize({width:1440,height:1000});await reset();await ready();await page.getByRole('heading',{name:'Combine help'}).waitFor();
    check(await page.getByRole('link',{name:/My next move/}).isVisible()&&await page.getByRole('heading',{name:'Combine help'}).isVisible()&&await noOverflow(),'Desktop retains sidebar and chat around a usable combine column');
    const desktop=path.join(path.dirname(receiptPath),'combine-desktop-1440.png');await page.screenshot({path:desktop});screenshots.push(desktop);
    check(errors.length===0,'No runtime errors in the actual-component synthetic journeys');
    fs.writeFileSync(receiptPath,JSON.stringify({status:'pass',checks,sourceHashes,screenshots,viewports:[{width:360,height:844},{width:390,height:844},{width:430,height:844},{width:1440,height:1000}],scope:'Current TSX + actual React 18 + generated repository Tailwind in Chromium; synthetic Clerk/Next routing/fetch, plain-text Markdown replacement in existing chat. Public task configuration plus invented athlete submissions. All network intercepted; no backend, live identity, real upload, production, full Next middleware or physical-device acceptance.'},null,2)+'\n');
    process.stdout.write(JSON.stringify({status:'pass',checks:checks.length,receipt:receiptPath,screenshots})+'\n');
  } finally { await browser.close() }
})().catch(error=>{process.stderr.write(String(error.stack||error)+'\n');process.exitCode=1});
