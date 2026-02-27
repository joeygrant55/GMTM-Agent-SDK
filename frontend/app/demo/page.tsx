'use client'

import { useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import ReactMarkdown from 'react-markdown'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

const STARTER_PROMPTS = [
  'What D1 schools recruit safeties from Texas?',
  'How do I email a college coach for the first time?',
  'What stats do D2 coaches look for in a linebacker?',
  'When should I start the recruiting process as a junior?',
]

const MAX_FREE_QUESTIONS = 3
const QUESTION_KEY = 'sparq_demo_questions'
const DEMO_ERROR = 'Our AI is taking a quick break. Try again in a moment.'

function getInitialCount(): number {
  if (typeof window === 'undefined') return 0
  const raw = window.localStorage.getItem(QUESTION_KEY)
  const value = Number.parseInt(raw || '0', 10)
  if (!Number.isFinite(value)) return 0
  return Math.min(Math.max(value, 0), MAX_FREE_QUESTIONS)
}

export default function DemoPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [toolActivity, setToolActivity] = useState<string | null>(null)
  const [questionsUsed, setQuestionsUsed] = useState(getInitialCount)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const gated = questionsUsed >= MAX_FREE_QUESTIONS

  const usageText = useMemo(() => `${questionsUsed}/${MAX_FREE_QUESTIONS} questions used`, [questionsUsed])

  const persistQuestionCount = (nextValue: number) => {
    setQuestionsUsed(nextValue)
    if (typeof window !== 'undefined') {
      window.localStorage.setItem(QUESTION_KEY, String(nextValue))
    }
  }

  const scrollToBottom = () => {
    requestAnimationFrame(() => {
      messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    })
  }

  const sendMessage = async (prompt?: string) => {
    if (loading || gated) return

    const userMessage = (prompt ?? input).trim()
    if (!userMessage) return

    setInput('')
    setLoading(true)
    setToolActivity(null)

    const nextMessages: Message[] = [...messages, { role: 'user', content: userMessage }, { role: 'assistant', content: '' }]
    setMessages(nextMessages)
    scrollToBottom()

    try {
      const response = await fetch('/api/demo-chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: userMessage, history: messages }),
      })

      if (!response.ok || !response.body) {
        throw new Error('Demo chat unavailable')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let assistantText = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const eventChunk of events) {
          const line = eventChunk.split('\n').find((l) => l.startsWith('data: '))
          if (!line) continue

          try {
            const data = JSON.parse(line.slice(6)) as { type?: string; text?: string; label?: string }

            if (data.type === 'tool') {
              setToolActivity(data.label?.includes('web') || data.label?.toLowerCase().includes('search')
                ? '🌐 Searching current web results...'
                : data.label || 'Working...')
            }

            if (data.type === 'text' && data.text) {
              assistantText += data.text
              setToolActivity(null)
              setMessages((prev) => {
                const updated = [...prev]
                updated[updated.length - 1] = { role: 'assistant', content: assistantText }
                return updated
              })
              scrollToBottom()
            }
          } catch {
            // Ignore malformed stream chunks
          }
        }
      }

      persistQuestionCount(Math.min(questionsUsed + 1, MAX_FREE_QUESTIONS))
    } catch {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = { role: 'assistant', content: DEMO_ERROR }
        return updated
      })
    } finally {
      setLoading(false)
      setToolActivity(null)
      scrollToBottom()
    }
  }

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white flex flex-col">
      <header className="border-b border-white/10 px-4 sm:px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <img src="/sparq-logo.jpg" alt="SPARQ" className="h-9 w-9 rounded-lg border border-white/10" />
            <div>
              <h1 className="text-lg sm:text-xl font-black">SPARQ AI Demo</h1>
              <p className="text-xs sm:text-sm text-sparq-lime">Try SPARQ AI - No sign-up required</p>
            </div>
          </div>
          <p className="text-xs sm:text-sm text-gray-400">{usageText}</p>
        </div>
      </header>

      <main className="flex-1 px-4 sm:px-6 py-5">
        <div className="max-w-5xl h-full mx-auto grid grid-rows-[1fr_auto] gap-4">
          <section className="border border-white/10 rounded-2xl bg-white/[0.03] overflow-y-auto p-4 sm:p-5">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col justify-center">
                <p className="text-sm sm:text-base text-gray-300 mb-4">Ask anything about recruiting and get a live AI answer.</p>
                <div className="flex flex-wrap gap-2">
                  {STARTER_PROMPTS.map((prompt) => (
                    <button
                      key={prompt}
                      type="button"
                      onClick={() => void sendMessage(prompt)}
                      disabled={gated || loading}
                      className="text-left px-3 py-2 rounded-full border border-white/10 bg-black/40 text-sm text-gray-200 hover:border-sparq-lime/40 disabled:opacity-50"
                    >
                      {prompt}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                {messages.map((msg, i) => {
                  const isLastAssistant = msg.role === 'assistant' && i === messages.length - 1
                  return (
                    <div key={`${msg.role}-${i}`} className={msg.role === 'user' ? 'flex justify-end' : 'flex justify-start'}>
                      <div
                        className={
                          msg.role === 'user'
                            ? 'max-w-[85%] rounded-2xl px-4 py-3 bg-sparq-lime text-sparq-charcoal font-semibold'
                            : 'max-w-[85%] rounded-2xl px-4 py-3 bg-white/[0.04] border border-white/10 text-gray-100'
                        }
                      >
                        {msg.role === 'assistant' ? (
                          <ReactMarkdown
                            components={{
                              p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                              ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2">{children}</ul>,
                              ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2">{children}</ol>,
                              a: ({ href, children }) => (
                                <a href={href} target="_blank" rel="noopener noreferrer" className="text-sparq-lime underline">
                                  {children}
                                </a>
                              ),
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        ) : (
                          msg.content
                        )}
                        {isLastAssistant && loading && !msg.content && (
                          <span className="text-gray-400 italic">{toolActivity || 'Thinking...'}</span>
                        )}
                        {isLastAssistant && loading && msg.content && (
                          <span className="inline-block w-2 h-4 ml-1 align-middle bg-sparq-lime/80 animate-pulse" />
                        )}
                      </div>
                    </div>
                  )
                })}
                {toolActivity && loading && (
                  <div className="text-xs text-sparq-lime">{toolActivity}</div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </section>

          <section className="space-y-3 pb-2">
            {gated && (
              <div className="rounded-xl border border-sparq-lime/30 bg-sparq-lime/10 p-4">
                <p className="text-sparq-lime font-semibold">You&apos;ve used your 3 free questions.</p>
                <p className="text-sm text-gray-200 mt-1">Create your profile to get answers personalized to YOUR stats and matches.</p>
                <Link
                  href="/onboarding/search"
                  className="inline-flex mt-3 bg-sparq-lime text-sparq-charcoal px-4 py-2 rounded-lg font-black"
                >
                  Get Started Free →
                </Link>
              </div>
            )}

            <div className="border border-white/10 rounded-xl bg-white/[0.02] p-3 flex gap-2">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={gated ? 'Free questions used. Start onboarding to continue.' : 'Ask SPARQ AI anything...'}
                rows={1}
                disabled={gated || loading}
                className="flex-1 resize-none rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm placeholder:text-gray-500 focus:outline-none focus:border-sparq-lime/50 disabled:opacity-50"
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && !event.shiftKey) {
                    event.preventDefault()
                    void sendMessage()
                  }
                }}
              />
              <button
                type="button"
                disabled={gated || loading || !input.trim()}
                onClick={() => void sendMessage()}
                className="shrink-0 px-4 py-2 rounded-lg bg-sparq-lime text-sparq-charcoal font-black disabled:opacity-40"
              >
                Send
              </button>
            </div>
          </section>
        </div>
      </main>
    </div>
  )
}
