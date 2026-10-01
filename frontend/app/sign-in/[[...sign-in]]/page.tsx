import { SignIn } from '@clerk/nextjs'
import SparqLogo from '@/components/SparqLogo'
import { isCombineSurface, isProfileSurface } from '@/lib/backend-config.cjs'

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center">
      <div className="text-center">
        <SparqLogo className="mx-auto mb-6 w-[168px]" />
        <p className="text-gray-400 mb-8">{isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE) ? 'Sign in to your private athlete profile' : isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE) ? 'Sign in to continue your digital combine' : 'Sign in to access your AI recruiting agent'}</p>
        {/* Profile surface has no self sign-up (/sign-up is denied), so hide its link. */}
        <SignIn fallbackRedirectUrl="/connect" {...(isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE) ? { appearance: { elements: { footerAction: { display: 'none' } } } } : {})} />
      </div>
    </div>
  )
}
