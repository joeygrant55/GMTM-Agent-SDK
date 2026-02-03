'use client'

import { useState, useRef, useEffect } from 'react'

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  thinking?: boolean
  streaming?: boolean  // Currently receiving streamed text
  thinkingSteps?: string[]
  toolsUsed?: string[]
  agentSteps?: string[]  // Step-by-step what agent did
  structured?: any // Structured data for cards/actions
}

interface AgentChatProps {
  athleteId: string
  athleteName: string
  initialConversationId?: number | null
}

export default function AgentChat({ athleteId, athleteName, initialConversationId }: AgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `Hi ${athleteName.split(' ')[0]}! I'm your AI recruiting agent. I can help you:\n\n• Find camps and combines\n• Research coaches and programs\n• Draft emails and messages\n• Analyze your profile and metrics\n• Discover opportunities\n\nWhat would you like help with?`,
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [conversationId, setConversationId] = useState<number | null>(null)
  const [conversations, setConversations] = useState<any[]>([])
  const [showSidebar, setShowSidebar] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

  // Load conversations list on mount + initial conversation if provided
  useEffect(() => {
    fetch(`${backendUrl}/api/conversations/${athleteId}`)
      .then(r => r.json())
      .then(data => setConversations(data.conversations || []))
      .catch(() => {})
    if (initialConversationId) {
      loadConversation(initialConversationId)
    }
  }, [athleteId, initialConversationId])

  // Load a specific conversation
  const loadConversation = async (convId: number) => {
    try {
      const res = await fetch(`${backendUrl}/api/conversations/${athleteId}/${convId}`)
      const data = await res.json()
      setConversationId(convId)
      const loaded: Message[] = data.messages.map((m: any) => ({
        role: m.role,
        content: m.content,
        timestamp: new Date(m.created_at),
        toolsUsed: m.tools_used ? (typeof m.tools_used === 'string' ? JSON.parse(m.tools_used) : m.tools_used) : [],
        agentSteps: m.agent_steps ? (typeof m.agent_steps === 'string' ? JSON.parse(m.agent_steps) : m.agent_steps) : [],
      }))
      setMessages(loaded)
      setShowSidebar(false)
    } catch (e) {}
  }

  // Start new conversation
  const newConversation = () => {
    setConversationId(null)
    setMessages([{
      role: 'assistant',
      content: `Hi ${athleteName.split(' ')[0]}! I'm your AI recruiting agent. I can help you:\n\n• Find camps and combines\n• Research coaches and programs\n• Draft emails and messages\n• Analyze your profile and metrics\n• Discover opportunities\n\nWhat would you like help with?`,
      timestamp: new Date()
    }])
    setShowSidebar(false)
  }

  const formatMessageContent = (content: string) => {
    // Split into lines for processing
    const lines = content.split('\n')
    let html = ''
    let inTable = false
    let tableHeaders: string[] = []
    let tableRows: string[][] = []

    const formatInline = (text: string) => {
      return text
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-sparq-charcoal underline">$1</a>')
    }

    const flushTable = () => {
      if (tableHeaders.length === 0) return ''
      let t = '<div class="overflow-x-auto my-3"><table class="min-w-full text-sm border border-gray-200 rounded-lg overflow-hidden">'
      t += '<thead class="bg-gray-900"><tr>'
      tableHeaders.forEach(h => {
        t += `<th class="px-3 py-2 text-left font-semibold text-sparq-lime border-b border-gray-700">${formatInline(h)}</th>`
      })
      t += '</tr></thead><tbody>'
      tableRows.forEach((row, idx) => {
        const bg = idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'
        t += `<tr class="${bg}">`
        row.forEach(cell => {
          t += `<td class="px-3 py-2 border-b border-gray-100 text-gray-700">${formatInline(cell)}</td>`
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

      // Table detection: line starts and ends with |
      if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
        const cells = trimmed.slice(1, -1).split('|').map(c => c.trim())
        
        // Check if this is a separator row (|---|---|---|)
        if (cells.every(c => /^[-:\s]+$/.test(c))) {
          inTable = true
          continue
        }
        
        if (!inTable && tableHeaders.length === 0) {
          // This is the header row
          tableHeaders = cells
          continue
        }
        
        if (inTable) {
          tableRows.push(cells)
          continue
        }
      } else {
        // Not a table row - flush any pending table
        if (inTable || tableHeaders.length > 0) {
          html += flushTable()
        }
      }

      // Headers
      if (trimmed.startsWith('#### ')) {
        html += `<h5 class="font-semibold text-gray-800 mt-3 mb-1 text-sm">${formatInline(trimmed.slice(5))}</h5>`
      } else if (trimmed.startsWith('### ')) {
        html += `<h4 class="font-semibold text-gray-900 mt-4 mb-2">${formatInline(trimmed.slice(4))}</h4>`
      } else if (trimmed.startsWith('## ')) {
        html += `<h3 class="font-bold text-gray-900 mt-4 mb-2 text-lg">${formatInline(trimmed.slice(3))}</h3>`
      } else if (trimmed.startsWith('# ')) {
        html += `<h2 class="font-bold text-gray-900 mt-4 mb-2 text-xl">${formatInline(trimmed.slice(2))}</h2>`
      } else if (trimmed === '---') {
        html += '<hr class="my-3 border-gray-200">'
      } else if (trimmed.startsWith('- ')) {
        html += `<div class="flex gap-2 ml-2 my-0.5"><span class="text-sparq-lime-dark">•</span><span>${formatInline(trimmed.slice(2))}</span></div>`
      } else if (trimmed === '') {
        html += '<div class="h-2"></div>'
      } else {
        html += `<p class="my-1">${formatInline(trimmed)}</p>`
      }
    }

    // Flush any remaining table
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

  const sendMessage = async () => {
    if (!input.trim() || loading) return

    const userMessage: Message = {
      role: 'user',
      content: input,
      timestamp: new Date()
    }

    setMessages(prev => [...prev, userMessage])
    setInput('')
    setLoading(true)

    // Add streaming message placeholder
    const streamingMessage: Message = {
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      thinking: true,
      agentSteps: []
    }
    setMessages(prev => [...prev, streamingMessage])

    try {
      const response = await fetch(`${backendUrl}/api/agent/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_id: athleteId,
          message: input,
          conversation_id: conversationId,
          conversation_history: conversationId ? [] : messages.slice(-5)
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

        // Parse SSE events from buffer
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

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
                  .then(r => r.json())
                  .then(d => setConversations(d.conversations || []))
                  .catch(() => {})
              }
            } else if (eventType === 'status') {
              // Update thinking status
              setMessages(prev => {
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
                steps.push(toolData.step)
                toolsUsed.push(toolData.tool)
                setMessages(prev => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last?.thinking) {
                    updated[updated.length - 1] = { ...last, content: 'Researching...', agentSteps: [...steps] }
                  }
                  return updated
                })
              } catch {}
            } else if (eventType === 'tool_done') {
              try {
                const toolData = JSON.parse(data)
                steps.push(toolData.step)
                setMessages(prev => {
                  const updated = [...prev]
                  const last = updated[updated.length - 1]
                  if (last?.thinking) {
                    updated[updated.length - 1] = { ...last, agentSteps: [...steps] }
                  }
                  return updated
                })
              } catch {}
            } else if (eventType === 'text') {
              streamedText += data
              // Switch from thinking to streaming text
              setMessages(prev => {
                const updated = [...prev]
                const last = updated[updated.length - 1]
                updated[updated.length - 1] = {
                  ...last,
                  content: streamedText,
                  thinking: false,
                  streaming: true,
                  agentSteps: [...steps],
                  toolsUsed: [...toolsUsed]
                }
                return updated
              })
            } else if (eventType === 'error') {
              setMessages(prev => {
                const updated = [...prev]
                updated[updated.length - 1] = {
                  role: 'assistant',
                  content: `Sorry, I encountered an error: ${data}. Please try again.`,
                  timestamp: new Date(),
                  thinking: false
                }
                return updated
              })
            }
            eventType = ''
          }
        }
      }

      // Final update - streaming complete, now format properly
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: streamedText || 'I completed my research. How can I help further?',
          timestamp: new Date(),
          thinking: false,
          streaming: false,
          toolsUsed,
          agentSteps: steps
        }
        return updated
      })

    } catch (error: any) {
      setMessages(prev => {
        const updated = [...prev]
        updated[updated.length - 1] = {
          role: 'assistant',
          content: `Sorry, I encountered an error: ${error.message}. Please try again.`,
          timestamp: new Date()
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

  return (
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 flex flex-col h-[700px] relative">
      {/* Conversation Sidebar */}
      {showSidebar && (
        <div className="absolute inset-0 z-20 flex">
          <div className="w-72 bg-white border-r border-gray-200 flex flex-col h-full rounded-l-xl">
            <div className="p-3 border-b border-gray-200 flex items-center justify-between">
              <h4 className="font-semibold text-gray-900 text-sm">Your Conversations</h4>
              <button onClick={() => setShowSidebar(false)} className="text-gray-400 hover:text-gray-600 text-lg">✕</button>
            </div>
            <div className="p-2">
              <button
                onClick={newConversation}
                className="w-full px-3 py-2 bg-sparq-charcoal text-sparq-lime text-sm font-medium rounded-lg hover:bg-sparq-charcoal-light transition-colors mb-2"
              >
                + New Chat
              </button>
            </div>
            <div className="flex-1 overflow-y-auto px-2 pb-2">
              {conversations.length === 0 ? (
                <p className="text-gray-400 text-sm text-center py-4">No saved chats yet</p>
              ) : (
                conversations.map(conv => (
                  <button
                    key={conv.id}
                    onClick={() => loadConversation(conv.id)}
                    className={`w-full text-left px-3 py-2 rounded-lg text-sm mb-1 transition-colors ${
                      conversationId === conv.id 
                        ? 'bg-sparq-lime/20 text-sparq-charcoal font-medium' 
                        : 'hover:bg-gray-100 text-gray-700'
                    }`}
                  >
                    <div className="font-medium truncate">{conv.title}</div>
                    <div className="text-xs text-gray-400 mt-0.5">
                      {conv.message_count} messages • {new Date(conv.updated_at).toLocaleDateString()}
                    </div>
                  </button>
                ))
              )}
            </div>
          </div>
          <div className="flex-1 bg-black/20" onClick={() => setShowSidebar(false)} />
        </div>
      )}

      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <button onClick={() => setShowSidebar(!showSidebar)} className="text-gray-400 hover:text-gray-600" title="Chat history">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" /></svg>
          </button>
          <img src="/sparq-logo.jpg" alt="SPARQ" className="w-10 h-10 rounded-full" />
          <div className="flex-1">
            <h3 className="font-semibold text-gray-900">SPARQ Agent</h3>
            <p className="text-sm text-gray-600">Your AI recruiting coordinator</p>
          </div>
          <button onClick={newConversation} className="text-sm px-3 py-1 bg-gray-100 text-gray-600 rounded-lg hover:bg-gray-200 transition-colors">
            + New
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, idx) => (
          <div
            key={idx}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] ${
                message.role === 'user' ? '' : 'w-full'
              }`}
            >
              {message.role === 'user' ? (
                // User message
                <div className="bg-sparq-charcoal text-white rounded-lg p-3">
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  <div className="text-xs mt-1 text-indigo-200">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              ) : message.thinking ? (
                // Thinking indicator
                <div className="bg-sparq-lime/10 border border-indigo-200 rounded-lg p-4">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-indigo-600 border-t-transparent"></div>
                    <span className="text-sm font-medium text-sparq-charcoal">Agent is thinking...</span>
                  </div>
                </div>
              ) : (
                // Assistant response
                <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                  {/* Agent steps - what it did */}
                  {message.agentSteps && message.agentSteps.length > 0 && (
                    <div className="px-4 pt-3 pb-2 border-b border-gray-100 bg-sparq-lime/10">
                      <div className="text-xs font-medium text-sparq-charcoal mb-2">Agent Activity:</div>
                      <div className="space-y-1">
                        {message.agentSteps.map((step, sidx) => (
                          <div key={sidx} className="text-xs text-gray-700">
                            {step}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                  
                  {/* Main content */}
                  <div className="p-4">
                    <div className="flex items-center gap-2 mb-3">
                      <div className="w-6 h-6 bg-sparq-lime/20 rounded-full flex items-center justify-center">
                        <span className="text-sm">🤖</span>
                      </div>
                      <span className="text-sm font-medium text-gray-900">SPARQ Agent</span>
                    </div>
                    
                    {/* Structured data (camp cards) */}
                    {message.structured?.camps && (
                      <div className="space-y-3 mb-4">
                        {message.structured.camps.map((camp: any, idx: number) => (
                          <div 
                            key={idx}
                            className="border border-gray-200 rounded-lg p-4 hover:border-sparq-lime hover:shadow-sm transition-all"
                          >
                            <div className="flex items-start justify-between gap-4">
                              <div className="flex-1">
                                <h4 className="font-semibold text-gray-900 mb-1">
                                  {camp.name}
                                </h4>
                              </div>
                              {camp.url && (
                                <a
                                  href={camp.url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="px-4 py-2 bg-sparq-charcoal text-white text-sm font-medium rounded-lg hover:bg-sparq-charcoal-light transition-colors whitespace-nowrap"
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
                    <div className="prose prose-sm max-w-none text-gray-700">
                      {message.streaming ? (
                        <div className="whitespace-pre-wrap">{message.content}<span className="animate-pulse">▊</span></div>
                      ) : (
                        <div 
                          dangerouslySetInnerHTML={{ 
                            __html: formatMessageContent(message.content) 
                          }}
                        />
                      )}
                    </div>
                    
                    <div className="text-xs text-gray-400 mt-3">
                      {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-gray-200 p-4">
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyPress}
            placeholder="Ask me anything about recruiting..."
            disabled={loading}
            rows={2}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-sparq-lime focus:border-sparq-lime resize-none disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-sparq-charcoal text-white font-medium rounded-lg hover:bg-sparq-charcoal-light disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
        <div className="mt-2 flex gap-2 flex-wrap">
          {!loading && messages.length <= 1 && (
            <>
              <button
                onClick={() => setInput('What college programs are the best fit for me?')}
                className="px-3 py-1 text-sm bg-gray-900 text-sparq-lime rounded-full hover:bg-gray-800 transition-colors"
              >
                🏫 Match me to colleges
              </button>
              <button
                onClick={() => setInput('How do my metrics compare to other athletes at my position?')}
                className="px-3 py-1 text-sm bg-gray-900 text-sparq-lime rounded-full hover:bg-gray-800 transition-colors"
              >
                📊 Analyze my profile
              </button>
              <button
                onClick={() => setInput('Find camps near me')}
                className="px-3 py-1 text-sm bg-gray-900 text-sparq-lime rounded-full hover:bg-gray-800 transition-colors"
              >
                🏕️ Find camps
              </button>
              <button
                onClick={() => setInput('Help me write an introduction email to a college coach')}
                className="px-3 py-1 text-sm bg-gray-900 text-sparq-lime rounded-full hover:bg-gray-800 transition-colors"
              >
                ✉️ Email a coach
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
