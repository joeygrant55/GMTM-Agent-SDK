'use client'

import { useEffect, useRef, useState } from 'react'
import { useUser } from '@clerk/nextjs'
import ReactMarkdown from 'react-markdown'

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolActivity?: string
}

const STARTER_PROMPTS = [
  { emoji: '🎯', label: 'Which college should I contact first?', prompt: 'Looking at my college matches, which program should I reach out to first and why?' },
  { emoji: '✉️', label: 'Write a coach outreach email', prompt: 'Help me write a cold outreach email to send to coaches at my top match schools.' },
  { emoji: '📊', label: 'How does my profile compare?', prompt: 'How does my profile compare to typical recruits at my target division level? Where am I strong and where do I need to improve?' },
  { emoji: '🏋️', label: 'What do coaches look for?', prompt: 'What do college coaches specifically look for in an athlete at my position? What should I be highlighting in my recruiting process?' },
]

export default function WorkspaceAIPanel() {
  const { user, isLoaded } = useUser()
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        "Your recruiting AI is ready. I know your stats, your target schools, and how your profile stacks up — ask me anything, or start with one of these:",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [toolActivity, setToolActivity] = useState<string | null>(null)

  // Main session
  const mainConversationIdRef = useRef<number | null>(null)

  // Fork state
  const [forkScenario, setForkScenario] = useState<string | null>(null)
  const [forkConversationId, setForkConversationId] = useState<number | null>(null)
  const [showForkInput, setShowForkInput] = useState(false)
  const [forkInputText, setForkInputText] = useState('')
  const [forkLoading, setForkLoading] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)

  const hasUserMessages = messages.some(m => m.role === 'user')
  const hasUserMessagesRef = useRef(false)
  hasUserMessagesRef.current = hasUserMessages

  // Active conversation id: fork if active, else main
  const activeConversationId = forkConversationId ?? mainConversationIdRef.current

  useEffect(() => {
    if (isLoaded && user?.id) {
      const stored = localStorage.getItem(`sparq_conv_${user.id}`)
      if (stored) {
        mainConversationIdRef.current = parseInt(stored, 10)
      }
    }
  }, [isLoaded, user?.id])

  useEffect(() => {
    const handler = (e: Event) => {
      const { prompt } = (e as CustomEvent<{ prompt: string }>).detail
      if (!hasUserMessagesRef.current && prompt && isLoaded && user?.id) {
        void sendMessage(prompt)
      }
    }
    window.addEventListener('sparq:proactive-prompt', handler)
    return () => window.removeEventListener('sparq:proactive-prompt', handler)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isLoaded, user?.id])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL || 'https://focused-essence-production-9809.up.railway.app'

  const sendMessage = async (overrideText?: string) => {
    const userMessage = (overrideText ?? input).trim()
    if (!userMessage || loading || !user?.id) return

    setInput('')
    setLoading(true)
    setToolActivity(null)

    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setMessages((prev) => [...prev, { role: 'assistant', content: '', toolActivity: undefined }])

    const params = new URLSearchParams({
      athlete_id: user.id,
      message: userMessage,
      ...(activeConversationId ? { conversation_id: String(activeConversationId) } : {}),
      ...(forkScenario ? { fork_scenario: forkScenario } : {}),
    })

    try {
      const response = await fetch(`${backendUrl}/api/agent/stream?${params}`)
      if (!response.body) throw new Error('No response body')

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
            const data = JSON.parse(line.slice(6))

            if (data.type === 'session' && data.session_id) {
              if (!forkConversationId) {
                const cid = parseInt(data.session_id, 10)
                if (!isNaN(cid)) {
                  mainConversationIdRef.current = cid
                  localStorage.setItem(`sparq_conv_${user.id}`, String(cid))
                }
              }
            }

            if (data.type === 'tool') setToolActivity(data.label)

            if (data.type === 'text') {
              assistantText += data.text
              setToolActivity(null)
              setMessages((prev) => {
                const updated = [...prev]
                updated[updated.length - 1] = { role: 'assistant', content: assistantText }
                return updated
              })
            }

            if (data.type === 'done') setToolActivity(null)
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

  const startFork = async () => {
    const scenario = forkInputText.trim()
    if (!scenario || !user?.id) return
    setForkLoading(true)
    try {
      const res = await fetch(`${backendUrl}/api/agent/fork`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_id: user.id,
          scenario,
          parent_conversation_id: mainConversationIdRef.current,
        }),
      })
      const data = await res.json()
      if (data.session_id) {
        setForkConversationId(parseInt(data.session_id, 10))
        setForkScenario(data.fork_scenario)
        setForkInputText('')
        setShowForkInput(false)
        setMessages([{
          role: 'assistant',
          content: `I'm now looking at your recruiting through a different lens: **${data.fork_scenario}**\n\nAsk me anything — I'll factor in this scenario for every answer.`,
        }])
      }
    } catch {
      // silently fail
    } finally {
      setForkLoading(false)
    }
  }

  const exitFork = () => {
    setForkScenario(null)
    setForkConversationId(null)
    setShowForkInput(false)
    setForkInputText('')
    setMessages([{
      role: 'assistant',
      content: "Your recruiting AI is ready. I know your stats, your target schools, and how your profile stacks up — ask me anything, or start with one of these:",
    }])
  }

  return (
    <div className="border-l border-white/10 bg-sparq-charcoal flex flex-col w-[300px] shrink-0">
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-white text-sm">Recruiting AI ✨</h2>
          {!forkScenario && (
            <button
              onClick={() => setShowForkInput(!showForkInput)}
              className="text-xs text-gray-400 hover:text-sparq-lime transition-colors"
              title="Explore a What If scenario"
            >
              🔀 What if...
            </button>
          )}
          {forkScenario && (
            <button
              onClick={exitFork}
              className="text-xs text-gray-400 hover:text-red-400 transition-colors"
              title="Exit what-if mode"
            >
              ✕ Exit
            </button>
          )}
        </div>

        {showForkInput && !forkScenario && (
          <div className="mt-3 flex flex-col gap-2">
            <input
              type="text"
              className="w-full bg-white/[0.06] border border-white/10 rounded-lg px-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-sparq-lime/50"
              placeholder="e.g. I switched to tight end..."
              value={forkInputText}
              onChange={(e) => setForkInputText(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') void startFork() }}
              disabled={forkLoading}
              autoFocus
            />
            <button
              onClick={() => void startFork()}
              disabled={forkLoading || !forkInputText.trim()}
              className="w-full bg-sparq-lime/20 border border-sparq-lime/30 hover:bg-sparq-lime/30 text-sparq-lime text-xs font-semibold py-1.5 rounded-lg transition-colors disabled:opacity-40"
            >
              {forkLoading ? 'Starting...' : 'Explore scenario →'}
            </button>
          </div>
        )}
      </div>

      {forkScenario && (
        <div className="px-4 py-2 bg-sparq-lime/10 border-b border-sparq-lime/20 text-xs text-sparq-lime font-medium">
          🔀 What if: {forkScenario}
        </div>
      )}

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
                )
              ) : loading && i === messages.length - 1 ? (
                <span className="text-gray-500 italic">{toolActivity || 'Thinking...'}</span>
              ) : null}
            </div>

            {i === 0 && !hasUserMessages && !forkScenario && (
              <div className="mt-3 space-y-2">
                {STARTER_PROMPTS.map((sp) => (
                  <button
                    key={sp.prompt}
                    type="button"
                    disabled={loading}
                    onClick={() => void sendMessage(sp.prompt)}
                    className="w-full text-left px-3 py-2 rounded-lg border border-white/10 bg-white/[0.03] hover:bg-white/[0.07] hover:border-sparq-lime/30 transition-colors text-xs text-gray-300 flex items-center gap-2 disabled:opacity-40"
                  >
                    <span className="text-base leading-none shrink-0">{sp.emoji}</span>
                    <span>{sp.label}</span>
                  </button>
                ))}
              </div>
            )}
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
          placeholder={forkScenario ? 'Ask about this scenario...' : 'Ask your recruiting AI...'}
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
