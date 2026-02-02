'use client'

import { useState } from 'react'

export default function Home() {
  const [athleteId, setAthleteId] = useState('')
  
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">⚡</span>
              </div>
              <h1 className="text-2xl font-bold text-gray-900">SPARQ Agent</h1>
            </div>
            <button className="px-4 py-2 text-sm font-medium text-indigo-600 hover:text-indigo-700">
              Sign In with GMTM
            </button>
          </div>
        </div>
      </header>

      {/* Hero Section */}
      <main className="max-w-4xl mx-auto px-4 py-16 sm:px-6 lg:px-8">
        <div className="text-center">
          <h2 className="text-5xl font-extrabold text-gray-900 sm:text-6xl">
            Your 24/7 AI
            <span className="text-indigo-600"> Recruiting Coordinator</span>
          </h2>
          <p className="mt-6 text-xl text-gray-600 max-w-2xl mx-auto">
            From youth camps to professional tryouts, SPARQ Agent finds opportunities, 
            tracks your progress, and helps you get recruited.
          </p>
        </div>

        {/* Quick Stats */}
        <div className="mt-12 grid grid-cols-3 gap-6">
          <div className="bg-white rounded-lg shadow-sm p-6 text-center">
            <div className="text-3xl font-bold text-indigo-600">75K+</div>
            <div className="mt-2 text-sm text-gray-600">Athletes Tracked</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6 text-center">
            <div className="text-3xl font-bold text-indigo-600">7K+</div>
            <div className="mt-2 text-sm text-gray-600">SPARQ Verified</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6 text-center">
            <div className="text-3xl font-bold text-indigo-600">24/7</div>
            <div className="mt-2 text-sm text-gray-600">Always Working</div>
          </div>
        </div>

        {/* Demo Access */}
        <div className="mt-16 bg-white rounded-xl shadow-lg p-8">
          <h3 className="text-2xl font-bold text-gray-900 text-center mb-6">
            See What SPARQ Agent Can Do
          </h3>
          <div className="max-w-md mx-auto">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter an athlete ID to demo (e.g. 383, 435, 2370)
            </label>
            <div className="flex space-x-3">
              <input
                type="number"
                value={athleteId}
                onChange={(e) => setAthleteId(e.target.value)}
                placeholder="Athlete ID"
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
              <button 
                onClick={() => {
                  if (athleteId) {
                    window.location.href = `/athlete/${athleteId}`
                  }
                }}
                className="px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
              >
                View Dashboard
              </button>
            </div>
            <p className="mt-3 text-sm text-gray-500 text-center">
              Or <a href="/athlete/383" className="text-indigo-600 hover:text-indigo-700 font-medium">try athlete #383</a>
            </p>
          </div>
        </div>

        {/* Features */}
        <div className="mt-16 grid md:grid-cols-2 gap-8">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="text-3xl mb-3">🎯</div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">Opportunity Discovery</h4>
            <p className="text-gray-600">
              Find camps, showcases, colleges, and teams actively looking for athletes like you.
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="text-3xl mb-3">📊</div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">Market Intelligence</h4>
            <p className="text-gray-600">
              See where you rank against peers and understand your recruiting potential.
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="text-3xl mb-3">💬</div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">Smart Communication</h4>
            <p className="text-gray-600">
              Draft emails to coaches and get guidance on what to say and when to reach out.
            </p>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="text-3xl mb-3">🔔</div>
            <h4 className="text-lg font-semibold text-gray-900 mb-2">Proactive Alerts</h4>
            <p className="text-gray-600">
              Get notified when coaches view your profile or new opportunities match your criteria.
            </p>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-20 bg-white border-t">
        <div className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
          <p className="text-center text-gray-500 text-sm">
            Powered by GMTM data • Built for athletes, by athletes
          </p>
        </div>
      </footer>
    </div>
  )
}
