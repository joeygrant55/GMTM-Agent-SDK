import type { Metadata } from 'next'
import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'

export const metadata: Metadata = {
  title: 'SPARQ Agent — Women’s Flag Football Recruiting, $29/mo',
  description:
    'The AI recruiting advisor for women’s flag football athletes. Every active NCAA, NAIA, and NJCAA program — tiered Reach / Target / Likely based on your stats. $29/month. Cheaper than the consultant your family couldn\u2019t afford — for $29/month.',
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
