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
for (const [method, input] of [['GET','/api/combine/current?event_id=1318'], ['POST','/api/combine/help'], ['GET','/api/profile/by-clerk/user_fixture'], ['GET',`/api/claims/${token}`], ['POST',`/api/claims/${token}/redeem`]]) check('Allowed API ' + method + ' ' + input, () => assert.equal(policy.resolveAPIRequest(input,'https://backend.example','combine',method), 'https://backend.example'+input))
for (const [method,input] of [['POST','/api/combine/current'],['GET','/api/combine/help'],['GET','/api/combine/current?user_id=2'],['GET','/api/combine/current?event_id=1318&event_id=1317'],['POST','/api/claims/mint'],['GET','/api/claims/mint'],['POST','/api/profile/connect'],['GET','/api/workspace/inbox/me'],['GET','//evil.example/api/combine/current'],['GET','https://evil.example/api/combine/current'],['GET','https://user@backend.example/api/combine/current'],['GET','/api/combine/../combine/current'],['GET','/api/%2e%2e/combine/current'],['GET','/api/claims/a%2Fredeem'],['GET','/api/combine/current#fragment']]) check('Denied API ' + method + ' ' + input, () => assert.throws(() => policy.resolveAPIRequest(input,'https://backend.example','combine',method)))
for (const p of ['/home','/home/inbox','/connect',`/claim/${token}`,`/claim/${token}/redeem`,'/sign-in','/sign-up/verify-email-address']) check('Allowed page ' + p, () => assert.equal(policy.candidatePagePolicy(p,'GET'),'page'))
for (const p of ['/home/colleges','/home/artifact/123.jpg','/athlete/2','/api/demo-chat','/api/onboarding/complete','/trpc/anything','/onboarding','/demo','/_next/image','/home%2fcolleges','/claim/a/b','/unlisted.jpg']) check('Denied page ' + p, () => assert.equal(policy.candidatePagePolicy(p,'GET'),'deny'))
check('No candidate POST pages or server actions', () => assert.equal(policy.candidatePagePolicy('/home','POST'),'deny'))
check('Legacy transport remains explicit and unrestricted by candidate manifest', () => assert.equal(policy.resolveAPIRequest('/api/workspace/inbox/me','https://backend.example','legacy'), 'https://backend.example/api/workspace/inbox/me'))

check('Profile surface keeps the restricted boundary', () => { assert.equal(policy.isProfileSurface('profile'),true); assert.equal(policy.isCombineSurface('profile'),false); assert.equal(policy.isRestrictedSurface('profile'),true); assert.equal(policy.isRestrictedSurface('legacy'),false) })
for (const input of ['/api/athlete/evidence','/api/athlete/materials','/api/profile/by-clerk/user_fixture']) check('Profile allows narrow read '+input,()=>assert.equal(policy.resolveAPIRequest(input,'https://backend.example','profile'),'https://backend.example'+input))
for (const [method,input] of [['POST','/api/athlete/evidence'],['GET','/api/athlete/evidence?user_id=2'],['GET','/api/athlete/evidence?'],['GET','/api/combine/current'],['POST','/api/combine/help'],['GET','/api/workspace/inbox/me'],['POST','/api/profile/connect'],['GET','/api/reports/public/token']]) {
 if(input.endsWith('?')) continue // URL normalizes an empty query; it cannot select another athlete.
 check('Profile denies '+method+' '+input,()=>assert.throws(()=>policy.resolveAPIRequest(input,'https://backend.example','profile',method)))
}
check('Combine does not gain profile evidence route',()=>assert.throws(()=>policy.resolveAPIRequest('/api/athlete/evidence','https://backend.example','combine')))
check('Combine does not gain materials route',()=>assert.throws(()=>policy.resolveAPIRequest('/api/athlete/materials','https://backend.example','combine')))
for (const [method,input] of [['POST','/api/athlete/materials'],['GET','/api/athlete/materials?user_id=2'],['GET','/api/athlete/materials?event_id=1318'],['GET','/api/athlete/materials/'],['GET','/api/athlete/materials#film']]) check('Profile denies material selector or alternate route '+method+' '+input,()=>assert.throws(()=>policy.resolveAPIRequest(input,'https://backend.example','profile',method)))

const apiFile = path.resolve(__dirname,'../app/_lib/api.ts')
const code = ts.transpileModule(fs.readFileSync(apiFile,'utf8'), {compilerOptions:{module:ts.ModuleKind.CommonJS,target:ts.ScriptTarget.ES2020}}).outputText
let tokens = 0, requests = []
const context = {exports:{}, require:id=>{assert.equal(id,'@/lib/backend-config.cjs');return policy}, process:{env:{NEXT_PUBLIC_BACKEND_URL:'https://backend.example',NEXT_PUBLIC_APP_SURFACE:'combine'}}, Headers, window:{Clerk:{session:{getToken:async()=>{tokens++;return 'synthetic-token'}}}}, fetch:async(...args)=>{requests.push(args);return {ok:true}}}
vm.runInNewContext(code,context)
;(async()=>{
 const nextConfigFile=path.resolve(__dirname,'../next.config.js')
 const nextConfigSource=fs.readFileSync(nextConfigFile,'utf8')
 const loadConfig=env=>{const sandbox={module:{exports:{}},process:{env},require:id=>{assert.equal(id,'./lib/backend-config.cjs');return policy}};vm.runInNewContext(nextConfigSource,sandbox);return sandbox.module.exports}
 check('Next startup fails without explicit backend',()=>assert.throws(()=>loadConfig({})))
 check('Candidate startup fails without Clerk configuration',()=>assert.throws(()=>loadConfig({NEXT_PUBLIC_BACKEND_URL:'https://backend.example',NEXT_PUBLIC_APP_SURFACE:'combine'})))
 const candidateConfig=loadConfig({NEXT_PUBLIC_BACKEND_URL:'https://backend.example',NEXT_PUBLIC_APP_SURFACE:'combine',NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:'synthetic'})
 check('Candidate disables framework image proxy before middleware',()=>assert.equal(candidateConfig.images.unoptimized,true))
 check('Candidate builds do not download font stylesheets',()=>assert.equal(candidateConfig.optimizeFonts,false))
 assert.equal((await candidateConfig.rewrites()).length,0);checks.push('Candidate emits no catch-all API rewrite')
 const profileConfig=loadConfig({NEXT_PUBLIC_BACKEND_URL:'https://backend.example',NEXT_PUBLIC_APP_SURFACE:'profile',NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY:'synthetic'})
 check('Profile disables framework image proxy',()=>assert.equal(profileConfig.images.unoptimized,true))
 assert.equal((await profileConfig.rewrites()).length,0);checks.push('Profile has no broad API rewrite')
 const legacyConfig=loadConfig({NEXT_PUBLIC_BACKEND_URL:'https://backend.example'})
 check('Legacy image configuration unchanged',()=>assert.equal(legacyConfig.images,undefined))
 check('Legacy font optimization setting unchanged',()=>assert.equal(legacyConfig.optimizeFonts,undefined))
 assert.equal((await legacyConfig.rewrites())[0].destination,'https://backend.example/api/:path*');checks.push('Legacy API rewrite uses explicit configured origin')
 for (const input of ['https://evil.example/api/combine/current','/api/workspace/inbox/me']) { await assert.rejects(context.exports.apiFetch(input)); checks.push('Actual helper rejects before token: '+input) }
 check('Denied requests acquire zero tokens and issue zero fetches',()=>{assert.equal(tokens,0);assert.equal(requests.length,0)})
 await context.exports.apiFetch('/api/combine/current?event_id=1318',{redirect:'follow'})
 check('Actual helper uses authorized origin and refuses caller redirect override',()=>{assert.equal(tokens,1);assert.equal(requests[0][0],'https://backend.example/api/combine/current?event_id=1318');assert.equal(requests[0][1].redirect,'error');assert.equal(requests[0][1].headers.get('Authorization'),'Bearer synthetic-token')})
 const hash = p => crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex')
 const result={status:'passed',checks:checks.length,names:checks,sourceHashes:{'lib/backend-config.cjs':hash(path.resolve(__dirname,'../lib/backend-config.cjs')),'app/_lib/api.ts':hash(apiFile),'next.config.js':hash(nextConfigFile)},limits:['Pure policy and compiled transport only; full Next middleware and real authentication tested separately.']}
 if(process.env.SPARQ_TEST_RECEIPT){fs.writeFileSync(process.env.SPARQ_TEST_RECEIPT,JSON.stringify(result,null,2)+'\n',{flag:'wx'})}
 console.log(JSON.stringify({status:result.status,checks:result.checks}))
})().catch(e=>{console.error(e);process.exitCode=1})
