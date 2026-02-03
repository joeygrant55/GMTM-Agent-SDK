'use client'

import { useState, useRef, useEffect } from 'react'
import Link from 'next/link'

const DEMO_ATHLETE_ID = '67782'
const DEMO_ATHLETE_NAME = 'Joey Grant'
const DEMO_PROFILE = {
  position: 'Quarterback',
  city: 'Altamonte Springs',
  state: 'FL',
  initials: 'JG'
}

const SUGGESTED_PROMPTS = [
  "What D1 programs are the best fit for me based on my metrics?",
  "Draft an email to the UCF coaching staff introducing myself",
  "How do my stats compare to other QBs in Florida?",
  "Find me quarterback camps and combines this spring",
]

interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  tools?: string[]
  streaming?: boolean
}

const formatInline = (text: string) => {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/(https?:\/\/[^\s<)]+)/g, '<a href="$1" target="_blank" rel="noopener" class="text-sparq-lime underline">$1</a>')
}

const formatContent = (content: string) => {
  const lines = content.split('\n')
  let html = ''
  let inTable = false
  let tableHeaders: string[] = []
  let tableRows: string[][] = []

  const flushTable = () => {
    if (tableHeaders.length === 0) return ''
    let t = '<div class="overflow-x-auto my-3"><table class="min-w-full text-sm border border-gray-700 rounded overflow-hidden">'
    t += '<thead class="bg-gray-800"><tr>'
    tableHeaders.forEach(h => { t += `<th class="px-3 py-2 text-left font-semibold text-sparq-lime border-b border-gray-700">${formatInline(h)}</th>` })
    t += '</tr></thead><tbody>'
    tableRows.forEach((row, idx) => {
      const bg = idx % 2 === 0 ? 'bg-gray-900/50' : 'bg-gray-800/30'
      t += `<tr class="${bg}">`
      row.forEach(cell => { t += `<td class="px-3 py-2 border-b border-gray-800 text-gray-300">${formatInline(cell)}</td>` })
      t += '</tr>'
    })
    t += '</tbody></table></div>'
    tableHeaders = []; tableRows = []; inTable = false
    return t
  }

  for (const line of lines) {
    const trimmed = line.trim()
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const cells = trimmed.slice(1, -1).split('|').map(c => c.trim())
      if (cells.every(c => /^[-:\s]+$/.test(c))) { inTable = true; continue }
      if (!inTable && tableHeaders.length === 0) { tableHeaders = cells; continue }
      if (inTable) { tableRows.push(cells); continue }
    } else {
      if (inTable || tableHeaders.length > 0) html += flushTable()
    }

    if (trimmed.startsWith('### ')) html += `<h3 class="font-semibold text-white mt-4 mb-2 text-base">${formatInline(trimmed.slice(4))}</h3>`
    else if (trimmed.startsWith('## ')) html += `<h2 class="font-bold text-white mt-5 mb-2 text-lg">${formatInline(trimmed.slice(3))}</h2>`
    else if (trimmed.startsWith('# ')) html += `<h1 class="font-bold text-white mt-4 mb-3 text-xl">${formatInline(trimmed.slice(2))}</h1>`
    else if (trimmed === '---') html += '<hr class="my-4 border-gray-700">'
    else if (trimmed.startsWith('- ')) html += `<div class="flex gap-2 ml-2 my-1"><span class="text-sparq-lime mt-0.5">•</span><span class="text-gray-300">${formatInline(trimmed.slice(2))}</span></div>`
    else if (/^\d+\.\s/.test(trimmed)) html += `<div class="flex gap-2 ml-2 my-1"><span class="text-sparq-lime font-medium">${trimmed.match(/^\d+/)![0]}.</span><span class="text-gray-300">${formatInline(trimmed.replace(/^\d+\.\s*/, ''))}</span></div>`
    else if (trimmed === '') html += '<div class="h-2"></div>'
    else html += `<p class="my-1.5 text-gray-300 leading-relaxed">${formatInline(trimmed)}</p>`
  }
  if (inTable || tableHeaders.length > 0) html += flushTable()
  return html
}

export default function DemoPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isStreaming, setIsStreaming] = useState(false)
  const [msgCount, setMsgCount] = useState(0)
  const [activeTools, setActiveTools] = useState<string[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

  const MAX_DEMO_MESSAGES = 5

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, activeTools])

  const sendMessage = async (text: string) => {
    if (!text.trim() || isStreaming || msgCount >= MAX_DEMO_MESSAGES) return

    const userMsg: Message = { role: 'user', content: text }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setIsStreaming(true)
    setMsgCount(prev => prev + 1)

    const toolsUsed: string[] = []
    let fullText = ''

    try {
      const res = await fetch(`${backendUrl}/api/agent/chat/stream`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          athlete_id: DEMO_ATHLETE_ID,
          message: text,
          conversation_id: null
        })
      })

      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      // Add empty assistant message
      setMessages(prev => [...prev, { role: 'assistant', content: '', streaming: true }])

      while (reader) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            const eventType = line.slice(7).trim()
            const nextLine = lines[lines.indexOf(line) + 1]
            if (nextLine?.startsWith('data: ')) {
              try {
                const data = JSON.parse(nextLine.slice(6))
                if (eventType === 'tool_start') {
                  toolsUsed.push(data.tool)
                  setActiveTools(prev => [...prev, data.tool])
                } else if (eventType === 'tool_done') {
                  setActiveTools(prev => prev.filter(t => t !== data.tool))
                } else if (eventType === 'text') {
                  const chunk = (data.content || '').replace(/\\n/g, '\n')
                  fullText += chunk
                  setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1] = { role: 'assistant', content: fullText, streaming: true }
                    return updated
                  })
                }
              } catch {}
            }
          } else if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6))
              if (data.content) {
                const chunk = data.content.replace(/\\n/g, '\n')
                fullText += chunk
                setMessages(prev => {
                  const updated = [...prev]
                  updated[updated.length - 1] = { role: 'assistant', content: fullText, streaming: true }
                  return updated
                })
              }
            } catch {}
          }
        }
      }
    } catch (err) {
      fullText = 'Sorry, something went wrong. Try again!'
    }

    // Finalize
    setMessages(prev => {
      const updated = [...prev]
      updated[updated.length - 1] = { role: 'assistant', content: fullText, tools: toolsUsed, streaming: false }
      return updated
    })
    setActiveTools([])
    setIsStreaming(false)
  }

  const atLimit = msgCount >= MAX_DEMO_MESSAGES

  return (
    <div className="min-h-screen bg-sparq-charcoal flex flex-col">
      {/* Header */}
      <header className="border-b border-white/10 px-4 py-3">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center gap-2">
              <img src="/sparq-logo.jpg" alt="SPARQ" className="w-8 h-8 rounded-lg" />
              <span className="font-bold text-white">SPARQ Agent</span>
            </Link>
            <span className="px-2 py-0.5 bg-sparq-lime/10 text-sparq-lime text-xs font-medium rounded-full border border-sparq-lime/20">DEMO</span>
          </div>
          <Link href="/sign-up" className="px-4 py-2 bg-sparq-lime text-sparq-charcoal text-sm font-bold rounded-lg hover:bg-sparq-lime-dark transition-colors">
            Sign Up Free
          </Link>
        </div>
      </header>

      <div className="flex-1 max-w-4xl w-full mx-auto flex flex-col">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-4 py-6 space-y-4">
          {/* Intro Card */}
          {messages.length === 0 && (
            <div className="space-y-6">
              {/* Profile Card */}
              <div className="bg-white/5 border border-white/10 rounded-xl p-6 max-w-2xl mx-auto">
                <div className="flex items-center gap-4 mb-4">
                  <div className="w-14 h-14 bg-sparq-lime/20 rounded-full flex items-center justify-center">
                    <span className="text-sparq-lime text-lg font-bold">{DEMO_PROFILE.initials}</span>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-white">{DEMO_ATHLETE_NAME}</h2>
                    <p className="text-gray-400">{DEMO_PROFILE.position} • {DEMO_PROFILE.city}, {DEMO_PROFILE.state}</p>
                  </div>
                </div>
                <p className="text-gray-400 text-sm leading-relaxed">
                  You're testing SPARQ Agent as a real athlete. Ask anything about recruiting — college matching, film review, coach outreach, camp recommendations. The agent has access to real athletic data and recruiting intelligence.
                </p>
              </div>

              {/* Suggested Prompts */}
              <div className="max-w-2xl mx-auto">
                <p className="text-gray-500 text-sm mb-3 text-center">Try asking:</p>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  {SUGGESTED_PROMPTS.map((prompt, i) => (
                    <button
                      key={i}
                      onClick={() => sendMessage(prompt)}
                      className="text-left p-4 bg-white/5 border border-white/10 rounded-xl hover:border-sparq-lime/30 transition-colors"
                    >
                      <p className="text-white text-sm">{prompt}</p>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Chat Messages */}
          {messages.map((msg, i) => (
            <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[85%] rounded-xl px-5 py-3 ${
                msg.role === 'user'
                  ? 'bg-sparq-lime text-sparq-charcoal'
                  : 'bg-white/5 border border-white/10'
              }`}>
                {msg.role === 'assistant' ? (
                  msg.streaming ? (
                    <div className="text-gray-300 whitespace-pre-wrap">
                      {msg.content}<span className="animate-pulse text-sparq-lime">▊</span>
                    </div>
                  ) : (
                    <div dangerouslySetInnerHTML={{ __html: formatContent(msg.content) }} />
                  )
                ) : (
                  <p className="font-medium">{msg.content}</p>
                )}
                {msg.tools && msg.tools.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 mt-2 pt-2 border-t border-white/10">
                    {msg.tools.map((tool, j) => (
                      <span key={j} className="px-2 py-0.5 bg-sparq-lime/10 text-sparq-lime text-xs rounded-full">{tool}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))}

          {/* Active Tools */}
          {activeTools.length > 0 && (
            <div className="flex justify-start">
              <div className="bg-white/5 border border-white/10 rounded-xl px-4 py-3">
                <div className="flex items-center gap-2 text-sm text-gray-400">
                  <div className="animate-spin w-4 h-4 border-2 border-sparq-lime border-t-transparent rounded-full" />
                  Researching: {activeTools[activeTools.length - 1]}...
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Limit CTA */}
        {atLimit && (
          <div className="px-4 pb-4">
            <div className="bg-sparq-lime/10 border border-sparq-lime/20 rounded-xl p-6 text-center">
              <h3 className="text-xl font-bold text-white mb-2">Like what you see? ⚡</h3>
              <p className="text-gray-400 mb-4">Sign up free to connect your own profile and get personalized recruiting advice.</p>
              <Link href="/sign-up" className="inline-block px-8 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark transition-colors">
                Sign Up — It's Free
              </Link>
            </div>
          </div>
        )}

        {/* Input */}
        {!atLimit && (
          <div className="px-4 pb-4 pt-2">
            <div className="flex gap-3 max-w-4xl mx-auto">
              <input
                type="text"
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && sendMessage(input)}
                placeholder={messages.length === 0 ? "Ask about recruiting, college fit, camps..." : "Ask a follow-up..."}
                disabled={isStreaming}
                className="flex-1 px-4 py-3 bg-white/10 border border-white/20 rounded-xl text-white placeholder-gray-500 focus:border-sparq-lime focus:ring-1 focus:ring-sparq-lime disabled:opacity-50"
              />
              <button
                onClick={() => sendMessage(input)}
                disabled={isStreaming || !input.trim()}
                className="px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-xl hover:bg-sparq-lime-dark disabled:opacity-50 transition-colors"
              >
                Send
              </button>
            </div>
            <p className="text-center text-gray-600 text-xs mt-2">
              {MAX_DEMO_MESSAGES - msgCount} demo messages remaining
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
