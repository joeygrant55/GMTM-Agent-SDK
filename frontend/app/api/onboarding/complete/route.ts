import { NextRequest, NextResponse } from 'next/server'
import { auth } from '@clerk/nextjs/server'
import { CompleteOnboardingPayload } from '@/app/onboarding/_lib/types'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

export async function POST(request: NextRequest) {
  const { userId } = await auth()
  let payload: CompleteOnboardingPayload

  try {
    payload = (await request.json()) as CompleteOnboardingPayload
  } catch {
    return NextResponse.json({ error: 'Invalid JSON body.' }, { status: 400 })
  }

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
  const enrichedPayload = { ...payload, clerk_id: userId }

  try {
    const res = await fetch(`${backendUrl}/api/profile/create-from-onboarding`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'application/json',
      },
      body: JSON.stringify(enrichedPayload),
      cache: 'no-store',
    })

    const data = await res.json().catch(() => ({}))

    if (!res.ok) {
      const errorMessage = typeof data?.detail === 'string'
        ? data.detail
        : typeof data?.error === 'string'
          ? data.error
          : 'Failed to complete onboarding.'

      return NextResponse.json({ error: errorMessage }, { status: res.status })
    }

    const profileId = data?.profile_id ?? data?.user_id ?? data?.id ?? null

    return NextResponse.json({
      success: true,
      profile_id: profileId,
      data,
    })
  } catch {
    return NextResponse.json({ error: 'Backend unavailable. Please try again.' }, { status: 502 })
  }
}
