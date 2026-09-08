export function isCombineSurface(value: string | undefined): boolean
export function resolveBackendOrigin(value: string | undefined): string
export function candidateAPIAllowed(pathname: string, method: string, search?: string): boolean
export function resolveAPIRequest(input: string, origin: string, surface: string | undefined, method?: string): string
export function candidatePagePolicy(pathname: string, method: string): 'deny' | 'asset' | 'home' | 'page'
