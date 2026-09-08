export interface ProfileConnection {
  found: boolean
  user_id: number | null
  has_sparq_profile: boolean
}

export class ProfileConnectionError extends Error {
  constructor(public readonly status?: number) {
    super(status === 401
      ? 'Sign in again to check your profile connection.'
      : status === 409
        ? 'Your athlete connection needs review. Contact your combine organizer for help.'
        : 'We could not confirm your profile connection. Please try again.')
    this.name = 'ProfileConnectionError'
  }
}

export function readProfileConnection(value: unknown): ProfileConnection {
  if (!value || typeof value !== 'object' || Array.isArray(value)) throw new ProfileConnectionError()
  const data = value as Partial<ProfileConnection>
  if (typeof data.found !== 'boolean' || typeof data.has_sparq_profile !== 'boolean'
    || (data.found
      ? !(typeof data.user_id === 'number' && Number.isSafeInteger(data.user_id) && data.user_id > 0)
      : data.user_id !== null)) throw new ProfileConnectionError()
  return { found: data.found, user_id: data.found ? data.user_id as number : null, has_sparq_profile: data.has_sparq_profile }
}

export async function readProfileConnectionResponse(response: Response): Promise<ProfileConnection> {
  if (!response.ok) throw new ProfileConnectionError(response.status)
  let data: unknown
  try { data = await response.json() } catch { throw new ProfileConnectionError() }
  return readProfileConnection(data)
}
