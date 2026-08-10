import { useState, useRef, useEffect } from 'react'

const STARTER_QUESTIONS = [
  'How many sick days do I get?',
  'What do I need to bring on Day 1?',
  'When does my health insurance start?',
  "What's the wifi password?", // intentionally out-of-scope, demos the fallback
]

function SourceTag({ source }) {
  return (
    <span className="source-tag">
      📄 {source.doc}
      {source.section ? ` · ${source.section}` : ''}
    </span>
  )
}

function Message({ message }) {
  const isUser = message.role === 'user'
  return (
    <div className={`message ${isUser ? 'message-user' : 'message-bot'}`}>
      <div className={`bubble ${message.fallback ? 'bubble-fallback' : ''}`}>
        <p>{message.text}</p>
        {message.sources && message.sources.length > 0 && (
          <div className="sources">
            {message.sources.map((s, i) => (
              <SourceTag key={i} source={s} />
            ))}
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
      text: "Hi! I'm OnboardBot 👋 Ask me anything about company policy, benefits, or IT setup.",
    },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendQuestion(question) {
    if (!question.trim() || loading) return

    setMessages((prev) => [...prev, { role: 'user', text: question }])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question }),
      })
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
        { role: 'bot', text: "Something went wrong reaching the server. Is the backend running?" },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="app">
      <header className="header">
        <div className="header-title">🤖 OnboardBot</div>
        <div className="header-subtitle">Your company knowledge, one question away</div>
      </header>

      <div className="chat-window">
        {messages.map((m, i) => (
          <Message key={i} message={m} />
        ))}
        {loading && (
          <div className="message message-bot">
            <div className="bubble bubble-loading">Thinking…</div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {messages.length <= 1 && (
        <div className="starter-questions">
          {STARTER_QUESTIONS.map((q) => (
            <button key={q} onClick={() => sendQuestion(q)}>
              {q}
            </button>
          ))}
        </div>
      )}

      <form
        className="input-row"
        onSubmit={(e) => {
          e.preventDefault()
          sendQuestion(input)
        }}
      >
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about leave, benefits, IT setup…"
        />
        <button type="submit" disabled={loading}>
          Send
        </button>
      </form>
    </div>
  )
}
