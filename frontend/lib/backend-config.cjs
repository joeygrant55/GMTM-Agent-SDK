// Pure configuration and route policy shared by Next, Edge and browser code.
// No environment reads here: callers use explicit (statically inlined) settings.
function isCombineSurface(value) {
  if (value === undefined || value === '' || value === 'legacy') return false
  if (value === 'combine') return true
  throw new Error('NEXT_PUBLIC_APP_SURFACE must be combine or legacy')
}
function resolveBackendOrigin(value) {
  if (typeof value !== 'string' || !value || value !== value.trim()) throw new Error('Set an explicit NEXT_PUBLIC_BACKEND_URL origin')
  let url
  try { url = new URL(value) } catch { throw new Error('NEXT_PUBLIC_BACKEND_URL must be an HTTP(S) origin') }
  if (!/^https?:\/\/[^/?#@]+\/?$/i.test(value) || !['http:', 'https:'].includes(url.protocol) || url.username || url.password || url.search || url.hash || url.pathname !== '/' || /[\\\s]/.test(value)) throw new Error('NEXT_PUBLIC_BACKEND_URL must contain only an HTTP(S) origin')
  if (url.protocol === 'http:' && !['localhost', '127.0.0.1', '[::1]'].includes(url.hostname)) throw new Error('Non-loopback backends require HTTPS')
  return url.origin
}
function candidateAPIAllowed(pathname, method, search = '') {
  const query = new URLSearchParams(search)
  if (pathname === '/api/combine/current' && method === 'GET') return [...query.keys()].every(k => k === 'event_id') && query.getAll('event_id').length <= 1
  if (search) return false
  if (pathname === '/api/combine/help') return method === 'POST'
  if (/^\/api\/profile\/by-clerk\/[A-Za-z0-9_-]{1,256}$/.test(pathname)) return method === 'GET'
  if (/^\/api\/claims\/[A-Za-z0-9_-]{1,384}(?:\.[A-Za-z0-9_-]{1,128})?\/redeem$/.test(pathname)) return method === 'POST'
  return /^\/api\/claims\/[A-Za-z0-9_-]{1,384}(?:\.[A-Za-z0-9_-]{1,128})?$/.test(pathname) && pathname !== '/api/claims/mint' && method === 'GET'
}
function resolveAPIRequest(input, origin, surface, method = 'GET') {
  if (typeof input !== 'string' || !input || /[\\\s]/.test(input) || /%(?:2e|2f|5c)/i.test(input) || /(?:^|\/)\.\.?(?:\/|$)/.test(input)) throw new Error('Invalid backend request URL')
  const base = resolveBackendOrigin(origin)
  const url = new URL(input.startsWith('/') || /^https?:\/\//.test(input) ? input : '/' + input, base)
  if (url.origin !== base || url.username || url.password || url.hash) throw new Error('Backend request must use the configured origin')
  if (isCombineSurface(surface) && !candidateAPIAllowed(url.pathname, method.toUpperCase(), url.search)) throw new Error('This API operation is unavailable in the combine surface')
  return url.href
}
function candidatePagePolicy(pathname, method) {
  // No generic filename exemption: dynamic legacy paths can have static suffixes.
  if (!['GET', 'HEAD'].includes(method.toUpperCase())) return 'deny'
  if (pathname.startsWith('/_next/static/') || pathname === '/_next/webpack-hmr' || ['/sparq-logo.jpg', '/favicon.ico'].includes(pathname)) return 'asset'
  if (pathname === '/') return 'home'
  if (['/home', '/home/inbox', '/connect'].includes(pathname)) return 'page'
  if (/^\/sign-(?:in|up)(?:\/[A-Za-z0-9_-]+)*$/.test(pathname)) return 'page'
  if (/^\/claim\/[A-Za-z0-9_-]{1,384}(?:\.[A-Za-z0-9_-]{1,128})?(?:\/redeem)?$/.test(pathname)) return 'page'
  return 'deny'
}
module.exports = { isCombineSurface, resolveBackendOrigin, candidateAPIAllowed, resolveAPIRequest, candidatePagePolicy }
