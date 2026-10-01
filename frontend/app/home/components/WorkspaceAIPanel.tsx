'use client'

import { apiFetch } from '@/app/_lib/api'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useSparqSession } from '@/app/_lib/useSparqSession'
import ReactMarkdown from 'react-markdown'
import IterationBanner from './IterationBanner'
import { ARTIFACT_TYPE_LABEL, ArtifactType } from './artifactStatus'
import { useCombineHelp } from './CombineHelpProvider'
import CombineHelpPanel from './CombineHelpPanel'

interface Message {
  role: 'user' | 'assistant'
  content: string
  toolActivity?: string
}

interface ScopedArtifact {
  artifactId: number
  type: ArtifactType
  title: string | null
  agent_id: string | null
}

const STARTER_PROMPTS = [
  { emoji: '🎯', label: 'Which college should I contact first?', prompt: 'Looking at my college matches, which program should I reach out to first and why?' },
  { emoji: '✉️', label: 'Write a coach outreach email', prompt: 'Help me write a cold outreach email to send to coaches at my top match schools.' },
  { emoji: '📊', label: 'How does my profile compare?', prompt: 'How does my profile compare to typical recruits at my target division level? Where am I strong and where do I need to improve?' },
  { emoji: '🏋️', label: 'What do coaches look for?', prompt: 'What do college coaches specifically look for in an athlete at my position? What should I be highlighting in my recruiting process?' },
]

const ARTIFACT_QUICK_ITERATIONS: Partial<Record<ArtifactType, { emoji: string; label: string; prompt: string }[]>> = {
  outreach_draft: [
    { emoji: '✂️', label: 'Make it shorter', prompt: 'Cut this draft by ~20% — keep the personal opener and the ask, trim the bio.' },
    { emoji: '🎯', label: 'More personal opener', prompt: 'Rewrite the opener so it lands more personal — reference something specific about the program.' },
    { emoji: '🎓', label: 'Mention my GPA', prompt: 'Work my GPA into the body naturally without sounding like a brag.' },
    { emoji: '🏈', label: 'Cite their recent game', prompt: 'Add a sentence referencing a specific play or moment from their most recent game.' },
  ],
  research_brief: [
    { emoji: '🔍', label: 'What should I do first?', prompt: 'Based on this brief, what is the single most important next action for me?' },
    { emoji: '📊', label: 'How do I stack up?', prompt: 'How does my profile compare to athletes this program has recruited recently?' },
    { emoji: '📨', label: 'Draft outreach', prompt: 'Use this brief to draft an outreach email to the position coach.' },
    { emoji: '⚠️', label: 'What are the risks?', prompt: 'What concerns or red flags should I be aware of with this program?' },
  ],
  honest_assessment: [
    { emoji: '💬', label: 'Why this verdict?', prompt: 'Walk me through why you reached this verdict — what specific data drove it?' },
    { emoji: '🧭', label: 'Show me Plan B', prompt: 'Open up the Plan B pathways in detail — which schools, which divisions, why?' },
    { emoji: '📈', label: 'How do I improve?', prompt: 'Of these metrics, which one would move my odds most if I improved it by 10%?' },
    { emoji: '❓', label: 'I disagree', prompt: 'I think this assessment is too pessimistic — push back on me, but with data.' },
  ],
}

const WELCOME_MESSAGE = 'Your recruiting AI is ready. Ask about your profile, your next step, or a program you want to explore.'

export default function WorkspaceAIPanel() {
  const { user, isLoaded } = useSparqSession()
  const combineHelp = useCombineHelp()
  // Combine help never inherits recruiting conversation IDs, forks or artifact state.
  if (combineHelp?.enabled) return <CombineHelpPanel />
  if (!isLoaded || !user?.id) {
    return (
      <div role="status" className="border-l border-white/10 bg-sparq-charcoal w-[300px] shrink-0 p-4 text-sm text-gray-400">
        {isLoaded ? 'Sign in to use your recruiting AI.' : 'Loading your account…'}
      </div>
    )
  }
  // Remount all owner-bound state before rendering a different account's panel.
  return <WorkspaceAISession key={user.id} ownerId={user.id} />
}

function WorkspaceAISession({ ownerId }: { ownerId: string }) {
  const router = useRouter()
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: WELCOME_MESSAGE,
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

  // Mode B — artifact-scoped iteration. When set, chat sends iteration intent against this artifact.
  const [scopedArtifact, setScopedArtifact] = useState<ScopedArtifact | null>(null)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const mountedRef = useRef(true)
  const requestRef = useRef<AbortController | null>(null)
  const sendMessageRef = useRef<(text: string) => Promise<void>>(async () => {})

  const hasUserMessages = messages.some(m => m.role === 'user')
  const hasUserMessagesRef = useRef(false)
  hasUserMessagesRef.current = hasUserMessages

  useEffect(() => {
    mountedRef.current = true
    try {
      const stored = Number(localStorage.getItem(`sparq_conv_${ownerId}`))
      mainConversationIdRef.current = Number.isSafeInteger(stored) && stored > 0 ? stored : null
    } catch {
      mainConversationIdRef.current = null
    }
    return () => {
      mountedRef.current = false
      requestRef.current?.abort()
      requestRef.current = null
    }
  }, [ownerId])

  const stopRequest = useCallback(() => {
    requestRef.current?.abort()
    requestRef.current = null
    setLoading(false)
    setForkLoading(false)
    setToolActivity(null)
  }, [])

  useEffect(() => {
    const handler = (e: Event) => {
      const prompt = (e as CustomEvent<{ prompt?: string }>).detail?.prompt
      if (!hasUserMessagesRef.current && prompt) {
        void sendMessageRef.current(prompt)
      }
    }
    window.addEventListener('sparq:proactive-prompt', handler)
    return () => window.removeEventListener('sparq:proactive-prompt', handler)
  }, [])

  // Mode B wiring — ArtifactViewer fires these when an artifact opens / closes.
  useEffect(() => {
    const onOpen = (e: Event) => {
      const detail = (e as CustomEvent<ScopedArtifact>).detail
      if (!detail?.artifactId) return
      stopRequest()
      setForkScenario(null)
      setForkConversationId(null)
      setShowForkInput(false)
      setForkInputText('')
      setScopedArtifact(detail)
      // Reset chat history so iterations stay scoped to the open artifact.
      const typeLabel = ARTIFACT_TYPE_LABEL[detail.type] ?? 'this artifact'
      setMessages([
        {
          role: 'assistant',
          content: `I'm scoped to your **${typeLabel}**${detail.title ? ` — *${detail.title}*` : ''}. Tell me how to iterate it, or pick a quick action below.`,
        },
      ])
    }
    const onClose = () => {
      stopRequest()
      setScopedArtifact(null)
      setMessages([
        {
          role: 'assistant',
          content: WELCOME_MESSAGE,
        },
      ])
    }
    window.addEventListener('sparq:artifact-opened', onOpen)
    window.addEventListener('sparq:artifact-closed', onClose)
    return () => {
      window.removeEventListener('sparq:artifact-opened', onOpen)
      window.removeEventListener('sparq:artifact-closed', onClose)
    }
  }, [stopRequest])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const backendUrl =
    process.env.NEXT_PUBLIC_BACKEND_URL || 'https://focused-essence-production-9809.up.railway.app'

  const sendMessage = async (overrideText?: string) => {
    const userMessage = (overrideText ?? input).trim()
    if (!userMessage || requestRef.current || !mountedRef.current) return

    const request = new AbortController()
    requestRef.current = request
    const isCurrent = () => mountedRef.current && requestRef.current === request && !request.signal.aborted

    setInput('')
    setLoading(true)
    setToolActivity(null)

    setMessages((prev) => [...prev, { role: 'user', content: userMessage }])
    setMessages((prev) => [...prev, { role: 'assistant', content: '', toolActivity: undefined }])

    // Mode B — artifact-scoped iteration. Hits the iterate-via-agent endpoint instead of the chat stream.
    if (scopedArtifact) {
      setToolActivity('Rewriting your draft…')
      try {
        const res = await apiFetch(
          `${backendUrl}/api/artifacts/${scopedArtifact.artifactId}/iterate-via-agent`,
          {
            method: 'POST',
            signal: request.signal,
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruction: userMessage, performed_by: ownerId }),
          }
        )
        const data = await res.json()
        if (!isCurrent()) return
        if (!res.ok || !data?.child_id) {
          throw new Error(data?.detail || 'Iteration failed')
        }
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: 'assistant',
            content: data.explanation || 'Updated.',
          }
          return updated
        })
        // Tell the open ArtifactViewer to navigate to the new revision.
        window.dispatchEvent(
          new CustomEvent('sparq:artifact-updated', {
            detail: { artifactId: scopedArtifact.artifactId, childId: data.child_id },
          })
        )
      } catch (err) {
        if (!isCurrent()) return
        setMessages((prev) => {
          const updated = [...prev]
          updated[updated.length - 1] = {
            role: 'assistant',
            content: "I couldn't rewrite that — try again, or rephrase.",
          }
          return updated
        })
      } finally {
        if (isCurrent()) {
          requestRef.current = null
          setLoading(false)
          setToolActivity(null)
        }
      }
      return
    }

    const activeConversationId = forkConversationId ?? mainConversationIdRef.current
    const params = new URLSearchParams({
      athlete_id: ownerId,
      message: userMessage,
      ...(activeConversationId ? { conversation_id: String(activeConversationId) } : {}),
      ...(forkScenario ? { fork_scenario: forkScenario } : {}),
    })

    try {
      const response = await apiFetch(`${backendUrl}/api/agent/stream?${params}`, { signal: request.signal })
      if (!isCurrent()) return
      if (!response.ok || !response.body) throw new Error('Chat request failed')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let assistantText = ''
      let buffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (!isCurrent()) return
        if (done) break

        buffer += decoder.decode(value, { stream: true })
        const events = buffer.split('\n\n')
        buffer = events.pop() || ''

        for (const eventChunk of events) {
          const line = eventChunk.split('\n').find((l) => l.startsWith('data: '))
          if (!line) continue

          let data
          try {
            data = JSON.parse(line.slice(6))
          } catch {
            continue // Skip malformed chunks without hiding an explicit error event.
          }
          if (data.type === 'error') throw new Error('Chat generation failed')

          if (data.type === 'session' && data.session_id) {
            if (!forkConversationId) {
              const cid = Number(data.session_id)
              if (Number.isSafeInteger(cid) && cid > 0) {
                mainConversationIdRef.current = cid
                try {
                  localStorage.setItem(`sparq_conv_${ownerId}`, String(cid))
                } catch {
                  // Conversation still works when browser storage is unavailable.
                }
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
        }
      }
      if (!assistantText) throw new Error('No chat response received')
    } catch {
      if (!isCurrent()) return
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: "I'm having trouble connecting right now. Please try again in a moment.",
        }
        return updated
      })
    } finally {
      if (isCurrent()) {
        requestRef.current = null
        setLoading(false)
        setToolActivity(null)
      }
    }
  }

  useEffect(() => {
    sendMessageRef.current = sendMessage
  })

  const startFork = async () => {
    const scenario = forkInputText.trim()
    if (!scenario || requestRef.current || !mountedRef.current) return
    const request = new AbortController()
    requestRef.current = request
    const isCurrent = () => mountedRef.current && requestRef.current === request && !request.signal.aborted
    setForkLoading(true)
    try {
      const res = await apiFetch(`${backendUrl}/api/agent/fork`, {
        method: 'POST',
        signal: request.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_id: ownerId,
          scenario,
          parent_conversation_id: mainConversationIdRef.current,
        }),
      })
      const data = await res.json()
      if (!isCurrent()) return
      const sessionId = Number(data.session_id)
      if (res.ok && Number.isSafeInteger(sessionId) && sessionId > 0) {
        setForkConversationId(sessionId)
        setForkScenario(data.fork_scenario)
        setForkInputText('')
        setShowForkInput(false)
        setMessages([{
          role: 'assistant',
          content: `I'm now looking at your recruiting through a different lens: **${data.fork_scenario}**\n\nAsk me anything — I'll factor in this scenario for every answer.`,
        }])
      } else throw new Error('Could not start scenario')
    } catch {
      if (isCurrent()) setMessages(prev => [...prev, { role: 'assistant', content: 'I could not start that scenario. Please try again.' }])
    } finally {
      if (isCurrent()) {
        requestRef.current = null
        setForkLoading(false)
      }
    }
  }

  const exitFork = () => {
    stopRequest()
    setForkScenario(null)
    setForkConversationId(null)
    setShowForkInput(false)
    setForkInputText('')
    setMessages([{
      role: 'assistant',
      content: WELCOME_MESSAGE,
    }])
  }

  return (
    <div className="border-l border-white/10 bg-sparq-charcoal flex flex-col w-[300px] shrink-0">
      <div className="p-4 border-b border-white/10">
        <div className="flex items-center justify-between">
          <h2 className="font-bold text-white text-sm">Recruiting AI ✨</h2>
          {!forkScenario && !scopedArtifact && (
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

        {showForkInput && !forkScenario && !scopedArtifact && (
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
              disabled={loading || forkLoading || !forkInputText.trim()}
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

      {scopedArtifact && (
        <IterationBanner
          artifact={{
            id: scopedArtifact.artifactId,
            type: scopedArtifact.type,
            title: scopedArtifact.title,
            agent_id: scopedArtifact.agent_id as never,
          }}
          onExit={() => router.push('/home/inbox')}
        />
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
                {(scopedArtifact
                  ? ARTIFACT_QUICK_ITERATIONS[scopedArtifact.type] ?? STARTER_PROMPTS
                  : STARTER_PROMPTS
                ).map((sp) => (
                  <button
                    key={sp.prompt}
                    type="button"
                    disabled={loading || forkLoading}
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
          placeholder={
            scopedArtifact
              ? 'Tell me how to iterate this draft…'
              : forkScenario
              ? 'Ask about this scenario...'
              : 'Ask your recruiting AI...'
          }
          rows={1}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void sendMessage()
            }
          }}
          disabled={loading || forkLoading}
        />
        <button
          onClick={() => void sendMessage()}
          disabled={loading || forkLoading || !input.trim()}
          className="bg-sparq-lime text-sparq-charcoal font-black px-3 py-2 rounded-lg text-sm disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >
          Send
        </button>
      </div>
    </div>
  )
}
