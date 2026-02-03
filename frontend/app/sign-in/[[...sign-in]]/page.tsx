import { SignIn } from '@clerk/nextjs'

export default function SignInPage() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <img src="/sparq-logo.jpg" alt="SPARQ" className="w-16 h-16 rounded-xl mx-auto mb-6" />
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Welcome to SPARQ</h1>
        <p className="text-gray-600 mb-8">Sign in to access your AI recruiting agent</p>
        <SignIn afterSignInUrl="/athlete/383" />
      </div>
    </div>
  )
}
