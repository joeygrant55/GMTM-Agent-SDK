import type { Metadata } from 'next'
import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'
import { isCombineSurface, isProfileSurface } from '@/lib/backend-config.cjs'

const combine = isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE)
const profile = isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)

export const metadata: Metadata = {
  title: profile ? 'SPARQ — Your athlete profile' : combine ? 'SPARQ — Your digital combine' : 'SPARQ Agent — The AI Recruiting Advisor',
  description: profile ? 'Understand your athletic evidence and put your profile to work.' : combine ? 'Know what to submit, get help with each activity, and keep your digital combine moving.' :
    'Built on 75,000 athlete profiles and 2,900 college programs. The recruiting consultant your family couldn\u2019t afford — for $29/month.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

  const body = (
    <html lang="en" className="bg-sparq-charcoal">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=Inter:wght@400;500;600;700&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="bg-sparq-charcoal text-white antialiased">{children}</body>
    </html>
  )

  if (clerkKey) {
    // Profile (sparq.gmtm.com): juniors sign in only through GMTM, so sign-out returns there.
    const afterSignOutUrl = profile ? process.env.NEXT_PUBLIC_GMTM_WEB_URL || undefined : undefined
    // Profile renders per request so Next and Clerk scripts carry the middleware CSP nonce.
    return <ClerkProvider publishableKey={clerkKey} afterSignOutUrl={afterSignOutUrl} dynamic={profile}>{body}</ClerkProvider>
  }
  return body
}
