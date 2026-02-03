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
}

export default function AgentChat({ athleteId, athleteName }: AgentChatProps) {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content: `Hi ${athleteName.split(' ')[0]}! I'm your AI recruiting agent. I can help you:\n\n• Find camps and combines\n• Research coaches and programs\n• Draft emails and messages\n• Analyze your profile and metrics\n• Discover opportunities\n\nWhat would you like help with?`,
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const formatMessageContent = (content: string) => {
    // Convert markdown-style formatting to HTML
    let formatted = content
      // Bold text
      .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
      // Headers
      .replace(/^### (.+)$/gm, '<h4 class="font-semibold text-gray-900 mt-3 mb-2">$1</h4>')
      .replace(/^## (.+)$/gm, '<h3 class="font-bold text-gray-900 mt-4 mb-2">$1</h3>')
      // Bullet points
      .replace(/^- (.+)$/gm, '<li class="ml-4">$1</li>')
      // URLs
      .replace(/(https?:\/\/[^\s]+)/g, '<a href="$1" target="_blank" rel="noopener noreferrer" class="text-indigo-600 hover:text-indigo-700 underline">$1</a>')
    
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
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
      
      // Create abort controller with 60 second timeout (agent can take 30-40s)
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 60000)
      
      const response = await fetch(`${backendUrl}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_id: athleteId,
          message: input,
          conversation_history: messages.slice(-5) // Last 5 messages for context
        }),
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)

      if (!response.ok) {
        throw new Error('Failed to get response from agent')
      }

      const data = await response.json()

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
    <div className="bg-white rounded-xl shadow-lg border border-gray-200 flex flex-col h-[700px]">
      {/* Header */}
      <div className="border-b border-gray-200 p-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center">
            <span className="text-xl">🤖</span>
          </div>
          <div>
            <h3 className="font-semibold text-gray-900">SPARQ Agent</h3>
            <p className="text-sm text-gray-600">Your AI recruiting coordinator</p>
          </div>
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
                <div className="bg-indigo-600 text-white rounded-lg p-3">
                  <div className="whitespace-pre-wrap">{message.content}</div>
                  <div className="text-xs mt-1 text-indigo-200">
                    {message.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              ) : message.thinking ? (
                // Thinking indicator
                <div className="bg-indigo-50 border border-indigo-200 rounded-lg p-4">
                  <div className="flex items-center gap-2">
                    <div className="animate-spin rounded-full h-4 w-4 border-2 border-indigo-600 border-t-transparent"></div>
                    <span className="text-sm font-medium text-indigo-700">Agent is thinking...</span>
                  </div>
                </div>
              ) : (
                // Assistant response
                <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
                  {/* Agent steps - what it did */}
                  {message.agentSteps && message.agentSteps.length > 0 && (
                    <div className="px-4 pt-3 pb-2 border-b border-gray-100 bg-indigo-50">
                      <div className="text-xs font-medium text-indigo-700 mb-2">Agent Activity:</div>
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
                      <div className="w-6 h-6 bg-indigo-100 rounded-full flex items-center justify-center">
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
                            className="border border-gray-200 rounded-lg p-4 hover:border-indigo-300 hover:shadow-sm transition-all"
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
                                  className="px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors whitespace-nowrap"
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
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none disabled:opacity-50"
          />
          <button
            onClick={sendMessage}
            disabled={loading || !input.trim()}
            className="px-6 py-2 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
        <div className="mt-2 flex gap-2 flex-wrap">
          {!loading && messages.length <= 1 && (
            <>
              <button
                onClick={() => setInput('Find camps near me')}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200"
              >
                Find camps near me
              </button>
              <button
                onClick={() => setInput('Research coaches recruiting my position')}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200"
              >
                Research coaches
              </button>
              <button
                onClick={() => setInput('Help me write an email to a coach')}
                className="px-3 py-1 text-sm bg-gray-100 text-gray-700 rounded-full hover:bg-gray-200"
              >
                Draft an email
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
