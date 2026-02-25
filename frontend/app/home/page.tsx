import nextDynamic from 'next/dynamic'

// Clerk hooks cannot run during SSR — load home content client-side only
const HomeClient = nextDynamic(() => import('./HomeClient'), { ssr: false })

export default function HomePage() {
  return <HomeClient />
}
