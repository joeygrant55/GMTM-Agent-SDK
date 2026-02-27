import { NextRequest, NextResponse } from 'next/server'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'
const FALLBACK_ERROR = 'Our AI is taking a quick break. Try again in a moment.'

interface ChatMessage {
  role: string
  content: string
}

interface DemoChatBody {
  message?: string
  history?: ChatMessage[]
}

export async function POST(request: NextRequest) {
  let body: DemoChatBody

  try {
    body = (await request.json()) as DemoChatBody
  } catch {
    return NextResponse.json({ error: 'Invalid request body.' }, { status: 400 })
  }

  const userMessage = body.message?.trim()
  if (!userMessage) {
    return NextResponse.json({ error: 'Message is required.' }, { status: 400 })
  }

  const history = Array.isArray(body.history) ? body.history : []
  const contextLines = history
    .slice(-8)
    .map((entry) => {
      const role = entry?.role === 'assistant' ? 'Assistant' : 'User'
      const content = String(entry?.content || '').trim()
      return content ? `${role}: ${content}` : ''
    })
    .filter(Boolean)

  const contextualMessage = contextLines.length
    ? `Conversation so far:\n${contextLines.join('\n')}\n\nLatest user question: ${userMessage}`
    : userMessage

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
  const params = new URLSearchParams({
    athlete_id: `demo-${Math.random().toString(36).slice(2, 10)}`,
    message: contextualMessage,
  })

  try {
    const res = await fetch(`${backendUrl}/api/agent/stream?${params.toString()}`, {
      method: 'GET',
      headers: {
        Accept: 'text/event-stream',
      },
      cache: 'no-store',
    })

    if (!res.ok || !res.body) {
      return NextResponse.json({ error: FALLBACK_ERROR }, { status: 502 })
    }

    return new Response(res.body, {
      status: 200,
      headers: {
        'Content-Type': 'text/event-stream; charset=utf-8',
        'Cache-Control': 'no-cache, no-transform',
        Connection: 'keep-alive',
      },
    })
  } catch {
    return NextResponse.json({ error: FALLBACK_ERROR }, { status: 502 })
  }
}
