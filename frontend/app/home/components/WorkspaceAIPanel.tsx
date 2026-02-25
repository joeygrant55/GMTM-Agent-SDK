'use client'

import { FormEvent, KeyboardEvent, useRef, useState } from 'react'

type ChatMessage = {
  role: 'assistant' | 'user'
  content: string
}

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

const INITIAL_MESSAGE: ChatMessage = {
  role: 'assistant',
  content:
    'Hey! I am your recruiting AI. I can help you find college matches, draft emails to coaches, and analyze your profile. What are you working on?',
}

const FALLBACK_MESSAGE =
  'I need an athlete profile connected to give you personalized advice. You can connect your profile from the Quick Scan page.'

export default function WorkspaceAIPanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([INITIAL_MESSAGE])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  const resizeTextarea = () => {
    const el = textareaRef.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`
  }

  const sendMessage = async (event?: FormEvent) => {
    event?.preventDefault()
    const message = input.trim()
    if (!message || sending) return

    setMessages((prev) => [...prev, { role: 'user', content: message }])
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setSending(true)

    try {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
      const response = await fetch(`${backendUrl}/api/agent/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, context: 'workspace' }),
      })

      if (!response.ok) {
        throw new Error('Agent request failed')
      }

      const data = await response.json()
      const assistantContent =
        data?.response || data?.message || data?.reply || data?.output || 'Let me know what you want to focus on next.'

      setMessages((prev) => [...prev, { role: 'assistant', content: String(assistantContent) }])
    } catch {
      setMessages((prev) => [...prev, { role: 'assistant', content: FALLBACK_MESSAGE }])
    } finally {
      setSending(false)
    }
  }

  const onInputKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      void sendMessage()
    }
  }

  return (
    <aside className="w-[300px] h-screen border-l border-white/10 bg-sparq-charcoal flex flex-col">
      <div className="p-4 border-b border-white/10">
        <h2 className="text-white font-bold">Recruiting AI ✨</h2>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {messages.map((message, index) => (
          <div
            key={`${message.role}-${index}`}
            className={
              message.role === 'user'
                ? 'bg-sparq-lime/10 border border-sparq-lime/20 rounded-xl p-3 ml-8 text-gray-100'
                : 'bg-white/[0.04] border border-white/10 rounded-xl p-3 mr-8 text-gray-200'
            }
          >
            {message.content}
          </div>
        ))}
      </div>

      <form onSubmit={sendMessage} className="p-4 border-t border-white/10">
        <div className="flex items-end gap-2">
          <textarea
            ref={textareaRef}
            rows={1}
            value={input}
            onChange={(event) => setInput(event.target.value)}
            onInput={resizeTextarea}
            onKeyDown={onInputKeyDown}
            placeholder="Ask your recruiting AI..."
            className="flex-1 resize-none bg-white/[0.04] border border-white/10 rounded-lg px-3 py-2 text-sm text-white placeholder:text-gray-500 focus:outline-none focus:border-sparq-lime/40"
          />
          <button
            type="submit"
            disabled={sending || !input.trim()}
            className="bg-sparq-lime text-sparq-charcoal font-black px-4 py-2 rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Send
          </button>
        </div>
      </form>
    </aside>
  )
}
