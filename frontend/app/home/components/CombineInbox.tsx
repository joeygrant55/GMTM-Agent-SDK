'use client'

import CurrentCombineCard from './CurrentCombineCard'

export default function CombineInbox() {
  return (
    <div className="mx-auto w-full max-w-4xl p-4 sm:p-6">
      <h1 className="mb-2 text-3xl font-black">My next move</h1>
      <p className="mb-6 text-sm leading-relaxed text-gray-300">Keep your USA Football entry moving. Check the requirements, continue in GMTM, and return to see your saved progress.</p>
      <CurrentCombineCard showProfileNextStep={false} />
    </div>
  )
}
