import type { Metadata } from 'next'
import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'

export const metadata: Metadata = {
  title: 'SPARQ Agent — The AI Recruiting Agent for Flag Football',
  description:
    'Powered by the SPARQ testing USA Flag Football selects national team athletes from. Verified metrics, honest odds, and an AI agent that works your recruiting every week.',
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
    return <ClerkProvider publishableKey={clerkKey}>{body}</ClerkProvider>
  }
  return body
}
