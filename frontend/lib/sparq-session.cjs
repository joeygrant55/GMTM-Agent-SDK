// SPARQ session (profile surface, sparq.gmtm.com). No Clerk: GMTM sign-in is the
// only sign-in (Joey, 2026-10-01). The backend signs an HS256 token
// {sub, jti, gsh, iat, exp} with SPARQ_SESSION_SECRET; gsh = sha256 hex of the GMTM
// sessionId the user entered with. Web Crypto only, so Edge middleware, route
// handlers and Node tests share this code. The raw GMTM sessionId is read only by
// gmtmSessionHash and is never stored, forwarded or logged.
const SESSION_COOKIE = '__Host-sparq-session'
const GSH_HEADER = 'x-sparq-gsh'
const SESSION_SECONDS = 24 * 60 * 60
const GSH = /^[0-9a-f]{64}$/

const bytes = text => new TextEncoder().encode(text)
const hex = buffer => [...new Uint8Array(buffer)].map(b => b.toString(16).padStart(2, '0')).join('')
async function sha256Hex(text) { return hex(await crypto.subtle.digest('SHA-256', bytes(text))) }
function base64url(text) {
  if (!/^[A-Za-z0-9_-]*$/.test(text)) throw Error('bad base64url')
  const b64 = text.replace(/-/g, '+').replace(/_/g, '/') + '='.repeat((4 - text.length % 4) % 4)
  return Uint8Array.from(atob(b64), c => c.charCodeAt(0))
}
function sameText(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string' || a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
  return diff === 0
}

// sha256 hex of GMTM's sessionId from a Cookie header, or null when absent.
async function gmtmSessionHash(cookieHeader) {
  for (const part of (cookieHeader || '').split(';')) {
    const at = part.indexOf('=')
    if (at > 0 && part.slice(0, at).trim() === 'sessionId') {
      const value = part.slice(at + 1).trim()
      return value ? sha256Hex(value) : null
    }
  }
  return null
}

// Returns {sub, exp} only for a well-formed, correctly signed, unexpired token whose
// gsh equals expectedGsh (the current browser's GMTM session). Never throws.
async function verifySession(token, secret, expectedGsh, now = Math.floor(Date.now() / 1000)) {
  try {
    if (typeof secret !== 'string' || bytes(secret).length < 32 || typeof expectedGsh !== 'string' || !GSH.test(expectedGsh)) return null
    const parts = typeof token === 'string' ? token.split('.') : []
    if (parts.length !== 3) return null
    const header = JSON.parse(new TextDecoder().decode(base64url(parts[0])))
    if (header?.alg !== 'HS256') return null
    const key = await crypto.subtle.importKey('raw', bytes(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['verify'])
    if (!await crypto.subtle.verify('HMAC', key, base64url(parts[2]), bytes(parts[0] + '.' + parts[1]))) return null
    const claims = JSON.parse(new TextDecoder().decode(base64url(parts[1])))
    const { sub, jti, gsh, iat, exp } = claims || {}
    if (typeof sub !== 'string' || !sub || typeof jti !== 'string' || !jti || !Number.isInteger(iat) || !Number.isInteger(exp)) return null
    if (!(exp > now) || iat > now + 60 || typeof gsh !== 'string' || !GSH.test(gsh)) return null
    if (!sameText(gsh, expectedGsh)) return null
    return { sub, exp }
  } catch {
    return null
  }
}

// __Host- requires Secure, Path=/ and no Domain. Browsers accept Secure on http://localhost.
function sessionCookie(token) {
  return { name: SESSION_COOKIE, value: token, httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: SESSION_SECONDS }
}
function clearedSessionCookie() { return { ...sessionCookie(''), maxAge: 0 } }

module.exports = { SESSION_COOKIE, GSH_HEADER, SESSION_SECONDS, sha256Hex, gmtmSessionHash, verifySession, sessionCookie, clearedSessionCookie }
