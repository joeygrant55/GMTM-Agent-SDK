import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center">
      <div className="text-center">
        <img src="/sparq-logo-white.png" alt="SPARQ" className="h-10 w-auto mx-auto mb-6" />
        <p className="text-gray-400 mb-8">Create your account to get started</p>
        <SignUp afterSignUpUrl="/connect" />
      </div>
    </div>
  )
}
