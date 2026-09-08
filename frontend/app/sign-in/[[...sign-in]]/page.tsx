import { SignIn } from '@clerk/nextjs'
import { isCombineSurface } from '@/lib/backend-config.cjs'

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center">
      <div className="text-center">
        <img src="/sparq-logo.jpg" alt="SPARQ" className="w-14 h-14 rounded-2xl mx-auto mb-6" />
        <p className="text-gray-400 mb-8">{isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE) ? 'Sign in to continue your digital combine' : 'Sign in to access your AI recruiting agent'}</p>
        <SignIn fallbackRedirectUrl="/connect" />
      </div>
    </div>
  )
}
