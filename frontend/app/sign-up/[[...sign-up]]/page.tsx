import { SignUp } from '@clerk/nextjs'

export default function SignUpPage() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <img src="/sparq-logo.jpg" alt="SPARQ" className="w-16 h-16 rounded-xl mx-auto mb-6" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Join SPARQ</h1>
        <p className="text-gray-600 mb-8">Create your account to get started</p>
        <SignUp afterSignUpUrl="/connect" />
      </div>
    </div>
  )
}
