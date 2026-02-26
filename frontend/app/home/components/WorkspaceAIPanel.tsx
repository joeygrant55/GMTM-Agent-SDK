'use client'

import { useEffect, useRef, useState } from 'react'
import { useUser } from '@clerk/nextjs'
import ReactMarkdown from 'react-markdown'

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolActivity?: string
}

export default function WorkspaceAIPanel() {
  const { user, isLoaded } = useUser()
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Hey! I am your recruiting AI. I can help you find college matches, research programs, draft coach emails, and analyze your profile. What are you working on?',
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [toolActivity, setToolActivity] = useState<string | null>(null)
  const sessionIdRef = useRef<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (isLoaded && user?.id) {
      const stored = localStorage.getItem(`sparq_session_${user.id}`)
      if (stored) {
        sessionIdRef.current = stored
      }
    }
  }, [isLoaded, user?.id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async () => {
    if (!input.trim() || loading || !user?.id) {
      return
    }

    const userMessage = input.trim()
    setInput('')
    setLoading(true)
    setToolActivity(null)

    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setMessages((prev) => [...prev, { role: 'assistant', content: '', toolActivity: undefined }])

    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL || 'https://focused-essence-production-9809.up.railway.app'
    const params = new URLSearchParams({
      athlete_id: user.id,
      message: userMessage,
      ...(sessionIdRef.current ? { session_id: sessionIdRef.current } : {}),
    })

    try {
      const response = await fetch(`${backendUrl}/api/agent/stream?${params}`)
      if (!response.body) {
        throw new Error('No response body')
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let assistantText = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) {
          break
        }

        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const eventChunk of events) {
          const line = eventChunk
            .split('\n')
            .find((l) => l.startsWith('data: '))
          if (!line) {
            continue
          }

          try {
            const data = JSON.parse(line.slice(6))

            if (data.type === 'session' && data.session_id) {
              sessionIdRef.current = data.session_id
              localStorage.setItem(`sparq_session_${user.id}`, data.session_id)
            }

            if (data.type === 'tool') {
              setToolActivity(data.label)
            }

            if (data.type === 'text') {
              assistantText += data.text
              setToolActivity(null)
              setMessages((prev) => {
                const updated = [...prev]
                updated[updated.length - 1] = { role: 'assistant', content: assistantText }
                return updated
              })
            }

            if (data.type === 'done') {
              setToolActivity(null)
            }
          } catch {
            // Skip malformed chunks
          }
        }
      }
    } catch {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: "I'm having trouble connecting right now. Please try again in a moment.",
        }
        return updated
      })
    } finally {
      setLoading(false)
      setToolActivity(null)
    }
  }

  return (
    <div className="border-l border-white/10 bg-sparq-charcoal flex flex-col w-[300px] shrink-0">
      <div className="p-4 border-b border-white/10">
        <h2 className="font-bold text-white text-sm">Recruiting AI ✨</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((msg, i) => (
          <div key={i} className={msg.role === 'user' ? 'ml-4' : 'mr-4'}>
            <div
              className={
                msg.role === 'user'
                  ? 'bg-sparq-lime/10 border border-sparq-lime/20 rounded-xl p-3 text-sm text-white'
                  : 'bg-white/[0.04] border border-white/10 rounded-xl p-3 text-sm text-gray-200'
              }
            >
              {msg.content ? (
                msg.role === 'assistant' ? (
                  <ReactMarkdown
                    components={{
                      p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                      strong: ({ children }) => <strong className="font-bold text-white">{children}</strong>,
                      em: ({ children }) => <em className="italic text-gray-300">{children}</em>,
                      h3: ({ children }) => <h3 className="font-bold text-white mt-3 mb-1">{children}</h3>,
                      ul: ({ children }) => <ul className="list-disc list-inside space-y-1 my-2">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 my-2">{children}</ol>,
                      li: ({ children }) => <li className="text-gray-200">{children}</li>,
                      hr: () => <hr className="border-white/10 my-2" />,
                      a: ({ href, children }) => <a href={href} target="_blank" rel="noopener noreferrer" className="text-sparq-lime underline">{children}</a>,
                    }}
                  >
                    {msg.content}
                  </ReactMarkdown>
                ) : (
                  msg.content
                )
              ) : (
                loading && i === messages.length - 1 ? (
                  <span className="text-gray-500 italic">{toolActivity || 'Thinking...'}</span>
                ) : null
              )}
            </div>
          </div>
        ))}
        {toolActivity && loading && (
          <div className="mr-4">
            <div className="bg-white/[0.04] border border-white/10 rounded-xl p-3 text-sm text-gray-400 italic">
              {toolActivity}
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="p-4 border-t border-white/10 flex gap-2">
        <textarea
          className="flex-1 bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-sparq-lime/50"
          placeholder="Ask your recruiting AI..."
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void sendMessage()
            }
          }}
          disabled={loading || !isLoaded}
        />
        <button
          onClick={() => void sendMessage()}
          disabled={loading || !input.trim() || !isLoaded}
          className="bg-sparq-lime text-sparq-charcoal font-black px-3 py-2 rounded-lg text-sm disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >
          Send
        </button>
      </div>
    </div>
  )
}
