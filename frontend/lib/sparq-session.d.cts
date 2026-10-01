export const SESSION_COOKIE: '__Host-sparq-session'
export const GSH_HEADER: 'x-sparq-gsh'
export const SESSION_SECONDS: number
export function sha256Hex(text: string): Promise<string>
export function gmtmSessionHash(cookieHeader: string | null | undefined): Promise<string | null>
export function verifySession(token: string | undefined, secret: string | undefined, expectedGsh: string | null | undefined, now?: number): Promise<{ sub: string; exp: number } | null>
type Cookie = { name: string; value: string; httpOnly: true; secure: true; sameSite: 'lax'; path: '/'; maxAge: number }
export function sessionCookie(token: string): Cookie
export function clearedSessionCookie(): Cookie
