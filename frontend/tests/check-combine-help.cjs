// Isolated combine conversational-help checks against current components, React and Tailwind.
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
  'app/athlete/[id]/components/combineResults.ts', 'app/_lib/api.ts', 'lib/backend-config.cjs',
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
const token=async()=>window.__identity.user?'fixture-'+window.__identity.user.id:null;
window.__params={token:'fixture-claim'};window.__requests=[];window.__pending=[];window.__mode={};window.__external=[];window.__helpRequests=[];window.__helpPending=[];window.__helpStreams=[];window.__helpMode={};
window.__nowOffset=0;const realNow=Date.now;Date.now=()=>realNow()+window.__nowOffset;
window.__helpTimeouts=[];const realSetTimeout=window.setTimeout;window.setTimeout=(fn,ms,...args)=>{const id=realSetTimeout(fn,ms,...args);if(ms===55000)window.__helpTimeouts.push({fn,id});return id};
document.addEventListener('click',event=>{const a=event.target.closest('a');if(a&&a.href.startsWith('https://')){event.preventDefault();window.__external.push(a.href)}});
function snapshot(owner,eventId,mode={}){
 const choices=definitions.map(d=>({event_id:d.event.event_id,name:d.event.name,division:d.event.event_id===1317?'Junior':'Adult',continuation_url:'https://gmtm.com/virtuals/'+d.event.event_id}));
 const selected=eventId||mode.claimEvent||null;const d=definitions.find(d=>d.event.event_id===selected);const linked=!mode.unlinked;
 const activities=d?d.tasks.map(t=>{const required=t.questions.filter(q=>q.required);const complete=(mode.present||[]).includes(t.task_id);const submitted=complete||(mode.submitted||[]).includes(t.task_id);return{task_id:t.task_id,event_id:t.event_id,title:t.title,order:t.list_order,kind:t.list_order===0?'background':t.list_order===1?'highlight':'exercise',description:'Synthetic organizer instruction for '+t.title+'. Record the requested evidence in GMTM.',continuation_url:'https://gmtm.com/virtuals/'+selected,submission_state:!linked?'unavailable':submitted?'submitted':'not_submitted',evidence_state:!linked||(mode.unknown||[]).includes(t.task_id)?'unknown':complete?'fields_present':'missing_fields',missing_fields:!linked||complete?[]:required.map(q=>q.title),required_field_count:required.length,required_fields:required.map(q=>({type:q.type,title:q.title})),submitted_at:submitted?'2026-09-06T12:00:00Z':null}}):[];
 return{schema_version:1,clerk_id:owner,athlete_id:linked?(owner==='athlete-a'?4521:4522):null,state:!linked?'link_required':d?'ready':'choose_event',events:choices,selected_event:d?{...choices.find(e=>e.event_id===selected),deadline_display:'September 21, 2026',deadline_source_url:'https://usafootball.com/national-team/digital-combine',configured_end:d.event.end_date}:null,activities,counts:{activities:activities.length,submitted:linked&&d?activities.filter(a=>a.submission_state==='submitted').length:null,fields_present:linked&&d?activities.filter(a=>a.evidence_state==='fields_present').length:null},fetched_at:'2026-09-06T12:00:00Z',athlete_id_status:'unknown'};
}
window.__snapshot=snapshot;
window.fetch=async(input,init={})=>{
 let url=new URL(String(input),location.origin);if(url.origin!==location.origin)throw Error('Blocked external fetch');const __proxied=url.pathname.startsWith('/api/sparq/proxy/');const __auth=__proxied?(window.__identity.user?'Bearer fixture-'+window.__identity.user.id:null):new Headers(init.headers).get('Authorization');if(__proxied){const __o=url.pathname;url=new URL(__o.slice('/api/sparq/proxy'.length)+url.search,location.origin)}
 if(url.pathname==='/api/combine/help'){
  const request={body:JSON.parse(init.body),authorization:__auth,signal:init.signal};window.__helpRequests.push(request);
  const mode=window.__helpMode;
  const sse=events=>events.map(e=>'data: '+JSON.stringify(e)+'\\n\\n').join('');
  const reply=()=>{
   if(mode.reject)throw new TypeError('Synthetic network failure');
   if(mode.status)return new Response('{}',{status:mode.status});
   if(mode.streaming)return new Response(new ReadableStream({start(controller){controller.enqueue(new TextEncoder().encode(sse([{type:'tool',name:'get_current_combine'},{type:'text',text:'PRIVATE PARTIAL ANSWER'}])));window.__helpStreams.push(controller)}}),{headers:{'content-type':'text/event-stream'}});
   const frames=mode.events||[{type:'tool',name:'get_current_combine'},{type:'text',text:'Use the organizer instructions for this activity.'},{type:'done'}];
   return new Response(mode.raw||sse(frames),{headers:{'content-type':'text/event-stream'}});
  };
  if(mode.pending)return new Promise(resolve=>window.__helpPending.push({request,resolve,reply}));
  return reply();
 }
 const owner=window.__identity.user?.id;const kind=url.pathname==='/api/combine/current'?'combine':url.pathname.includes('/workspace/profile/')?'profile':url.pathname.includes('/workspace/inbox/')?'inbox':url.pathname.includes('/workspace/badges/')?'badges':url.pathname.endsWith('/redeem')?'redeem':null;
 if(!kind)throw Error('Unexpected API request '+url.pathname);
 const eventId=Number(url.searchParams.get('event_id'))||null;const mode=window.__mode[kind]||{};
 const body=mode.body!==undefined?mode.body:kind==='combine'?snapshot(owner,eventId,mode):kind==='profile'?{clerk_id:owner,combine_results:[],hudl_url:null}:kind==='inbox'?{artifacts:[]}:kind==='badges'?{}:{connected:true,clerk_id:owner,user_id:4521,workspace_ready:false,event_id:1317};
 const request={kind,eventId,owner,url:url.href,method:init.method||'GET',authorization:__auth,signal:init.signal};window.__requests.push(request);
 const reply=()=>{if(mode.reject)throw Error('Synthetic request failure');return new Response(JSON.stringify(body),{status:mode.status||200,headers:{'content-type':'application/json'}})};
 if(mode.pending)return new Promise(resolve=>window.__pending.push({request,resolve,reply}));
 if(mode.jsonPending)return{ok:true,status:200,json:()=>new Promise(resolve=>window.__pending.push({request,resolve,reply:()=>body}))};
 return reply();
};
window.__releaseHelp=()=>{const p=window.__helpPending.shift();p.resolve(p.reply())};window.__endHelp=()=>{for(const c of window.__helpStreams){c.enqueue(new TextEncoder().encode('data: '+JSON.stringify({type:'text',text:' LATE PRIVATE ANSWER'})+'\\n\\ndata: '+JSON.stringify({type:'done'})+'\\n\\n'));c.close()}window.__helpStreams=[]};
window.__release=()=>{const p=window.__pending.shift();if(!p)throw Error('No pending response');p.resolve(p.reply())};
const jsx=(type,props,key)=>React.createElement(type,{...props,...(key!==undefined?{key}:{})});
function load(id,from=''){
 if(id==='react')return React;
 if(id==='react/jsx-runtime')return{jsx,jsxs:jsx,Fragment:React.Fragment};
 if(id==='@/app/_lib/useSparqSession')return{useSparqSession:useUser,signOutOfSparq:async()=>{}};
 if(id==='@/components/SignOutButton')return{__esModule:true,default:()=>React.createElement('button',{'aria-label':'Sign out'},'Sign out')};
 if(id==='next/navigation')return{useRouter:()=>router,useParams:()=>window.__params,usePathname:()=>useRoute().pathname,useSearchParams:()=>new URLSearchParams(useRoute().query)};
 if(id==='next/link')return{__esModule:true,default:({children,...props})=>React.createElement('a',{...props,onClick:e=>{props.onClick?.(e);if(!e.defaultPrevented){e.preventDefault();router.push(props.href)}}},children)};
 if(id==='next/dynamic')return{__esModule:true,default:loader=>{let component=null,promise=null;return function Dynamic(props){const [C,setC]=React.useState(()=>component);React.useEffect(()=>{let active=true;(promise||=(loader())).then(m=>{component=m.default||m;if(active)setC(()=>component)});return()=>{active=false}},[]);return C?React.createElement(C,props):null}}};
 if(id==='react-markdown')return{__esModule:true,default:({children})=>React.createElement('div',null,children)};
 if(id.startsWith('@/'))id=id.slice(2);else if(id.startsWith('.')){const parts=(from.slice(0,from.lastIndexOf('/')+1)+id).split('/'),out=[];for(const part of parts){if(part==='..')out.pop();else if(part!=='.')out.push(part)}id=out.join('/')}
 if(id==='app/home/components/ProfileWorkspaceShell')return{__esModule:true,default:({children})=>children}; // profile-only shell; never rendered on combine
 if(cache[id])return cache[id].exports;const m={exports:{}};cache[id]=m;if(!modules[id])throw Error('Unknown module '+id);modules[id](x=>load(x,id),m,m.exports);return m.exports;
}
const root=ReactDOM.createRoot(document.getElementById('root'));
window.__mount=(kind='shell',strict=false)=>{const id=kind==='home'?'app/home/HomeClient':kind==='card'?'app/home/components/CurrentCombineCard':'app/home/layout';const C=load(id).default;const child=kind==='shell'?React.createElement(load('app/home/components/InboxFeed').default):null;const content=React.createElement(C,null,child);root.render(strict?React.createElement(React.StrictMode,null,content):content)};
`;

(async () => {
  const postcss=require(path.join(deps,'postcss')),tailwind=require(path.join(deps,'tailwindcss'));
  const config=require(path.join(deps,'tailwindcss/lib/lib/load-config.js')).loadConfig(path.join(frontend,'tailwind.config.ts'));
  const css=(await postcss([tailwind({...config,content:rawSources})]).process('@tailwind base;@tailwind components;@tailwind utilities;',{from:undefined})).css;
  sourceHashes['tailwind.config.ts']=crypto.createHash('sha256').update(fs.readFileSync(path.join(frontend,'tailwind.config.ts'))).digest('hex');
  const origin='http://127.0.0.1:4320';
  const assets={
    '/':'<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><link rel="stylesheet" href="/style.css"></head><body><div id="root"></div><script src="/react.js"></script><script src="/react-dom.js"></script><script src="/app.js"></script></body></html>',
    '/style.css':css,'/app.js':bundle,'/sparq-logo.jpg':fs.readFileSync(path.join(frontend,'public/sparq-logo.jpg')),
    '/react.js':fs.readFileSync(path.join(deps,'react/umd/react.development.js'),'utf8'),
    '/react-dom.js':fs.readFileSync(path.join(deps,'react-dom/umd/react-dom.development.js'),'utf8'),
  };
  const browser=await chromium.launch({headless:true}),checks=[],errors=[],screenshots=[];
  try {
    const page=await browser.newPage({viewport:{width:390,height:844}});
    page.on('pageerror',e=>errors.push(String(e)));
    await page.route('**/*',route=>{const u=new URL(route.request().url()),key=u.pathname.startsWith('/home')?'/':u.pathname;if(u.origin!==origin||!(key in assets))return route.abort();return route.fulfill({status:200,contentType:key.endsWith('.js')?'application/javascript':key.endsWith('.css')?'text/css':key.endsWith('.jpg')?'image/jpeg':'text/html',body:assets[key]})});
    const check=(condition,name)=>{assert(condition,name);checks.push(name);if(checks.length%10===0)process.stdout.write('Passed '+checks.length+' help checks\n')};
    const settle=()=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
    const reset=async({query='event_id=1317',modes={},helpMode={},strict=false}={})=>{await page.goto(origin);await page.evaluate(({query,modes,helpMode,strict})=>{localStorage.setItem('sparq_conv_athlete-a','987654');window.__setRoute('/home/inbox'+(query?'?'+query:''));window.__mode=modes;window.__helpMode=helpMode;window.__mount('shell',strict)}, {query,modes,helpMode,strict})};
    const ready=()=>page.getByRole('button',{name:'Refresh progress',exact:true}).waitFor();
    const panel=()=>page.locator('#workspace-help');
    const main=()=>page.locator('#workspace-main');
    const task=title=>main().getByRole('list',{name:'Combine activities'}).locator(':scope > li').filter({has:page.getByRole('heading',{name:new RegExp(title)})});
    const openTask=async(title='Stick Overhead Squat')=>{await task(title).getByRole('button',{name:'Help with this activity'}).click();await panel().getByRole('heading',{name:'Combine help',exact:true}).waitFor();await panel().getByRole('textbox',{name:'Your combine question'}).waitFor();await settle()};
    const send=async(text='How do I record it?')=>{await panel().getByRole('textbox',{name:'Your combine question'}).fill(text);await panel().getByRole('button',{name:'Send',exact:true}).click()};
    const answer=()=>panel().getByRole('log').getByText('Use the organizer instructions for this activity.',{exact:false}).last().waitFor();
    await reset();await ready();
    check(await page.evaluate(()=>window.__helpRequests.length)===0,'Mounting the combine card and help panel makes no model request');
    await openTask();
    check(await panel().locator('header').getByText('Stick Overhead Squat',{exact:true}).count()===1&&!await main().isVisible(),'Activity action opens mobile help with the selected activity');
    check(await panel().getByRole('heading',{name:'Combine help'}).evaluate(e=>e===document.activeElement),'Activity help moves keyboard focus to the panel heading');
    check(await panel().getByRole('group',{name:'What you’ll submit'}).getByText('Video',{exact:true}).isVisible()&&await page.evaluate(()=>window.__helpRequests.length)===0,'Public video requirement is visible before expanding instructions or asking a model');
    check(await panel().getByText('No saved attempt is visible for this activity.',{exact:true}).isVisible(),'No submission is not misrepresented as an empty saved attempt');
    await panel().locator('summary').click();
    check(await panel().getByText(/Synthetic organizer instruction for Stick Overhead Squat/).isVisible()&&await panel().getByRole('link',{name:'Continue in GMTM'}).getAttribute('href')==='https://gmtm.com/virtuals/1317','Organizer instructions and verified GMTM continuation work before any model call');
    await panel().getByRole('button',{name:'Help me record this activity',exact:true}).click();
    check(await page.evaluate(()=>window.__helpRequests.length)===0&&await panel().getByRole('textbox').inputValue()==='Help me record this activity','Starter only prefills a question; explicit Send is required');
    await panel().getByRole('button',{name:'Send',exact:true}).click();await answer();
    check(await page.evaluate(()=>{const r=window.__helpRequests[0];return r.authorization==='Bearer fixture-athlete-a'&&r.body.event_id===1317&&r.body.task_id===4906&&r.body.message==='Help me record this activity'&&Object.keys(r.body).sort().join(',')==='event_id,history,message,task_id'&&r.body.history.length===0}),'Explicit Send supplies only current event/task IDs, text and bounded history with authenticated request');
    check(await page.evaluate(()=>window.__requests.every(r=>!r.url.includes('/agent/stream')&&!r.url.includes('/agent/fork'))),'Combine help never uses generic conversation or fork endpoints');
    await send('What is still missing?');await page.waitForFunction(()=>window.__helpRequests.length===2);await panel().getByRole('button',{name:'Send',exact:true}).waitFor();
    check(await page.evaluate(()=>{const h=window.__helpRequests[1].body.history;return h.length===2&&h[0].role==='user'&&h[1].role==='assistant'&&h[1].content==='Use the organizer instructions for this activity.'}),'Successful exchange becomes same-context in-memory history');
    await page.keyboard.press('Escape');await page.getByRole('button',{name:'Refresh progress',exact:true}).click();await ready();await openTask();
    check(await panel().getByRole('log').getByText('Use the organizer instructions for this activity.',{exact:false}).count()===2,'Same-event and task progress refresh preserves conversation');
    await page.keyboard.press('Escape');await page.getByRole('button',{name:'Ask SPARQ',exact:true}).click();await send('What should I do next?');await answer();
    check(await page.evaluate(()=>window.__helpRequests.at(-1).body.task_id===null&&window.__helpRequests.at(-1).body.history.length===0),'Main Ask SPARQ opens event-level help without task history');

    for(const [name,settings] of [['loading',{combine:{pending:true}}],['source failure',{combine:{status:503}}],['choose event',{}]]){
      await reset({query:'',modes:settings});if(name!=='loading')await ready();await page.getByRole('button',{name:'Ask SPARQ',exact:true}).click();
      await panel().getByText(/Choose a combine and load its activities/).waitFor();
      check(await panel().getByText(/Choose a combine and load its activities/).isVisible()&&await panel().getByRole('textbox').count()===0&&await page.evaluate(()=>window.__helpRequests.length)===0,`${name} retains explicit combine helper state without legacy chat or model calls`);
    }
    for(const status of [401,404,409,422,429,503]){
      await reset({helpMode:{status}});await ready();await openTask();await send();await panel().getByRole('alert').waitFor();
      check(await panel().getByRole('link',{name:'Continue in GMTM'}).isVisible()&&await panel().locator('summary').isVisible()&&await panel().getByRole('textbox').inputValue()==='How do I record it?',`HTTP ${status} shows recovery and preserves instructions, continuation and retry text`);
    }
    for(const [name,mode] of [
      ['provider error',{events:[{type:'text',text:'Partial advice'},{type:'error',error:'PRIVATE SERVER DETAIL'}]}],
      ['missing completion',{events:[{type:'text',text:'Partial advice'}]}],
      ['malformed stream',{raw:'data: broken\n\n'}],
      ['empty completed answer',{events:[{type:'done'}]}],
      ['network failure',{reject:true}],
    ]){
      await reset({helpMode:mode});await ready();await openTask();await send();await panel().getByRole('alert').waitFor();
      check(await panel().getByText('PRIVATE SERVER DETAIL',{exact:true}).count()===0&&await panel().getByRole('link',{name:'Continue in GMTM'}).isVisible(),`${name} cannot become an empty success or expose raw provider error`);
      await page.evaluate(()=>window.__helpMode={});await panel().getByRole('button',{name:'Send',exact:true}).click();await answer();
      check(await page.evaluate(()=>window.__helpRequests.at(-1).body.history.length)===0,`${name} partial or failed exchange is excluded from retry history`);
    }

    await reset({modes:{combine:{unlinked:true}},helpMode:{status:503}});await ready();await openTask();
    check(await panel().getByText(/You can still ask for help with the public checklist here/).isVisible()&&await panel().getByRole('group',{name:'What you’ll submit'}).getByText('Video',{exact:true}).isVisible(),'Unlinked public help explicitly offers assistance and actual requirements without personal answers');
    await send();await panel().getByRole('alert').waitFor();
    check(await panel().getByText('Saved progress for this activity could not be checked.',{exact:true}).isVisible()&&await panel().getByRole('group',{name:'What you’ll submit'}).isVisible()&&await panel().getByText('No saved attempt is visible for this activity.',{exact:true}).count()===0,'Provider failure keeps unlinked progress unknown and public requirements visible');
    await reset({modes:{combine:{submitted:[4906],unknown:[4906]}},helpMode:{status:503}});await ready();await openTask();await send();await panel().getByRole('alert').waitFor();
    check(await panel().getByText('A saved attempt is visible. Its required information could not be checked.',{exact:true}).isVisible(),'Provider failure preserves known saved attempt separately from unknown field presence');
    await reset({helpMode:{pending:true}});await ready();await openTask();await send('PRIVATE TASK QUESTION');await page.waitForFunction(()=>window.__helpPending.length===1);
    await page.keyboard.press('Escape');await openTask('Max. Push-Ups');await page.evaluate(()=>window.__releaseHelp());await settle();
    check(await page.evaluate(()=>window.__helpRequests[0].signal.aborted)&&await panel().getByText('PRIVATE TASK QUESTION',{exact:false}).count()===0&&await panel().getByText('Use the organizer instructions for this activity.',{exact:false}).count()===0,'Switching tasks aborts and ignores a late valid response from the old task');
    await page.evaluate(()=>window.__helpMode={});await send();await answer();check(await page.evaluate(()=>window.__helpRequests.at(-1).body.task_id===4901&&window.__helpRequests.at(-1).body.history.length===0),'New task starts with the correct ID and no previous-task history');

    for(const reason of ['cancel','timeout']){
      await reset({helpMode:{pending:true}});await ready();await openTask();await send('Question to recover');await page.waitForFunction(()=>window.__helpPending.length===1);
      if(reason==='cancel')await panel().getByRole('button',{name:'Cancel answer',exact:true}).click();else await page.evaluate(()=>window.__helpTimeouts.at(-1).fn());
      await settle();
      await panel().getByRole('alert').waitFor()
      check(await panel().getByRole('textbox').inputValue()==='Question to recover'&&await panel().getByRole('button',{name:'Send',exact:true}).isEnabled()&&await page.evaluate(()=>window.__helpRequests.length===1&&window.__helpRequests[0].signal.aborted),`${reason} stops a hung request, restores the question and clears busy state`);
      await page.evaluate(()=>window.__releaseHelp());await settle();check(await panel().getByText('Use the organizer instructions for this activity.',{exact:false}).count()===0,`${reason} ignores a late otherwise-valid response`);
    }

    for(const boundary of ['account','event']){
      await reset({helpMode:{streaming:true}});await ready();await openTask();await send('PRIVATE '+boundary.toUpperCase()+' QUESTION');await panel().getByText('PRIVATE PARTIAL ANSWER',{exact:true}).waitFor();
      await page.evaluate(boundary=>{window.__helpMode={};if(boundary==='account')window.__setIdentity({isLoaded:true,user:{id:'athlete-b'}});else window.__setRoute('/home/inbox?event_id=1318')},boundary);
      await ready();await page.evaluate(()=>window.__endHelp());await settle();await openTask();
      check(await page.evaluate(()=>window.__helpRequests[0].signal.aborted)&&await panel().getByText(/PRIVATE/).count()===0,`${boundary} switch clears help state and ignores late stream chunks`);
      await send();await answer();check(await page.evaluate(boundary=>{const r=window.__helpRequests.at(-1);return r.body.history.length===0&&r.body.event_id===(boundary==='event'?1318:1317)&&r.authorization===(boundary==='account'?'Bearer fixture-athlete-b':'Bearer fixture-athlete-a')},boundary),`${boundary} switch uses the new context identity without inherited memory`);
    }
    await page.evaluate(()=>window.__setIdentity({isLoaded:true,user:null}));await settle();await page.getByRole('button',{name:'Ask SPARQ',exact:true}).click();
    await panel().getByText('Sign in to ask about your combine.').waitFor();
    check(await panel().getByText('Sign in to ask about your combine.').isVisible()&&await panel().getByRole('log').count()===0,'Signout clears all combine help conversation state');

    await reset({strict:true});await ready();await openTask();await panel().getByRole('button',{name:'What is still missing?',exact:true}).click();
    check(await page.evaluate(()=>window.__helpRequests.length)===0,'StrictMode and task starter do not cause an automatic model call');await panel().getByRole('button',{name:'Send',exact:true}).click();await answer();
    check(await page.evaluate(()=>window.__helpRequests.length)===1,'One explicit Send starts one help request in StrictMode');
    await reset();await ready();await openTask();
    for(let index=0;index<8;index++){
      await page.evaluate(()=>window.__helpMode={events:[{type:'text',text:'A'.repeat(2600)},{type:'done'}]});await send(String(index)+'Q'.repeat(1998));await panel().getByRole('button',{name:'Send',exact:true}).waitFor();
    }
    check(await page.evaluate(()=>{const h=window.__helpRequests.at(-1).body.history;return h.length<=12&&h.length%2===0&&h.every((m,i)=>m.role===(i%2?'assistant':'user')&&m.content.length<=2000)&&h.reduce((n,m)=>n+m.content.length,0)<=12000}),'Outbound history contains bounded complete alternating pairs within per-message and total limits');
    check(await page.evaluate(()=>localStorage.getItem('sparq_conv_athlete-a'))==='987654','Combine help neither reads nor overwrites generic conversation persistence');

    await reset();await ready();await page.evaluate(()=>window.__setRoute('/home/profile'));await settle();await page.getByRole('button',{name:'Ask SPARQ',exact:true}).click();
    await panel().getByRole('heading',{name:'Recruiting AI ✨'}).waitFor();
    check(await panel().getByRole('heading',{name:'Recruiting AI ✨'}).isVisible(),'Other workspace pages retain their separate recruiting panel');

    fs.mkdirSync(path.dirname(receiptPath),{recursive:true});
    for(const width of [360,390,430]){
      await page.setViewportSize({width,height:844});await reset({modes:{combine:{unlinked:true}}});await ready();await openTask();await panel().locator('summary').click();
      check(await panel().getByRole('group',{name:'What you’ll submit'}).getByText('Video',{exact:true}).isVisible(),`Phone ${width} exposes public video requirement before any model response`);
      check(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth)&&await panel().getByRole('textbox').isVisible()&&await panel().getByRole('button',{name:'Send',exact:true}).evaluate(e=>e.getBoundingClientRect().bottom<=innerHeight),`Phone ${width} activity help, grounded instructions and composer fit without horizontal overflow`);
      if(width===390){const file=path.join(path.dirname(receiptPath),'combine-help-phone-390.png');await page.screenshot({path:file});screenshots.push(file)}
    }
    await page.setViewportSize({width:1440,height:1000});await reset({query:'event_id=1318'});await ready();await openTask('20-Yard Dash');
    const dash=panel().getByRole('group',{name:'What you’ll submit'});
    check(await dash.getByText('40 Yard Dash Time',{exact:true}).isVisible()&&await dash.getByText('20 Yard Dash',{exact:true}).isVisible()&&await dash.getByText('Video',{exact:true}).isVisible()&&await dash.getByText(/known mismatch/).isVisible(),'Desktop help shows exact adult time/video labels and caption explanation without a model call');
    check(await main().isVisible()&&await panel().isVisible()&&await panel().getByRole('textbox').isVisible(),'Desktop keeps the activity card and contextual help alongside each other');
    const desktop=path.join(path.dirname(receiptPath),'combine-help-desktop-1440.png');await page.screenshot({path:desktop});screenshots.push(desktop);
    check(errors.length===0,'No component runtime errors during isolated combine-help journeys');
    fs.writeFileSync(receiptPath,JSON.stringify({status:'pass',checks,sourceHashes,screenshots,viewports:[360,390,430,1440],scope:'Actual current components + React18 + generated repository Tailwind in Chromium; synthetic SPARQ session/Next routing/current-combine/SSE, public configuration with invented athlete data, all external network blocked. No model, backend, database or real account. Does not establish provider quality, live auth or physical-device acceptance.'},null,2)+'\n');
    process.stdout.write(JSON.stringify({status:'pass',checks:checks.length,receipt:receiptPath,screenshots})+'\n');
  }finally{await browser.close()}
})().catch(e=>{process.stderr.write(String(e.stack||e)+'\n');process.exitCode=1});
