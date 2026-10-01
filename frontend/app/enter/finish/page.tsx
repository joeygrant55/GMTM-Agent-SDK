// Reads the short-lived ticket cookie on the server; the client completes sign-in.
import { cookies } from 'next/headers'
import { TICKET_COOKIE } from '../entry'
import FinishEntry from './FinishEntry'

export const dynamic = 'force-dynamic'

export default function FinishEntryPage() {
  return <FinishEntry ticket={cookies().get(TICKET_COOKIE)?.value ?? ''} />
}
