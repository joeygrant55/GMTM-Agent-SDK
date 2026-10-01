import SparqLogo from '@/components/SparqLogo'

export const dynamic = 'force-dynamic'

export default function EntryUnavailablePage({ searchParams }: { searchParams: { reason?: string } }) {
  const retry = searchParams.reason === 'retry'
  const linked = searchParams.reason === 'linked'
  const gmtm = process.env.NEXT_PUBLIC_GMTM_WEB_URL || 'https://gmtm.com'
  return (
    <main className="min-h-screen bg-sparq-charcoal flex items-center justify-center px-4 text-center">
      <div className="max-w-md">
        <SparqLogo className="mx-auto mb-6 w-[168px]" />
        <h1 className="text-2xl font-bold text-white mb-3">{linked ? 'This account is already connected' : retry ? 'Let’s try that again' : 'SPARQ is not open to you yet'}</h1>
        <p className="text-gray-400 mb-8">
          {linked
            ? 'Your GMTM account is already connected to a SPARQ account. Contact support@gmtm.com.'
            : retry
            ? 'This sign-in link expired or was already used. Open SPARQ from GMTM again.'
            : 'SPARQ is open to a small group of junior flag athletes right now. Thanks for your interest. Keep building your GMTM profile.'}
        </p>
        <a href={gmtm} className="px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg">Back to GMTM</a>
      </div>
    </main>
  )
}
