import QuickScanClient from './QuickScanClient'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'SPARQ Quick Scan — Your Free Recruiting Report',
  description: 'See your real metrics and percentile rankings vs. athletes in the SPARQ database. Free for all athletes.',
}

export default function QuickScanPage() {
  return <QuickScanClient />
}
