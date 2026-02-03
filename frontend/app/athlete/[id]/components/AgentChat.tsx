'use client'

import { useState, useRef, useEffect } from 'react'

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp: Date
  thinking?: boolean
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
    // Convert markdown tables to HTML tables
    let formatted = content
    
    // Detect markdown tables and convert them
    const tableRegex = /\|(.+)\|\n\|[-:\| ]+\|\n((?:\|.+\|\n?)+)/gm
    formatted = formatted.replace(tableRegex, (match, headerRow, bodyRows) => {
      const headers = headerRow.split('|').map((h: string) => h.trim()).filter((h: string) => h)
      const rows = bodyRows.trim().split('\n').map((row: string) => 
        row.split('|').map((cell: string) => cell.trim()).filter((cell: string) => cell)
      )
      
      let table = '<div class="overflow-x-auto my-3"><table class="min-w-full text-sm border border-gray-200 rounded-lg overflow-hidden">'
      table += '<thead class="bg-gray-900"><tr>'
      headers.forEach((h: string) => {
        table += `<th class="px-3 py-2 text-left font-semibold text-sparq-lime border-b border-gray-700">${h}</th>`
      })
      table += '</tr></thead><tbody>'
      rows.forEach((row: string[], idx: number) => {
        const bgClass = idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'
        table += `<tr class="${bgClass}">`
        row.forEach((cell: string) => {
          table += `<td class="px-3 py-2 border-b border-gray-100 text-gray-700">${cell}</td>`
        })
        table += '</tr>'
      })
      table += '</tbody></table></div>'
      return table
    })
    
    // Bold text
    formatted = formatted.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    // Headers
    formatted = formatted.replace(/^#### (.+)$/gm, '<h5 class="font-semibold text-gray-800 mt-3 mb-1 text-sm">$1</h5>')
    formatted = formatted.replace(/^### (.+)$/gm, '<h4 class="font-semibold text-gray-900 mt-4 mb-2">$1</h4>')
    formatted = formatted.replace(/^## (.+)$/gm, '<h3 class="font-bold text-gray-900 mt-4 mb-2 text-lg">$1</h3>')
    formatted = formatted.replace(/^# (.+)$/gm, '<h2 class="font-bold text-gray-900 mt-4 mb-2 text-xl">$1</h2>')
    // Horizontal rules
    formatted = formatted.replace(/^---$/gm, '<hr class="my-3 border-gray-200">')
    // Bullet points
    formatted = formatted.replace(/^- (.+)$/gm, '<div class="flex gap-2 ml-2"><span class="text-sparq-lime-dark">•</span><span>$1</span></div>')
    // URLs
    formatted = formatted.replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-sparq-charcoal hover:text-sparq-charcoal underline">$1</a>')
    // Emojis as section markers
    formatted = formatted.replace(/^((?:📊|🏈|🎯|💪|⚠️|✅|🏫|📅|🎥|✉️|🔍|⭐|🌟).+)$/gm, '<div class="font-medium text-gray-900 mt-3">$1</div>')
    
    return formatted
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

    // Add thinking indicator
    const thinkingMessage: Message = {
      role: 'assistant',
      content: 'Thinking...',
      timestamp: new Date(),
      thinking: true
    }
    setMessages(prev => [...prev, thinkingMessage])

    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 120000) // 2 min for deep research
      
      const response = await fetch(`${backendUrl}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_id: athleteId,
          message: input,
          conversation_id: conversationId,
          conversation_history: conversationId ? [] : messages.slice(-5)
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error('Failed to get response from agent')
      }

      const data = await response.json()

      // Save conversation ID for persistence
      if (data.conversation_id && !conversationId) {
        setConversationId(data.conversation_id)
        // Refresh sidebar
        fetch(`${backendUrl}/api/conversations/${athleteId}`)
          .then(r => r.json())
          .then(d => setConversations(d.conversations || []))
          .catch(() => {})
      }

      // Remove thinking message and add real response with tools used
      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role: 'assistant',
          content: data.response || data.message || 'I encountered an error. Please try again.',
          timestamp: new Date(),
          toolsUsed: data.tools_used || [],
          agentSteps: data.agent_steps || [],
          structured: data.structured || null
        }
      ])

    } catch (error: any) {
      // Remove thinking message and show error
      const errorMessage = error.name === 'AbortError' 
        ? 'The request took too long. The agent might be doing deep research - please try a simpler question or try again.'
        : `Sorry, I encountered an error: ${error.message}. Please try again.`
      
      setMessages(prev => [
        ...prev.slice(0, -1),
        {
          role: 'assistant',
          content: errorMessage,
          timestamp: new Date()
        }
      ])
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
                      <div 
                        dangerouslySetInnerHTML={{ 
                          __html: formatMessageContent(message.content) 
                        }}
                      />
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
