// Pure configuration and route policy shared by Next, Edge and browser code.
// No environment reads here: callers use explicit (statically inlined) settings.
function readSurface(value) {
  if (value === undefined || value === '' || value === 'legacy') return 'legacy'
  if (value === 'combine' || value === 'profile') return value
  throw new Error('NEXT_PUBLIC_APP_SURFACE must be combine, profile or legacy')
}
function isCombineSurface(value) { return readSurface(value) === 'combine' }
function isProfileSurface(value) { return readSurface(value) === 'profile' }
function isRestrictedSurface(value) { return readSurface(value) !== 'legacy' }
function resolveBackendOrigin(value) {
  if (typeof value !== 'string' || !value || value !== value.trim()) throw new Error('Set an explicit NEXT_PUBLIC_BACKEND_URL origin')
  let url
  try { url = new URL(value) } catch { throw new Error('NEXT_PUBLIC_BACKEND_URL must be an HTTP(S) origin') }
  if (!/^https?:\/\/[^/?#@]+\/?$/i.test(value) || !['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/' || /[\\\s]/.test(value)) throw new Error('NEXT_PUBLIC_BACKEND_URL must contain only an HTTP(S) origin')
  if (url.protocol === 'http:' && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) throw new Error('Non-loopback backends require HTTPS')
  return url.origin
}
function candidateAPIAllowed(pathname, method, search = '', surface = 'combine') {
  if (!['combine', 'profile'].includes(surface)) return false
  const query = new URLSearchParams(search)
  if (surface === 'combine' && pathname === '/api/combine/current' && method === 'GET') return [...query.keys()].every(k => k === 'event_id') && query.getAll('event_id').length <= 1
  if (search) return false
  if (surface === 'combine' && pathname === '/api/combine/help') return method === 'POST'
  if (surface === 'profile' && ['/api/athlete/evidence', '/api/athlete/materials'].includes(pathname)) return method === 'GET'
  if (surface === 'profile' && ['/api/athlete/debrief', '/api/athlete/opportunities', '/api/athlete/opportunities/engagement'].includes(pathname)) return method === 'POST'
  if (surface === 'profile' && pathname === '/api/athlete/workspace') return method === 'GET' || method === 'PATCH'
  if (surface === 'profile' && pathname === '/api/athlete/parent-notice') return method === 'GET' || method === 'POST'
  // Junior colleges (reviewed set): the backend owner-checks the clerk_id in each URL.
  if (surface === 'profile' && /^\/api\/workspace\/colleges\/[A-Za-z0-9_-]{1,256}(?:\/[a-z0-9-]{1,80})?$/.test(pathname)) return method === 'GET'
  if (surface === 'profile' && /^\/api\/workspace\/trigger-matching\/[A-Za-z0-9_-]{1,256}$/.test(pathname)) return method === 'POST'
  if (surface === 'profile' && /^\/api\/workspace\/colleges\/[A-Za-z0-9_-]{1,256}\/[a-z0-9-]{1,80}\/outreach-draft$/.test(pathname)) return method === 'GET' || method === 'POST'
  if (/^\/api\/profile\/by-clerk\/[A-Za-z0-9_-]{1,256}$/.test(pathname)) return method === 'GET'
  if (/^\/api\/claims\/[A-Za-z0-9_-]{1,384}(?:\.[A-Za-z0-9_-]{1,128})?\/redeem$/.test(pathname)) return method === 'POST'
  return /^\/api\/claims\/[A-Za-z0-9_-]{1,384}(?:\.[A-Za-z0-9_-]{1,128})?$/.test(pathname) && pathname !== '/api/claims/mint' && method === 'GET'
}
function resolveAPIRequest(input, origin, surface, method = 'GET') {
  if (typeof input !== 'string' || !input || /[\\\s]/.test(input) || /%(?:2e|2f|5c)/i.test(input) || /(?:^|\/)\.\.?(?:\/|$)/.test(input)) throw new Error('Invalid backend request URL')
  const base = resolveBackendOrigin(origin)
  const url = new URL(input.startsWith('/') || /^https?:\/\//.test(input) ? input : '/' + input, base)
  if (url.origin !== base || url.username || url.password || url.hash) throw new Error('Backend request must use the configured origin')
  if (isRestrictedSurface(surface) && !candidateAPIAllowed(url.pathname, method.toUpperCase(), url.search, surface)) throw new Error('This API operation is unavailable in the selected surface')
  return url.href
}
function candidatePagePolicy(pathname, method, surface = 'combine') {
  // No generic filename exemption: dynamic legacy paths can have static suffixes.
  if (!['GET', 'HEAD'].includes(method.toUpperCase())) return 'deny'
  if (pathname.startsWith('/_next/static/') || pathname === '/_next/webpack-hmr' || ['/sparq-logo.jpg', '/sparq-wordmark.png', '/favicon.ico'].includes(pathname)) return 'asset'
  if (pathname === '/') return 'home'
  if (['/home', '/home/inbox', '/connect'].includes(pathname)) return 'page'
  // GMTM entry bridge exists only on the profile surface, which has no self sign-up.
  if (surface === 'profile' && /^\/enter(?:\/(?:callback|finish|unavailable))?$/.test(pathname)) return 'page'
  if (surface === 'profile' && /^\/home\/colleges(?:\/[a-z0-9-]{1,80})?$/.test(pathname)) return 'page'
  if (surface === 'profile' && /^\/sign-up(?:\/|$)/.test(pathname)) return 'deny'
  if (/^\/sign-(?:in|up)(?:\/[A-Za-z0-9_-]+)*$/.test(pathname)) return 'page'
  if (/^\/claim\/[A-Za-z0-9_-]{1,384}(?:\.[A-Za-z0-9_-]{1,128})?(?:\/redeem)?$/.test(pathname)) return 'page'
  return 'deny'
}
// Profile surface (sparq.gmtm.com) CSP: GMTM's .gmtm.com sessionId cookie is
// script-readable, so scripts run only with the per-request nonce. Styles keep
// 'unsafe-inline' (Next/Clerk inline styles); scripts never do.
function clerkFrontendApi(publishableKey) {
  const match = /^pk_(?:test|live)_([A-Za-z0-9+/=]+)$/.exec(publishableKey || '')
  if (!match) return null
  let host
  try { host = atob(match[1]).replace(/\$$/, '') } catch { return null }
  return /^[a-z0-9.-]+$/i.test(host) ? 'https://' + host : null
}
function profileContentSecurityPolicy({ nonce, publishableKey, backendOrigin, dev = false }) {
  if (!/^[A-Za-z0-9+/=_-]{16,}$/.test(nonce || '')) throw new Error('A random CSP nonce is required')
  const clerk = clerkFrontendApi(publishableKey)
  const hosts = list => list.filter(Boolean).join(' ')
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ''} ` + hosts([clerk, 'https://challenges.cloudflare.com']),
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    "img-src 'self' data: blob: https:",
    "media-src 'self' blob: https:",
    'connect-src ' + hosts(["'self'", backendOrigin && resolveBackendOrigin(backendOrigin), clerk, 'https://clerk-telemetry.com']),
    "frame-src 'self' https://challenges.cloudflare.com",
    "worker-src 'self' blob:",
    "object-src 'none'",
    "base-uri 'self'",
    "form-action 'self'",
    "frame-ancestors 'none'",
  ].join('; ')
}
// Drop GMTM's sessionId from a Cookie header without reading its value.
function withoutGmtmSession(cookieHeader) {
  return (cookieHeader || '').split(';').map(part => part.trim()).filter(part => part && part.split('=')[0].trim() !== 'sessionId').join('; ')
}
module.exports = { profileContentSecurityPolicy, withoutGmtmSession, isCombineSurface, isProfileSurface, isRestrictedSurface, resolveBackendOrigin, candidateAPIAllowed, resolveAPIRequest, candidatePagePolicy }
