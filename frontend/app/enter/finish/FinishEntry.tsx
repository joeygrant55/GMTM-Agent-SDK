'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useClerk } from '@clerk/nextjs'
import { completeEntry, type ClerkLike } from './complete'

export default function FinishEntry({ ticket }: { ticket: string }) {
  const router = useRouter()
  const clerk = useClerk()
  const started = useRef(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => {
    if (!clerk.loaded || started.current) return
    started.current = true
    completeEntry(clerk as unknown as ClerkLike, ticket).then(ok => {
      if (ok) router.replace('/home')
      else setFailed(true)
    })
  }, [clerk, clerk.loaded, ticket, router])

  const gmtm = process.env.NEXT_PUBLIC_GMTM_WEB_URL || 'https://gmtm.com'
  return (
    <main className="min-h-screen bg-sparq-charcoal flex items-center justify-center px-4 text-center">
      {failed ? (
        <div className="max-w-md">
          <h1 className="text-2xl font-bold text-white mb-3">We could not sign you in</h1>
          <p className="text-gray-400 mb-8">This sign-in link has expired. Open SPARQ from GMTM again.</p>
          <a href={gmtm} className="px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg">Back to GMTM</a>
        </div>
      ) : (
        <p role="status" className="text-gray-300">Signing you in…</p>
      )}
    </main>
  )
}
