'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import ResponseParser from './ResponseParser'

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  thinking?: boolean
  streaming?: boolean
  thinkingSteps?: string[]
  toolsUsed?: string[]
  agentSteps?: string[]
  structured?: any
}

interface AgentChatProps {
  athleteId: string
  athleteName: string
  initialConversationId?: number | null
}

// Tool name → friendly description
const TOOL_DESCRIPTIONS: Record<string, { text: string; icon: string }> = {
  college_matcher: { text: 'Matching against college programs...', icon: '🎯' },
  profile_analyzer: { text: 'Analyzing athletic profile...', icon: '📊' },
  coach_lookup: { text: 'Researching coaching staffs...', icon: '🏈' },
  camp_finder: { text: 'Finding camps and combines...', icon: '🏕️' },
  calendar_check: { text: 'Checking recruiting calendar...', icon: '📅' },
  film_guide: { text: 'Reviewing film resources...', icon: '🎬' },
  brave_search: { text: 'Searching the web...', icon: '🔍' },
  fetch_metrics: { text: 'Loading performance metrics...', icon: '⚡' },
  scholarship_check: { text: 'Evaluating scholarship likelihood...', icon: '🎓' },
}

const getToolInfo = (toolName: string) =>
  TOOL_DESCRIPTIONS[toolName] || { text: `Running ${toolName.replace(/_/g, ' ')}...`, icon: '⚙️' }

// Quick action cards
const QUICK_ACTIONS = [
  {
    icon: '🎯',
    title: 'Find My Colleges',
    desc: 'Get matched to programs that fit you',
    prompt: 'What college programs are the best fit for me?',
  },
  {
    icon: '✉️',
    title: 'Email a Coach',
    desc: 'Draft a personalized intro email',
    prompt: 'Help me write an introduction email to a college coach',
  },
  {
    icon: '📊',
    title: 'Analyze My Profile',
    desc: 'See how your metrics stack up',
    prompt: 'How do my metrics compare to other athletes at my position?',
  },
  {
    icon: '🏕️',
    title: 'Find Camps',
    desc: 'Camps & combines near you',
    prompt: 'Find camps near me',
  },
]

// Inline "What's next?" suggestions (smaller, horizontal)
const FOLLOWUP_ACTIONS = [
  { icon: '🎯', label: 'Find colleges', prompt: 'What college programs are the best fit for me?' },
  { icon: '✉️', label: 'Email a coach', prompt: 'Help me write an introduction email to a college coach' },
  { icon: '📊', label: 'Analyze profile', prompt: 'How do my metrics compare to other athletes at my position?' },
  { icon: '🏕️', label: 'Find camps', prompt: 'Find camps near me' },
]

export default function AgentChat({ athleteId, athleteName, initialConversationId }: AgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `What's up ${athleteName.split(' ')[0]}! 👋 I'm your SPARQ recruiting agent — here to help you find the right programs, connect with coaches, and level up your recruiting game.\n\nWhat do you want to work on?`,
      timestamp: new Date(),
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [conversations, setConversations] = useState<any[]>([])
  const [showSidebar, setShowSidebar] = useState(false)
  const [copiedIdx, setCopiedIdx] = useState<number | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

  useEffect(() => {
    fetch(`${backendUrl}/api/conversations/${athleteId}`)
      .then((r) => r.json())
      .then((data) => setConversations(data.conversations || []))
      .catch(() => {})
    if (initialConversationId) {
      loadConversation(initialConversationId)
    }
  }, [athleteId, initialConversationId])

  const loadConversation = async (convId: number) => {
    try {
      const res = await fetch(`${backendUrl}/api/conversations/${athleteId}/${convId}`)
      const data = await res.json()
      setConversationId(convId)
      const loaded: Message[] = data.messages.map((m: any) => ({
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at),
        toolsUsed: m.tools_used
          ? typeof m.tools_used === 'string'
            ? JSON.parse(m.tools_used)
            : m.tools_used
          : [],
        agentSteps: m.agent_steps
          ? typeof m.agent_steps === 'string'
            ? JSON.parse(m.agent_steps)
            : m.agent_steps
          : [],
      }))
      setMessages(loaded)
      setShowSidebar(false)
    } catch (e) {}
  }

  const newConversation = () => {
    setConversationId(null)
    setMessages([
      {
        role: 'assistant',
        content: `What's up ${athleteName.split(' ')[0]}! 👋 I'm your SPARQ recruiting agent — here to help you find the right programs, connect with coaches, and level up your recruiting game.\n\nWhat do you want to work on?`,
        timestamp: new Date(),
      },
    ])
    setShowSidebar(false)
  }

  const formatMessageContent = (content: string) => {
    const lines = content.split('\n')
    let html = ''
    let inTable = false
    let tableHeaders: string[] = []
    let tableRows: string[][] = []

    const formatInline = (text: string) => {
      return text
        .replace(/\*\*([^*]+)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
        .replace(
          /(https?:\/\/[^\s<]+)/g,
          '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-[#c8ff00] hover:underline">$1</a>'
        )
    }

    const flushTable = () => {
      if (tableHeaders.length === 0) return ''
      let t =
        '<div class="overflow-x-auto my-3 rounded-lg border border-white/[0.06]"><table class="min-w-full text-sm">'
      t += '<thead class="bg-[#1a1a1a]"><tr>'
      tableHeaders.forEach((h) => {
        t += `<th class="px-3 py-2 text-left font-semibold text-[#c8ff00] border-b border-white/[0.06]">${formatInline(h)}</th>`
      })
      t += '</tr></thead><tbody>'
      tableRows.forEach((row, idx) => {
        const bg = idx % 2 === 0 ? 'bg-[#141414]' : 'bg-[#1a1a1a]'
        t += `<tr class="${bg}">`
        row.forEach((cell) => {
          t += `<td class="px-3 py-2 border-b border-white/[0.04] text-white/[0.75]">${formatInline(cell)}</td>`
        })
        t += '</tr>'
      })
      t += '</tbody></table></div>'
      tableHeaders = []
      tableRows = []
      inTable = false
      return t
    }

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      const trimmed = line.trim()

      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        const cells = trimmed
          .slice(1, -1)
          .split('|')
          .map((c) => c.trim())
        if (cells.every((c) => /^[-:\s]+$/.test(c))) {
          inTable = true
          continue
        }
        if (!inTable && tableHeaders.length === 0) {
          tableHeaders = cells
          continue
        }
        if (inTable) {
          tableRows.push(cells)
          continue
        }
      } else {
        if (inTable || tableHeaders.length > 0) {
          html += flushTable()
        }
      }

      if (trimmed.startsWith('#### ')) {
        html += `<h5 class="font-semibold text-white/90 mt-3 mb-1 text-sm">${formatInline(trimmed.slice(5))}</h5>`
      } else if (trimmed.startsWith('### ')) {
        html += `<h4 class="font-semibold text-white mt-4 mb-2 font-display">${formatInline(trimmed.slice(4))}</h4>`
      } else if (trimmed.startsWith('## ')) {
        html += `<h3 class="font-bold text-white mt-4 mb-2 text-lg font-display">${formatInline(trimmed.slice(3))}</h3>`
      } else if (trimmed.startsWith('# ')) {
        html += `<h2 class="font-bold text-white mt-4 mb-2 text-xl font-display">${formatInline(trimmed.slice(2))}</h2>`
      } else if (trimmed === '---') {
        html += '<hr class="my-3 border-white/[0.06]">'
      } else if (trimmed.startsWith('- ')) {
        html += `<div class="flex gap-2 ml-2 my-0.5"><span class="text-[#c8ff00]">•</span><span class="text-white/[0.85]">${formatInline(trimmed.slice(2))}</span></div>`
      } else if (trimmed === '') {
        html += '<div class="h-2"></div>'
      } else {
        html += `<p class="my-1 text-white/[0.85]">${formatInline(trimmed)}</p>`
      }
    }

    if (inTable || tableHeaders.length > 0) {
      html += flushTable()
    }

    return html
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Auto-resize textarea
  const autoResize = useCallback(() => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 120) + 'px'
  }, [])

  const sendMessage = async (overrideInput?: string) => {
    const text = overrideInput || input
    if (!text.trim() || loading) return

    const userMessage: Message = {
      role: 'user',
      content: text,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMessage])
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setLoading(true)

    const streamingMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      thinking: true,
      agentSteps: [],
      toolsUsed: [],
    }
    setMessages((prev) => [...prev, streamingMessage])

    try {
      const response = await fetch(`${backendUrl}/api/agent/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_id: athleteId,
          message: text,
          conversation_id: conversationId,
          conversation_history: conversationId ? [] : messages.slice(-5),
        }),
      })

      if (!response.ok) throw new Error('Failed to connect to agent')

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No response stream')

      const decoder = new TextDecoder()
      let buffer = ''
      let streamedText = ''
      let steps: string[] = []
      let toolsUsed: string[] = []

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let eventType = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const data = line.slice(6)

            if (eventType === 'conversation_id') {
              const cid = parseInt(data)
              if (cid && !conversationId) {
                setConversationId(cid)
                fetch(`${backendUrl}/api/conversations/${athleteId}`)
                  .then((r) => r.json())
                  .then((d) => setConversations(d.conversations || []))
                  .catch(() => {})
              }
            } else if (eventType === 'status') {
              setMessages((prev) => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                if (last?.thinking) {
                  updated[updated.length - 1] = { ...last, content: data, agentSteps: [...steps] }
                }
                return updated
              })
            } else if (eventType === 'tool_start') {
              try {
                const toolData = JSON.parse(data)
                steps.push(`tool_start:${toolData.tool}`)
                toolsUsed.push(toolData.tool)
                setMessages((prev) => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last?.thinking) {
                    updated[updated.length - 1] = {
                      ...last,
                      content: 'Researching...',
                      agentSteps: [...steps],
                      toolsUsed: [...toolsUsed],
                    }
                  }
                  return updated
                })
              } catch {}
            } else if (eventType === 'tool_done') {
              try {
                const toolData = JSON.parse(data)
                steps.push(`tool_done:${toolData.tool}`)
                setMessages((prev) => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last?.thinking) {
                    updated[updated.length - 1] = { ...last, agentSteps: [...steps], toolsUsed: [...toolsUsed] }
                  }
                  return updated
                })
              } catch {}
            } else if (eventType === 'text') {
              streamedText += data.replace(/\\n/g, '\n')
              setMessages((prev) => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                updated[updated.length - 1] = {
                  ...last,
                  content: streamedText,
                  thinking: false,
                  streaming: true,
                  agentSteps: [...steps],
                  toolsUsed: [...toolsUsed],
                }
                return updated
              })
            } else if (eventType === 'error') {
              setMessages((prev) => {
                const updated = [...prev]
                updated[updated.length - 1] = {
                  role: 'assistant',
                  content: `Something went wrong: ${data}. Try again?`,
                  timestamp: new Date(),
                  thinking: false,
                }
                return updated
              })
            }
            eventType = ''
          }
        }
      }

      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: streamedText || 'Done! What else can I help with?',
          timestamp: new Date(),
          thinking: false,
          streaming: false,
          toolsUsed,
          agentSteps: steps,
        }
        return updated
      })
    } catch (error: any) {
      setMessages((prev) => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `Sorry, something went wrong: ${error.message}. Try again?`,
          timestamp: new Date(),
        }
        return updated
      })
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const copyToClipboard = (text: string, idx: number) => {
    navigator.clipboard.writeText(text)
    setCopiedIdx(idx)
    setTimeout(() => setCopiedIdx(null), 2000)
  }

  // Determine if we should show the big action grid
  const showActionGrid = messages.length <= 1
  // Show inline followups after last assistant message (when not loading)
  const lastMsg = messages[messages.length - 1]
  const showFollowups = !loading && !showActionGrid && lastMsg?.role === 'assistant' && !lastMsg.thinking && !lastMsg.streaming

  // Parse agentSteps into timeline items for thinking display
  const parseSteps = (steps: string[]) => {
    const timeline: { tool: string; status: 'active' | 'done'; text: string; icon: string }[] = []
    const toolStatus: Record<string, 'active' | 'done'> = {}

    for (const step of steps) {
      if (step.startsWith('tool_start:')) {
        const tool = step.replace('tool_start:', '')
        toolStatus[tool] = 'active'
        const info = getToolInfo(tool)
        timeline.push({ tool, status: 'active', text: info.text, icon: info.icon })
      } else if (step.startsWith('tool_done:')) {
        const tool = step.replace('tool_done:', '')
        toolStatus[tool] = 'done'
        // Update existing entry
        const existing = timeline.find((t) => t.tool === tool && t.status === 'active')
        if (existing) existing.status = 'done'
      }
    }
    return timeline
  }

  return (
    <div className="bg-[#0a0a0a] rounded-2xl border border-white/[0.06] flex flex-col h-[calc(100dvh-10rem)] md:h-[700px] relative overflow-hidden">
      {/* Conversation Sidebar */}
      {showSidebar && (
        <div className="fixed inset-0 z-30 md:absolute md:inset-0 md:z-20 flex">
          <div className="w-full max-w-sm md:w-72 bg-[#0a0a0a] border-r border-white/[0.06] flex flex-col h-full md:rounded-l-2xl">
            <div className="p-4 md:p-3 border-b border-white/[0.06] flex items-center justify-between">
              <h4 className="font-semibold text-white font-display">Your Conversations</h4>
              <button
                onClick={() => setShowSidebar(false)}
                className="p-2 -mr-2 text-white/40 hover:text-white/70 text-xl"
              >
                ✕
              </button>
            </div>
            <div className="p-3 md:p-2">
              <button
                onClick={newConversation}
                className="w-full px-4 py-3 md:px-3 md:py-2 bg-[#c8ff00] text-[#0a0a0a] font-semibold rounded-lg hover:bg-[#d4ff33] transition-colors"
              >
                + New Chat
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-3 md:px-2 pb-3 md:pb-2">
              {conversations.length === 0 ? (
                <p className="text-white/30 text-center py-6 md:py-4 text-sm">No saved chats yet</p>
              ) : (
                conversations.map((conv) => (
                  <button
                    key={conv.id}
                    onClick={() => loadConversation(conv.id)}
                    className={`w-full text-left px-4 py-3 md:px-3 md:py-2 rounded-lg mb-2 md:mb-1 transition-colors ${
                      conversationId === conv.id
                        ? 'bg-[#c8ff00]/15 text-[#c8ff00] font-medium'
                        : 'hover:bg-white/[0.04] text-white/70'
                    }`}
                  >
                    <div className="font-medium truncate text-sm">{conv.title}</div>
                    <div className="text-xs text-white/30 mt-1 md:mt-0.5">
                      {conv.message_count} messages •{' '}
                      {new Date(conv.updated_at).toLocaleDateString()}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
          <div className="flex-1 bg-black/50" onClick={() => setShowSidebar(false)} />
        </div>
      )}

      {/* Header */}
      <div className="border-b border-white/[0.06] px-3 py-2.5 md:px-4 md:py-3 bg-[#0a0a0a]">
        <div className="flex items-center gap-2 md:gap-3">
          <button
            onClick={() => setShowSidebar(!showSidebar)}
            className="p-2 -ml-2 text-white/40 hover:text-white/70"
            title="Chat history"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
          {/* SPARQ Logo */}
          <div className="w-8 h-8 rounded-full bg-[#141414] border border-white/[0.06] flex items-center justify-center flex-shrink-0">
            <span className="text-[#c8ff00] font-bold text-xs font-display">S</span>
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <h3 className="font-semibold text-white text-sm md:text-base font-display">SPARQ Agent</h3>
              <span className="w-2 h-2 rounded-full bg-[#c8ff00] animate-pulse" />
            </div>
            <p className="text-xs text-white/40 truncate">Your AI recruiting coordinator</p>
          </div>
          <button
            onClick={newConversation}
            className="text-xs px-3 py-1.5 bg-white/[0.06] text-white/60 rounded-lg hover:bg-white/[0.1] hover:text-white/80 transition-colors"
          >
            + New
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-3 md:p-4 space-y-3 md:space-y-4">
        {messages.map((message, idx) => (
          <div key={idx} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[90%] md:max-w-[85%] ${message.role === 'user' ? '' : 'w-full'}`}>
              {message.role === 'user' ? (
                /* User message — dark card with lime left border */
                <div className="bg-[#141414] border-l-2 border-[#c8ff00] rounded-lg p-3">
                  <div className="whitespace-pre-wrap text-white/[0.9] text-sm">{message.content}</div>
                  <div className="text-[10px] mt-1.5 text-white/25">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              ) : message.thinking ? (
                /* Theatrical thinking / progress tracker */
                <ThinkingCard steps={message.agentSteps || []} parseSteps={parseSteps} />
              ) : (
                /* Assistant response */
                <div className="bg-[#141414] rounded-xl border border-white/[0.06]">
                  {/* Agent steps collapsed */}
                  {message.agentSteps && message.agentSteps.length > 0 && (
                    <div className="px-4 pt-3 pb-2 border-b border-white/[0.04]">
                      <div className="flex items-center gap-2 flex-wrap">
                        {(message.toolsUsed || [])
                          .filter((v, i, a) => a.indexOf(v) === i)
                          .map((tool, tidx) => {
                            const info = getToolInfo(tool)
                            return (
                              <span
                                key={tidx}
                                className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/[0.04] text-[10px] text-white/40"
                              >
                                <span>{info.icon}</span>
                                {tool.replace(/_/g, ' ')}
                              </span>
                            )
                          })}
                      </div>
                    </div>
                  )}

                  {/* Main content */}
                  <div className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-5 h-5 rounded-full bg-[#c8ff00]/10 flex items-center justify-center">
                        <span className="text-[#c8ff00] text-[10px] font-bold font-display">S</span>
                      </div>
                      <span className="text-xs font-medium text-white/50">SPARQ Agent</span>
                    </div>

                    {/* Structured data (camp cards) */}
                    {message.structured?.camps && (
                      <div className="space-y-3 mb-4">
                        {message.structured.camps.map((camp: any, cidx: number) => (
                          <div
                            key={cidx}
                            className="border border-white/[0.06] rounded-lg p-4 hover:border-[#c8ff00]/30 transition-all bg-white/[0.02]"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                <h4 className="font-semibold text-white mb-1">{camp.name}</h4>
                              </div>
                              {camp.url && (
                                <a
                                  href={camp.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="px-3 py-1.5 bg-[#c8ff00] text-[#0a0a0a] text-xs font-semibold rounded-lg hover:bg-[#d4ff33] transition-colors whitespace-nowrap"
                                >
                                  Learn More →
                                </a>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Main text content */}
                    <div className="text-sm leading-relaxed">
                      {message.streaming ? (
                        <div className="whitespace-pre-wrap text-white/[0.85]">
                          {message.content}
                          <span className="inline-block w-1.5 h-4 bg-[#c8ff00] animate-pulse ml-0.5 -mb-0.5 rounded-sm" />
                        </div>
                      ) : (
                        <ResponseParser
                          content={message.content}
                          onAction={(text) => sendMessage(text)}
                        />
                      )}
                    </div>

                    {/* Footer: timestamp + actions */}
                    <div className="flex items-center justify-between mt-3 pt-2 border-t border-white/[0.04]">
                      <div className="text-[10px] text-white/20">
                        {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </div>
                      {message.content.length > 200 && (
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => copyToClipboard(message.content, idx)}
                            className="text-[10px] text-white/25 hover:text-white/50 transition-colors flex items-center gap-1"
                          >
                            {copiedIdx === idx ? (
                              <>
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                </svg>
                                Copied
                              </>
                            ) : (
                              <>
                                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                  <path
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                    strokeWidth={2}
                                    d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                                  />
                                </svg>
                                Copy
                              </>
                            )}
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}

        {/* Inline followups — horizontal scroll */}
        {showFollowups && (
          <div className="pt-2">
            <p className="text-[10px] uppercase tracking-wider text-white/20 mb-2 ml-1">What&apos;s next?</p>
            <div className="flex gap-2 overflow-x-auto pb-1 -mx-3 px-3 md:mx-0 md:px-0">
              {FOLLOWUP_ACTIONS.map((action, aidx) => (
                <button
                  key={aidx}
                  onClick={() => sendMessage(action.prompt)}
                  className="flex-shrink-0 flex items-center gap-1.5 px-3 py-2 bg-[#141414] border border-white/[0.06] rounded-full text-xs text-white/60 hover:border-[#c8ff00]/30 hover:text-[#c8ff00] transition-all"
                >
                  <span>{action.icon}</span>
                  <span>{action.label}</span>
                </button>
              ))}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Quick Action Grid — shows when conversation has ≤1 message */}
      {showActionGrid && (
        <div className="px-3 pb-2 md:px-4">
          <div className="grid grid-cols-2 gap-2">
            {QUICK_ACTIONS.map((action, aidx) => (
              <button
                key={aidx}
                onClick={() => sendMessage(action.prompt)}
                className="bg-[#141414] border border-white/[0.06] rounded-xl p-3 md:p-4 text-left hover:border-[#c8ff00]/30 hover:bg-[#1a1a1a] transition-all active:scale-[0.97] group"
              >
                <div className="text-xl md:text-2xl mb-1.5">{action.icon}</div>
                <div className="font-semibold text-white text-sm font-display">{action.title}</div>
                <div className="text-[11px] text-white/35 mt-0.5 leading-tight">{action.desc}</div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Bar */}
      <div className="border-t border-white/[0.06] p-3 md:p-4 bg-[#0a0a0a]">
        <div className="flex items-end gap-2">
          {/* Attach placeholder */}
          <button
            className="p-2 text-white/20 hover:text-white/40 transition-colors flex-shrink-0 mb-0.5"
            title="Attach (coming soon)"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13"
              />
            </svg>
          </button>

          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              autoResize()
            }}
            onKeyDown={handleKeyPress}
            placeholder="Ask anything about recruiting..."
            disabled={loading}
            rows={1}
            className="flex-1 px-3 py-2.5 bg-[#141414] border border-white/[0.06] rounded-xl text-white/90 placeholder-white/25 focus:ring-1 focus:ring-[#c8ff00]/50 focus:border-[#c8ff00]/50 resize-none disabled:opacity-40 text-sm min-h-[42px] max-h-[120px] outline-none transition-all"
          />

          {/* Mic placeholder */}
          <button
            className="p-2 text-white/20 hover:text-white/40 transition-colors flex-shrink-0 mb-0.5"
            title="Voice input (coming soon)"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z"
              />
            </svg>
          </button>

          {/* Send button */}
          <button
            onClick={() => sendMessage()}
            disabled={loading || !input.trim()}
            className="p-2.5 bg-[#c8ff00] text-[#0a0a0a] rounded-xl hover:bg-[#d4ff33] disabled:opacity-30 disabled:cursor-not-allowed transition-all flex-shrink-0 mb-0.5"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}

/* ── /demo-style Terminal Thinking Feed ── */
function ThinkingCard({
  steps,
  parseSteps,
}: {
  steps: string[]
  parseSteps: (s: string[]) => { tool: string; status: 'active' | 'done'; text: string; icon: string }[]
}) {
  const timeline = parseSteps(steps)
  const allDone = timeline.length > 0 && timeline.every(s => s.status === 'done')

  return (
    <div className={`rounded-xl border bg-black/40 overflow-hidden transition-all duration-700 w-full ${
      allDone ? 'border-[#c8ff00]/30 bg-[#c8ff00]/[0.03]' : 'border-white/10'
    }`}>
      {/* Terminal header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5 bg-white/[0.02]">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
        </div>
        <span className="text-[11px] text-gray-500 font-mono ml-2">sparq-agent</span>
        {allDone && (
          <span className="ml-auto text-[10px] text-[#c8ff00] font-mono font-semibold">
            ✓ Complete
          </span>
        )}
        {!allDone && (
          <div className="ml-auto h-0.5 w-16 bg-white/[0.04] rounded-full overflow-hidden">
            <div className="h-full bg-[#c8ff00] animate-thinking-progress rounded-full" />
          </div>
        )}
      </div>

      {/* Steps */}
      <div className="px-4 py-3 space-y-1">
        {timeline.length > 0 ? (
          timeline.map((step, sidx) => (
            <div
              key={sidx}
              className="flex items-center gap-2.5 font-mono text-sm animate-slideIn"
              style={{ animationDelay: `${sidx * 80}ms` }}
            >
              {/* Icon */}
              <span className="w-4 flex-shrink-0 text-center">
                {step.status === 'done' ? (
                  <span className="text-[#c8ff00] font-bold">✓</span>
                ) : (
                  <span className="inline-block w-3.5 h-3.5 border-2 border-[#c8ff00] border-t-transparent rounded-full animate-spin" />
                )}
              </span>
              {/* Label */}
              <span className={`flex-1 ${step.status === 'done' ? 'text-gray-400' : 'text-white'}`}>
                {step.text}
              </span>
            </div>
          ))
        ) : (
          <div className="flex items-center gap-2.5 font-mono text-sm">
            <span className="inline-block w-3.5 h-3.5 border-2 border-[#c8ff00] border-t-transparent rounded-full animate-spin" />
            <span className="text-white">Getting started...</span>
          </div>
        )}
      </div>
    </div>
  )
}
