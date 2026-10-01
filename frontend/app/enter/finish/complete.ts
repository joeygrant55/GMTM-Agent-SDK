// Pure completion step, testable with a fake Clerk. Every entry replaces the
// current session: sign out first (callback form, so Clerk does not navigate),
// then redeem the one-use ticket on the fresh client.
export type ClerkLike = {
  session?: unknown
  signOut: (callback: () => void) => Promise<void>
  client?: { signIn: { create: (p: { strategy: 'ticket'; ticket: string }) => Promise<{ status: string | null; createdSessionId: string | null }> } }
  setActive: (p: { session: string }) => Promise<void>
}

export async function completeEntry(clerk: ClerkLike, ticket: string): Promise<boolean> {
  if (!ticket) return false
  try {
    if (clerk.session) await clerk.signOut(() => {})
    if (!clerk.client) return false
    const attempt = await clerk.client.signIn.create({ strategy: 'ticket', ticket })
    if (attempt.status !== 'complete' || !attempt.createdSessionId) return false
    await clerk.setActive({ session: attempt.createdSessionId })
    return true
  } catch {
    return false
  }
}
