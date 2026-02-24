import ConnectClient from './ConnectClient'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Connect Your Profile | SPARQ Agent',
  description: 'Link your GMTM athlete profile to SPARQ Agent.',
}

export default function ConnectPage() {
  return <ConnectClient />
}
