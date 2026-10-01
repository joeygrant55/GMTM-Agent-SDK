export function isCombineSurface(value: string | undefined): boolean
export function isProfileSurface(value: string | undefined): boolean
export function isRestrictedSurface(value: string | undefined): boolean
export function resolveBackendOrigin(value: string | undefined): string
export function candidateAPIAllowed(pathname: string, method: string, search?: string, surface?: string): boolean
export function resolveAPIRequest(input: string, origin: string, surface: string | undefined, method?: string): string
export function candidatePagePolicy(pathname: string, method: string, surface?: string): 'deny' | 'asset' | 'home' | 'page'
export function profileContentSecurityPolicy(options: { nonce: string; publishableKey?: string; backendOrigin?: string; dev?: boolean }): string
export function withoutGmtmSession(cookieHeader: string | null | undefined): string
