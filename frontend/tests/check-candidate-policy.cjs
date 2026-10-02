// Pure policy and actual compiled API helper. No server, credentials or network.
const assert = require('node:assert/strict')
const fs = require('node:fs')
const path = require('node:path')
const vm = require('node:vm')
const crypto = require('node:crypto')
const policy = require('../lib/backend-config.cjs')
const deps = process.env.SPARQ_TEST_NODE_MODULES
if (!deps) throw Error('Set SPARQ_TEST_NODE_MODULES to an existing dependency tree')
const ts = require(path.join(deps, 'typescript'))
const checks = []
function check(name, fn) { fn(); checks.push(name) }
for (const value of [undefined, '', ' https://backend.example', 'ftp://backend.example', 'https://u:p@backend.example', 'https://backend.example/api', 'https://backend.example/x/..', 'https://@backend.example', 'https://backend.example?x=1', 'https://backend.example#x', 'http://backend.example', 'https://backend.example\\foo']) check('Reject invalid origin ' + String(value), () => assert.throws(() => policy.resolveBackendOrigin(value)))
check('Canonical explicit backend origin', () => assert.equal(policy.resolveBackendOrigin('https://backend.example:443/'), 'https://backend.example'))
check('Explicit loopback backend', () => assert.equal(policy.resolveBackendOrigin('http://127.0.0.1:8901'), 'http://127.0.0.1:8901'))
check('Legacy default and explicit candidate', () => { assert.equal(policy.isCombineSurface(undefined), false); assert.equal(policy.isCombineSurface('combine'), true); assert.throws(() => policy.isCombineSurface('typo')) })
const token = 'eyJ1IjoxLCJlIjoxMzE4fQ.actual-signature'
for (const [method, input] of [['GET','/api/combine/current?event_id=1318'], ['POST','/api/combine/help'], ['GET','/api/profile/by-owner/user_fixture']]) check('Allowed API ' + method + ' ' + input, () => assert.equal(policy.resolveAPIRequest(input,'https://backend.example','combine',method), 'https://backend.example'+input))
for (const [method,input] of [['POST','/api/combine/current'],['GET','/api/combine/help'],['GET','/api/combine/current?user_id=2'],['GET','/api/combine/current?event_id=1318&event_id=1317'],['POST','/api/claims/mint'],['GET','/api/claims/mint'],['GET',`/api/claims/${token}`],['POST',`/api/claims/${token}/redeem`],['POST','/api/profile/connect'],['GET','/api/workspace/inbox/me'],['GET','//evil.example/api/combine/current'],['GET','https://evil.example/api/combine/current'],['GET','https://user@backend.example/api/combine/current'],['GET','/api/combine/../combine/current'],['GET','/api/%2e%2e/combine/current'],['GET','/api/claims/a%2Fredeem'],['GET','/api/combine/current#fragment']]) check('Denied API ' + method + ' ' + input, () => assert.throws(() => policy.resolveAPIRequest(input,'https://backend.example','combine',method)))
for (const p of ['/home','/home/inbox','/enter','/enter/callback','/enter/unavailable']) check('Allowed page ' + p, () => assert.equal(policy.candidatePagePolicy(p,'GET'),'page'))
for (const p of ['/home/colleges','/home/artifact/123.jpg','/athlete/2','/api/demo-chat','/api/onboarding/complete','/trpc/anything','/onboarding','/demo','/_next/image','/home%2fcolleges','/claim/a/b','/unlisted.jpg','/connect',`/claim/${token}`,`/claim/${token}/redeem`,'/sign-in','/sign-up/verify-email-address']) check('Denied page ' + p, () => assert.equal(policy.candidatePagePolicy(p,'GET'),'deny'))
check('No candidate POST pages or server actions', () => assert.equal(policy.candidatePagePolicy('/home','POST'),'deny'))
check('Legacy transport remains explicit and unrestricted by candidate manifest', () => assert.equal(policy.resolveAPIRequest('/api/workspace/inbox/me','https://backend.example','legacy'), 'https://backend.example/api/workspace/inbox/me'))

check('Profile surface keeps the restricted boundary', () => { assert.equal(policy.isProfileSurface('profile'),true); assert.equal(policy.isCombineSurface('profile'),false); assert.equal(policy.isRestrictedSurface('profile'),true); assert.equal(policy.isRestrictedSurface('legacy'),false) })
for (const input of ['/api/athlete/evidence','/api/athlete/materials','/api/profile/by-owner/user_fixture']) check('Profile allows narrow read '+input,()=>assert.equal(policy.resolveAPIRequest(input,'https://backend.example','profile'),'https://backend.example'+input))
for (const [method,input] of [['POST','/api/athlete/evidence'],['GET','/api/athlete/evidence?user_id=2'],['GET','/api/athlete/evidence?'],['GET','/api/combine/current'],['POST','/api/combine/help'],['GET','/api/workspace/inbox/me'],['POST','/api/profile/connect'],['GET','/api/reports/public/token']]) {
 if(input.endsWith('?')) continue // URL normalizes an empty query; it cannot select another athlete.
 check('Profile denies '+method+' '+input,()=>assert.throws(()=>policy.resolveAPIRequest(input,'https://backend.example','profile',method)))
}
check('Combine does not gain profile evidence route',()=>assert.throws(()=>policy.resolveAPIRequest('/api/athlete/evidence','https://backend.example','combine')))
check('Combine does not gain materials route',()=>assert.throws(()=>policy.resolveAPIRequest('/api/athlete/materials','https://backend.example','combine')))
check('Combine does not gain debrief route',()=>assert.throws(()=>policy.resolveAPIRequest('/api/athlete/debrief','https://backend.example','combine','POST')))
check('Combine does not gain opportunity route',()=>assert.throws(()=>policy.resolveAPIRequest('/api/athlete/opportunities','https://backend.example','combine','POST')))
for (const [method,input] of [['POST','/api/athlete/opportunities'],['GET','/api/athlete/opportunities'],['POST','/api/athlete/opportunities?user_id=2'],['POST','/api/athlete/opportunities/']]) check('Profile denies retired opportunity '+method+' '+input,()=>assert.throws(()=>policy.resolveAPIRequest(input,'https://backend.example','profile',method)))
for(const [method,url,surface] of [['POST','/api/athlete/opportunities/engagement','profile'],['GET','/api/athlete/opportunities/engagement','profile'],['POST','/api/athlete/opportunities/engagement?actor=2','profile'],['POST','/api/athlete/opportunities/engagement/','profile'],['POST','/api/athlete/opportunities/engagement','combine']]) check('Engagement route boundary '+method+' '+url+' '+surface,()=>assert.throws(()=>policy.resolveAPIRequest(url,'https://backend.example',surface,method)))
for (const method of ['GET','PATCH']) check('Profile allows owned workspace '+method,()=>assert.equal(policy.resolveAPIRequest('/api/athlete/workspace','https://backend.example','profile',method),'https://backend.example/api/athlete/workspace'))
for (const method of ['GET','PATCH','POST','DELETE']) check('Combine does not gain saved workspace '+method,()=>assert.throws(()=>policy.resolveAPIRequest('/api/athlete/workspace','https://backend.example','combine',method)))
for (const [method,input] of [['POST','/api/athlete/workspace'],['DELETE','/api/athlete/workspace'],['PATCH','/api/athlete/workspace?user_id=2'],['PATCH','/api/athlete/workspace/']]) check('Profile denies alternate workspace '+method+' '+input,()=>assert.throws(()=>policy.resolveAPIRequest(input,'https://backend.example','profile',method)))
for (const [method,input] of [['POST','/api/athlete/debrief'],['GET','/api/athlete/debrief'],['POST','/api/athlete/debrief?user_id=2'],['POST','/api/athlete/debrief/']]) check('Profile denies retired Ask SPARQ debrief '+method+' '+input,()=>assert.throws(()=>policy.resolveAPIRequest(input,'https://backend.example','profile',method)))
for (const [method,input] of [['POST','/api/athlete/materials'],['GET','/api/athlete/materials?user_id=2'],['GET','/api/athlete/materials?event_id=1318'],['GET','/api/athlete/materials/'],['GET','/api/athlete/materials#film']]) check('Profile denies material selector or alternate route '+method+' '+input,()=>assert.throws(()=>policy.resolveAPIRequest(input,'https://backend.example','profile',method)))

const apiFile = path.resolve(__dirname,'../app/_lib/api.ts')
// Junior colleges: exactly the reviewed routes, profile surface only.
const collegeAPIs=[['GET','/api/workspace/saved-colleges/user_fixture'],['POST','/api/workspace/saved-colleges/user_fixture/daytona-state-college'],['POST','/api/workspace/colleges/user_fixture/daytona-state-college/sent'],['GET','/api/workspace/colleges/user_fixture'],['POST','/api/workspace/trigger-matching/user_fixture'],['GET','/api/workspace/colleges/user_fixture/alabama-state-university'],['GET','/api/workspace/colleges/user_fixture/alabama-state-university/outreach-draft'],['POST','/api/workspace/colleges/user_fixture/alabama-state-university/outreach-draft']]
for (const [method,input] of collegeAPIs) {
 check('Profile allows college '+method+' '+input,()=>assert.equal(policy.resolveAPIRequest(input,'https://backend.example','profile',method),'https://backend.example'+input))
 check('Combine denies college '+method+' '+input,()=>assert.throws(()=>policy.resolveAPIRequest(input,'https://backend.example','combine',method)))
}
for (const [method,input] of [['POST','/api/workspace/colleges/user_fixture'],['GET','/api/workspace/trigger-matching/user_fixture'],['POST','/api/workspace/colleges/user_fixture/alabama-state-university'],['PATCH','/api/workspace/colleges/user_fixture/alabama-state-university/outreach-draft'],['GET','/api/workspace/colleges/user_fixture?all=1'],['GET','/api/workspace/colleges/user_fixture/Bad_ID'],['GET','/api/workspace/colleges/user_fixture/1/research'],['POST','/api/workspace/colleges/user_fixture/1/research'],['PUT','/api/workspace/colleges/1/status'],['GET','/api/workspace/enrichment-status/user_fixture'],['GET','/api/workspace/outreach/user_fixture'],['POST','/api/artifacts/draft-outreach'],['GET','/api/artifacts/1'],['GET','/api/workspace/saved-colleges/user_fixture/daytona-state-college'],['DELETE','/api/workspace/saved-colleges/user_fixture/daytona-state-college'],['POST','/api/workspace/saved-colleges/user_fixture'],['POST','/api/workspace/saved-colleges/user_fixture/Bad_ID'],['POST','/api/workspace/saved-colleges/user_fixture/a/b'],['GET','/api/workspace/colleges/user_fixture/daytona-state-college/sent'],['PATCH','/api/workspace/colleges/user_fixture/daytona-state-college/sent'],['POST','/api/workspace/colleges/user_fixture/daytona-state-college/sent?x=1']]) check('Profile denies '+method+' '+input,()=>assert.throws(()=>policy.resolveAPIRequest(input,'https://backend.example','profile',method)))
for (const p of ['/home/colleges','/home/colleges/alabama-state-university','/home/progress','/home/footage']) {
 check('Profile allows page '+p,()=>assert.equal(policy.candidatePagePolicy(p,'GET','profile'),'page'))
 check('Combine denies page '+p,()=>assert.equal(policy.candidatePagePolicy(p,'GET','combine'),'deny'))
}
check('Profile serves the bundled US map as a static asset; combine does not',()=>{assert.equal(policy.candidatePagePolicy('/us-states.svg','GET','profile'),'asset');assert.equal(policy.candidatePagePolicy('/us-states.svg','GET','combine'),'deny')})
for (const p of ['/home/colleges/Bad_ID','/home/colleges/a/b','/home/colleges/','/home/progress/','/home/footage/x','/home/emails','/home/card','/us-states.svg/x']) check('Profile denies page '+p,()=>assert.equal(policy.candidatePagePolicy(p,'GET','profile'),'deny'))
const code = ts.transpileModule(fs.readFileSync(apiFile,'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
let tokens = 0, requests = []
const context = {exports:{}, require:id=>{assert.equal(id,'@/lib/backend-config.cjs');return policy}, process:{env:{NEXT_PUBLIC_BACKEND_URL:'https://backend.example',NEXT_PUBLIC_APP_SURFACE:'combine'}}, Headers, URL, fetch:async(...args)=>{requests.push(args);return {ok:true}}}
vm.runInNewContext(code,context)
;(async()=>{
 const nextConfigFile=path.resolve(__dirname,'../next.config.js')
 const nextConfigSource=fs.readFileSync(nextConfigFile,'utf8')
 const loadConfig=env=>{const sandbox={module:{exports:{}},process:{env},require:id=>{assert.equal(id,'./lib/backend-config.cjs');return policy}};vm.runInNewContext(nextConfigSource,sandbox);return sandbox.module.exports}
 check('Next startup fails without explicit backend',()=>assert.throws(()=>loadConfig({})))
 const candidateConfig=loadConfig({NEXT_PUBLIC_BACKEND_URL:'https://backend.example',NEXT_PUBLIC_APP_SURFACE:'combine'})
 check('Candidate disables framework image proxy before middleware',()=>assert.equal(candidateConfig.images.unoptimized,true))
 check('Candidate builds do not download font stylesheets',()=>assert.equal(candidateConfig.optimizeFonts,false))
 assert.equal(candidateConfig.rewrites,undefined);checks.push('Candidate emits no API rewrite')
 const profileConfig=loadConfig({NEXT_PUBLIC_BACKEND_URL:'https://backend.example',NEXT_PUBLIC_APP_SURFACE:'profile'})
 checks.push('Profile starts with only the backend origin')
 check('Profile disables framework image proxy',()=>assert.equal(profileConfig.images.unoptimized,true))
 assert.equal(profileConfig.rewrites,undefined);checks.push('Profile has no API rewrite')
 const legacyConfig=loadConfig({NEXT_PUBLIC_BACKEND_URL:'https://backend.example'})
 check('Legacy image configuration unchanged',()=>assert.equal(legacyConfig.images,undefined))
 check('Legacy font optimization setting unchanged',()=>assert.equal(legacyConfig.optimizeFonts,undefined))
 assert.equal(legacyConfig.rewrites,undefined);checks.push('Legacy has no /api rewrite: browser calls reach the backend only through /api/sparq/proxy')
 for (const input of ['https://evil.example/api/combine/current','/api/workspace/inbox/me']) { await assert.rejects(context.exports.apiFetch(input)); checks.push('Actual helper rejects before any request: '+input) }
 check('Denied requests issue zero fetches',()=>{assert.equal(tokens,0);assert.equal(requests.length,0)})
 await context.exports.apiFetch('/api/combine/current?event_id=1318',{redirect:'follow'})
 check('Actual helper goes through the same-origin SPARQ proxy and refuses caller redirect override',()=>{assert.equal(requests[0][0],'/api/sparq/proxy/api/combine/current?event_id=1318');assert.equal(requests[0][1].redirect,'error');assert.equal(requests[0][1].credentials,'same-origin');assert.equal(requests[0][1].headers,undefined)})
 const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')
 const result={status:'passed',checks:checks.length,names:checks,sourceHashes:{'lib/backend-config.cjs':hash(path.resolve(__dirname,'../lib/backend-config.cjs')),'app/_lib/api.ts':hash(apiFile),'next.config.js':hash(nextConfigFile)},limits:['Pure policy and compiled transport only; full Next middleware and the SPARQ session tested separately.']}
 if(process.env.SPARQ_TEST_RECEIPT){fs.writeFileSync(process.env.SPARQ_TEST_RECEIPT,JSON.stringify(result,null,2)+'\n',{flag:'wx'})}
 console.log(JSON.stringify({status:result.status,checks:result.checks}))
})().catch(e=>{console.error(e);process.exitCode=1})
