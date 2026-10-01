'use client'

import { signOutOfSparq } from '@/app/_lib/useSparqSession'

// Ends the SPARQ session and returns to GMTM (GMTM is the only sign-in).
export default function SignOutButton() {
  return (
    <button type="button" onClick={() => { void signOutOfSparq() }}
      className="min-h-9 rounded-md border border-white/15 px-3 text-xs font-medium text-gray-300 hover:text-white">
      Sign out
    </button>
  )
}
