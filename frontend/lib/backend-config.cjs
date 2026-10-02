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
  if (surface === 'profile' && pathname === '/api/athlete/workspace') return method === 'GET' || method === 'PATCH'
  if (surface === 'profile' && pathname === '/api/athlete/parent-notice') return method === 'GET' || method === 'POST'
  // Junior colleges (reviewed set): the backend owner-checks the clerk_id in each URL.
  if (surface === 'profile' && /^\/api\/workspace\/colleges\/[A-Za-z0-9_-]{1,256}(?:\/[a-z0-9-]{1,80})?$/.test(pathname)) return method === 'GET'
  if (surface === 'profile' && /^\/api\/workspace\/trigger-matching\/[A-Za-z0-9_-]{1,256}$/.test(pathname)) return method === 'POST'
  if (surface === 'profile' && /^\/api\/workspace\/colleges\/[A-Za-z0-9_-]{1,256}\/[a-z0-9-]{1,80}\/outreach-draft$/.test(pathname)) return method === 'GET' || method === 'POST'
  // Saves (heart) and "I sent it" marks, owner-checked by the backend.
  if (surface === 'profile' && /^\/api\/workspace\/saved-colleges\/[A-Za-z0-9_-]{1,256}$/.test(pathname)) return method === 'GET'
  if (surface === 'profile' && /^\/api\/workspace\/saved-colleges\/[A-Za-z0-9_-]{1,256}\/[a-z0-9-]{1,80}$/.test(pathname)) return method === 'POST'
  if (surface === 'profile' && /^\/api\/workspace\/colleges\/[A-Za-z0-9_-]{1,256}\/[a-z0-9-]{1,80}\/sent$/.test(pathname)) return method === 'POST'
  // Emails page (drafts + sent marks, no coach contact) and the parent address for CC; owner-checked.
  if (surface === 'profile' && /^\/api\/workspace\/college-emails\/[A-Za-z0-9_-]{1,256}$/.test(pathname)) return method === 'GET'
  if (surface === 'profile' && /^\/api\/workspace\/parent-contact\/[A-Za-z0-9_-]{1,256}$/.test(pathname)) return method === 'GET' || method === 'POST'
  // My card: her ordered highlight picks; owner-checked by the backend. No public card.
  if (surface === 'profile' && /^\/api\/workspace\/card\/[A-Za-z0-9_-]{1,256}$/.test(pathname)) return method === 'GET' || method === 'POST'
  if (surface === 'profile' && /^\/api\/workspace\/card\/[A-Za-z0-9_-]{1,256}\/lead$/.test(pathname)) return method === 'GET'
  return /^\/api\/profile\/by-owner\/[A-Za-z0-9_-]{1,256}$/.test(pathname) && method === 'GET'
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
  // Same-origin SPARQ routes: session read, sign-out and the backend proxy.
  // Each handler checks its own method, session and (proxy) candidateAPIAllowed.
  if (/^\/api\/sparq\/(?:session|sign-out|proxy\/[^?#]*)$/.test(pathname)) return 'api'
  // No generic filename exemption: dynamic legacy paths can have static suffixes.
  if (!['GET', 'HEAD'].includes(method.toUpperCase())) return 'deny'
  if (pathname.startsWith('/_next/static/') || pathname === '/_next/webpack-hmr' || ['/sparq-logo.jpg', '/sparq-wordmark.png', '/favicon.ico'].includes(pathname)) return 'asset'
  // Bundled continental US outline for the colleges map (no tile server).
  if (surface === 'profile' && pathname === '/us-states.svg') return 'asset'
  if (pathname === '/') return 'home'
  if (['/home', '/home/inbox'].includes(pathname)) return 'page'
  // GMTM entry bridge: GMTM is the only sign-in (no self sign-up) on every surface.
  if (/^\/enter(?:\/(?:callback|unavailable))?$/.test(pathname)) return 'page'
  if (surface === 'profile' && /^\/home\/colleges(?:\/[a-z0-9-]{1,80})?$/.test(pathname)) return 'page'
  if (surface === 'profile' && ['/home/progress', '/home/footage', '/home/emails', '/home/card'].includes(pathname)) return 'page'
  return 'deny'
}
// CSP for every surface: GMTM's .gmtm.com sessionId cookie is script-readable, so
// scripts run only with the per-request nonce. No third-party sign-in hosts: the
// browser talks to its own origin (the /api/sparq proxy) plus, on the legacy
// surface only, `connect` (the backend origin its public pages read directly).
// Styles keep 'unsafe-inline' (Next inline styles). The profile surface loads images only from
// itself, GMTM's CDN and YouTube's thumbnail host (her film posters), and video only from GMTM's
// CDN (her clips); other surfaces keep https:.
const GMTM_CDN = 'https://cdn.gmtm.com'
const YOUTUBE_POSTERS = 'https://i.ytimg.com'
function profileContentSecurityPolicy({ nonce, dev = false, connect = '', profile = false }) {
  if (!/^[A-Za-z0-9+/=_-]{16,}$/.test(nonce || '')) throw new Error('A random CSP nonce is required')
  return [
    "default-src 'self'",
    `script-src 'self' 'nonce-${nonce}' 'strict-dynamic'${dev ? " 'unsafe-eval'" : ''}`,
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com",
    "font-src 'self' https://fonts.gstatic.com",
    profile ? `img-src 'self' data: ${GMTM_CDN} ${YOUTUBE_POSTERS}` : "img-src 'self' data: blob: https:",
    profile ? `media-src 'self' ${GMTM_CDN}` : "media-src 'self' blob: https:",
    `connect-src 'self'${connect ? ' ' + resolveBackendOrigin(connect) : ''}`,
    "frame-src 'none'",
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
