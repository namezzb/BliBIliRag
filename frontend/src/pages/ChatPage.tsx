import { useEffect, useRef, useState } from 'react'
import { apiClient } from '@/services/api'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [useSelfRag, setUseSelfRag] = useState(true)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: Message = { role: 'user', content: input }
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setError(null)

    try {
      setLoading(true)
      const response = await apiClient.chat(input, 'default', useSelfRag)
      const assistantMessage: Message = { role: 'assistant', content: response.answer }
      setMessages((prev) => [...prev, assistantMessage])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Chat failed')
    } finally {
      setLoading(false)
    }
  }

  const handleClear = () => {
    if (!confirm('确定要清空对话历史吗？')) return
    setMessages([])
    setError(null)
  }

  return (
    <div data-testid="chat-page" className="flex h-full flex-col gap-4 animate-fade-in">
      <section className="panel p-5 sm:p-6">
        <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
          <div>
            <h2 className="text-3xl font-bold" style={{ color: 'var(--text-main)' }}>
              对话助手
            </h2>
            <p className="mt-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
              在索引内容上进行问答，支持 Self-RAG 路径增强。
            </p>
          </div>

          <div className="flex items-center gap-2">
            <label className="panel-muted flex items-center gap-2 px-3 py-2 text-sm" style={{ color: 'var(--text-main)' }}>
              <input
                type="checkbox"
                checked={useSelfRag}
                onChange={(e) => setUseSelfRag(e.target.checked)}
              />
              Self-RAG
            </label>
            <button onClick={handleClear} className="btn-secondary btn-sm">
              清空
            </button>
          </div>
        </div>
      </section>

      <section data-testid="chat-messages" className="panel flex-1 overflow-auto p-4">
        {messages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-center">
            <div>
              <p className="text-lg font-semibold" style={{ color: 'var(--text-main)' }}>
                开始对话吧
              </p>
              <p className="mt-2 text-sm" style={{ color: 'var(--text-subtle)' }}>
                输入问题后系统会发起实时检索与生成。
              </p>
            </div>
          </div>
        ) : (
          <div className="space-y-3">
            {messages.map((msg, idx) => (
              <div key={`${msg.role}-${idx}`} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-6 ${
                    msg.role === 'user' ? 'text-white' : ''
                  }`}
                  style={
                    msg.role === 'user'
                      ? { background: 'linear-gradient(120deg, #0b88d1, #16a8f5)' }
                      : {
                          background: 'var(--surface-muted)',
                          color: 'var(--text-main)',
                          border: '1px solid var(--line)',
                        }
                  }
                >
                  {msg.content}
                </div>
              </div>
            ))}

            {loading && (
              <div className="text-sm" style={{ color: 'var(--text-subtle)' }}>
                正在生成回复...
              </div>
            )}

            {error && (
              <div className="rounded-xl px-4 py-3 text-sm" style={{ color: '#a92929', background: '#fff1f1', border: '1px solid #f5bcbc' }}>
                {error}
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </section>

      <section className="panel p-3 sm:p-4">
        <form onSubmit={handleSend} className="flex flex-col gap-2 sm:flex-row">
          <input
            data-testid="chat-input"
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入你的问题..."
            disabled={loading}
            className="input-base"
          />
          <button
            data-testid="chat-send"
            type="submit"
            disabled={loading || !input.trim()}
            className="btn-primary sm:w-36"
          >
            {loading ? '发送中' : '发送'}
          </button>
        </form>
      </section>
    </div>
  )
}
