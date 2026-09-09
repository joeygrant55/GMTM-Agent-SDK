import { SignUp } from '@clerk/nextjs'
import SparqLogo from '@/components/SparqLogo'

export default function SignUpPage() {
  return (
    <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center">
      <div className="text-center">
        <SparqLogo className="mx-auto mb-6 w-[168px]" />
        <p className="text-gray-400 mb-8">Create your account to get started</p>
        <SignUp fallbackRedirectUrl="/connect" />
      </div>
    </div>
  )
}
