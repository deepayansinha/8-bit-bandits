import { useState, useRef, useEffect } from 'react'

const STARTER_QUESTIONS = [
  'How many sick days do I get?',
  'What do I need to bring on Day 1?',
  'When does my health insurance start?',
  "What's the wifi password?",
]

function SourceTag({ source }) {
  return (
    <span className="source-tag">
      <svg className="doc-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="16" y1="13" x2="8" y2="13" />
        <line x1="16" y1="17" x2="8" y2="17" />
        <polyline points="10 9 9 9 8 9" />
      </svg>
      {source.doc}
      {source.section ? ` · ${source.section}` : ''}
    </span>
  )
}

function Message({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`message ${isUser ? 'message-user' : 'message-bot'}`}>
      <div className="avatar">
        {isUser ? '👤' : '🤖'}
      </div>
      <div className={`bubble ${message.fallback ? 'bubble-fallback' : ''}`}>
        <p className="message-text">{message.text}</p>

        {message.sources && message.sources.length > 0 && (
          <div className="sources-container">
            <span className="sources-label">Verified Sources:</span>
            <div className="sources-list">
              {message.sources.map((s, i) => (
                <SourceTag key={i} source={s} />
              ))}
            </div>
          </div>
        )}

        {message.fallback && message.suggested_contact && (
          <div className="fallback-note">
            💡 Suggested contact: <strong>{message.suggested_contact}</strong>
          </div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [messages, setMessages] = useState([
    {
      role: 'bot',
      text: "Hi! I'm OnboardBot 👋 Ask me anything about company policies, leave, health benefits, or IT setup.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [ingesting, setIngesting] = useState(false)
  const [ingestStatus, setIngestStatus] = useState(null)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  async function sendQuestion(questionText) {
    const q = questionText || input
    if (!q.trim() || loading) return

    setMessages((prev) => [...prev, { role: 'user', text: q }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q }),
      })

      if (!res.ok) throw new Error('API server returned error')
      const data = await res.json()

      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: data.answer,
          sources: data.sources,
          fallback: data.fallback,
          suggested_contact: data.suggested_contact,
        },
      ])
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'bot',
          text: "Something went wrong reaching the server. Ensure the backend API is running.",
          fallback: true,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  async function triggerIngestion() {
    setIngesting(true)
    setIngestStatus('Indexing documents...')
    try {
      const res = await fetch('/ingest', { method: 'POST' })
      const data = await res.json()
      setIngestStatus(`Done! Indexed ${data.documents_indexed} docs (${data.chunks_created} chunks).`)
      setTimeout(() => setIngestStatus(null), 4000)
    } catch (err) {
      setIngestStatus('Ingestion failed. Check backend server.')
      setTimeout(() => setIngestStatus(null), 4000)
    } finally {
      setIngesting(false)
    }
  }

  return (
    <div className="app-container">
      <header className="header">
        <div className="header-brand">
          <div className="logo-badge">🤖</div>
          <div>
            <h1 className="header-title">OnboardBot</h1>
            <p className="header-subtitle">Instant Company Knowledge RAG Engine</p>
          </div>
        </div>
        <div className="header-actions">
          <button
            className="ingest-btn"
            onClick={triggerIngestion}
            disabled={ingesting}
            title="Re-index company documents"
          >
            {ingesting ? '⚡ Indexing...' : '🔄 Re-index Docs'}
          </button>
        </div>
      </header>

      {ingestStatus && (
        <div className="toast-notification">
          ℹ️ {ingestStatus}
        </div>
      )}

      <main className="chat-window">
        {messages.map((m, i) => (
          <Message key={i} message={m} />
        ))}
        {loading && (
          <div className="message message-bot">
            <div className="avatar">🤖</div>
            <div className="bubble bubble-loading">
              <span className="dot"></span>
              <span className="dot"></span>
              <span className="dot"></span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </main>

      {messages.length <= 1 && (
        <div className="starter-questions-container">
          <span className="starter-label">Try asking:</span>
          <div className="starter-chips">
            {STARTER_QUESTIONS.map((q) => (
              <button key={q} className="starter-chip" onClick={() => sendQuestion(q)}>
                {q}
              </button>
            ))}
          </div>
        </div>
      )}

      <footer className="footer">
        <form
          className="input-row"
          onSubmit={(e) => {
            e.preventDefault()
            sendQuestion()
          }}
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about sick leave, health insurance, IT setup..."
            disabled={loading}
          />
          <button type="submit" className="send-btn" disabled={loading || !input.trim()}>
            Send ➔
          </button>
        </form>
      </footer>
    </div>
  )
}
