'use client'

import { useEffect, useState } from 'react'

export default function TestPage() {
  const [results, setResults] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const testAPIs = async () => {
      const tests = []
      
      // Test 1: Backend health
      try {
        const res = await fetch('/api/health')
        const data = await res.json()
        tests.push({ name: 'Backend Health', status: 'OK', data })
      } catch (err: any) {
        tests.push({ name: 'Backend Health', status: 'FAIL', error: err.message })
      }

      // Test 2: Valid athlete (383)
      try {
        const res = await fetch('/api/athlete/383')
        if (res.ok) {
          const data = await res.json()
          tests.push({ name: 'Athlete 383 (Valid)', status: 'OK', data })
        } else {
          tests.push({ name: 'Athlete 383 (Valid)', status: 'FAIL', error: `HTTP ${res.status}` })
        }
      } catch (err: any) {
        tests.push({ name: 'Athlete 383 (Valid)', status: 'FAIL', error: err.message })
      }

      // Test 3: Invalid athlete (2)
      try {
        const res = await fetch('/api/athlete/2')
        if (!res.ok) {
          const data = await res.json()
          tests.push({ name: 'Athlete 2 (Invalid - should 404)', status: 'OK', data })
        } else {
          tests.push({ name: 'Athlete 2 (Invalid)', status: 'UNEXPECTED', error: 'Should have returned 404' })
        }
      } catch (err: any) {
        tests.push({ name: 'Athlete 2 (Invalid)', status: 'FAIL', error: err.message })
      }

      // Test 4: Search API
      try {
        const res = await fetch('/api/search?state=TX&limit=3')
        const data = await res.json()
        tests.push({ name: 'Search API (TX athletes)', status: 'OK', data })
      } catch (err: any) {
        tests.push({ name: 'Search API', status: 'FAIL', error: err.message })
      }

      setResults(tests)
      setLoading(false)
    }

    testAPIs()
  }, [])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 p-8">
        <h1 className="text-2xl font-bold mb-4">SPARQ Agent API Test</h1>
        <p>Running tests...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-2xl font-bold mb-6">SPARQ Agent API Test Results</h1>
      
      <div className="space-y-4">
        {results?.map((test: any, idx: number) => (
          <div key={idx} className={`p-4 rounded-lg ${
            test.status === 'OK' ? 'bg-green-50 border-2 border-green-200' :
            test.status === 'FAIL' ? 'bg-red-50 border-2 border-red-200' :
            'bg-yellow-50 border-2 border-yellow-200'
          }`}>
            <div className="flex items-center justify-between mb-2">
              <h3 className="font-semibold text-gray-900">{test.name}</h3>
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                test.status === 'OK' ? 'bg-green-100 text-green-800' :
                test.status === 'FAIL' ? 'bg-red-100 text-red-800' :
                'bg-yellow-100 text-yellow-800'
              }`}>
                {test.status}
              </span>
            </div>
            {test.error && (
              <p className="text-sm text-red-600 mb-2">Error: {test.error}</p>
            )}
            {test.data && (
              <pre className="text-xs bg-white p-3 rounded border overflow-auto max-h-40">
                {JSON.stringify(test.data, null, 2)}
              </pre>
            )}
          </div>
        ))}
      </div>

      <div className="mt-8 flex gap-4">
        <a href="/" className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700">
          ← Home
        </a>
        <a href="/athlete/383" className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700">
          Test Athlete #383
        </a>
        <a href="/athlete/2" className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700">
          Test Athlete #2 (should error)
        </a>
      </div>
    </div>
  )
}
