import { useState } from "react"

type StreamEvent =
  | { type: "status"; message: string }
  | { type: "token"; content: string }
  | { type: "done"; message: string; state: Record<string, unknown>; awaiting_info: boolean }
  | { type: "error"; message: string }

type ChatMsg = { role: "user" | "assistant"; content: string }

function App() {
  const [message, setMessage] = useState("")
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [tripState, setTripState] = useState<Record<string, unknown>>({})
  const [status, setStatus] = useState("")
  const [loading, setLoading] = useState(false)

  const appendAssistantText = (text: string) => {
    setMessages(prev => {
      const last = prev[prev.length - 1]
      if (last?.role === "assistant") {
        return [...prev.slice(0, -1), { role: "assistant", content: text }]
      }
      return [...prev, { role: "assistant", content: text }]
    })
  }

  const sendMessage = async () => {
    if (!message.trim() || loading) return
    const userMessage = message
    const historyPayload = messages
    setMessage("")
    setMessages(prev => [...prev, { role: "user", content: userMessage }])
    setLoading(true)
    setStatus("Connexion à l'agent...")

    try {
      const res = await fetch("http://localhost:8000/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage, history: historyPayload, state: tripState })
      })
      if (!res.body) throw new Error("Pas de flux")

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ""
      let text = ""

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })

        // Les événements SSE sont séparés par une ligne vide
        const parts = buffer.split("\n\n")
        buffer = parts.pop() ?? ""

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith("data: ")) continue
          const event: StreamEvent = JSON.parse(line.slice(6))

          if (event.type === "status") {
            setStatus(event.message)
          } else if (event.type === "token") {
            setStatus("")
            text += event.content
            appendAssistantText(text)
          } else if (event.type === "done") {
            setStatus("")
            appendAssistantText(event.message)
            setTripState(event.state ?? {})
          } else if (event.type === "error") {
            setStatus("")
            appendAssistantText(event.message)
          }
        }
      }
    } catch {
      appendAssistantText("Erreur de connexion au serveur")
    }
    setStatus("")
    setLoading(false)
  }

  return (
    <div style={{
      minHeight: "100vh",
      background: "linear-gradient(135deg, #0f172a 0%, #1e293b 100%)",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      fontFamily: "system-ui, sans-serif",
      color: "white",
      padding: "2rem"
    }}>
      {/* Hero */}
      <div style={{ textAlign: "center", marginBottom: "3rem" }}>
        <div style={{
          fontSize: "3rem",
          marginBottom: "1rem"
        }}>✈️</div>
        <h1 style={{
          fontSize: "3rem",
          fontWeight: "700",
          background: "linear-gradient(90deg, #38bdf8, #818cf8)",
          WebkitBackgroundClip: "text",
          WebkitTextFillColor: "transparent",
          margin: "0 0 1rem 0"
        }}>
          TravelMind AI
        </h1>
        <p style={{
          fontSize: "1.2rem",
          color: "#94a3b8",
          maxWidth: "500px"
        }}>
          Votre agent de voyage intelligent. Planification complète, heure par heure.
        </p>
      </div>

      {/* Features */}
      <div style={{
        display: "flex",
        gap: "1.5rem",
        marginBottom: "3rem",
        flexWrap: "wrap",
        justifyContent: "center"
      }}>
        {[
          { icon: "🗺️", text: "Planification jour par jour" },
          { icon: "🏨", text: "Hôtels & restaurants réels" },
          { icon: "🌤️", text: "Météo en temps réel" },
          { icon: "🔄", text: "Alternatives à la demande" }
        ].map((f, i) => (
          <div key={i} style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            borderRadius: "12px",
            padding: "1rem 1.5rem",
            display: "flex",
            alignItems: "center",
            gap: "0.75rem",
            fontSize: "0.9rem",
            color: "#cbd5e1"
          }}>
            <span style={{ fontSize: "1.3rem" }}>{f.icon}</span>
            {f.text}
          </div>
        ))}
      </div>

      {/* Chat box */}
      <div style={{
        width: "100%",
        maxWidth: "700px",
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: "16px",
        padding: "1.5rem"
      }}>
        {/* Conversation */}
        {messages.length > 0 && (
          <div style={{
            display: "flex",
            flexDirection: "column",
            gap: "0.75rem",
            maxHeight: "420px",
            overflowY: "auto",
            marginBottom: "1.5rem"
          }}>
            {messages.map((m, i) => (
              <div key={i} style={{
                alignSelf: m.role === "user" ? "flex-end" : "flex-start",
                maxWidth: "85%",
                background: m.role === "user"
                  ? "linear-gradient(135deg, rgba(56,189,248,0.25), rgba(129,140,248,0.25))"
                  : "rgba(56,189,248,0.05)",
                border: m.role === "user"
                  ? "1px solid rgba(56,189,248,0.35)"
                  : "1px solid rgba(56,189,248,0.2)",
                borderRadius: "10px",
                padding: "0.75rem 1rem",
                color: "#e2e8f0",
                fontSize: "0.9rem",
                lineHeight: "1.7",
                whiteSpace: "pre-wrap"
              }}>
                {m.content}
              </div>
            ))}
          </div>
        )}

        {/* Status (étape en cours côté agent) */}
        {status && (
          <div style={{
            display: "flex",
            alignItems: "center",
            gap: "0.6rem",
            color: "#94a3b8",
            fontSize: "0.85rem",
            fontStyle: "italic",
            padding: "0.5rem 0.25rem",
            marginBottom: "1rem"
          }}>
            <span style={{
              width: "8px",
              height: "8px",
              borderRadius: "50%",
              background: "#38bdf8",
              animation: "pulse 1.2s ease-in-out infinite"
            }} />
            {status}
          </div>
        )}

        {/* Input */}
        <div style={{
          display: "flex",
          gap: "0.75rem"
        }}>
          <input
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={e => e.key === "Enter" && sendMessage()}
            placeholder="Ex: Je veux partir à Tokyo en avril pour 10 jours avec 2000€..."
            style={{
              flex: 1,
              background: "rgba(255,255,255,0.08)",
              border: "1px solid rgba(255,255,255,0.15)",
              borderRadius: "10px",
              padding: "0.875rem 1rem",
              color: "white",
              fontSize: "0.95rem",
              outline: "none"
            }}
          />
          <button
            onClick={sendMessage}
            disabled={loading}
            style={{
              background: loading ? "#475569" : "linear-gradient(135deg, #38bdf8, #818cf8)",
              border: "none",
              borderRadius: "10px",
              padding: "0.875rem 1.5rem",
              color: "white",
              fontWeight: "600",
              cursor: loading ? "not-allowed" : "pointer",
              fontSize: "0.95rem",
              whiteSpace: "nowrap"
            }}
          >
            {loading ? "⏳ En cours..." : "Planifier →"}
          </button>
        </div>
      </div>

      {/* Footer */}
      <p style={{
        marginTop: "2rem",
        color: "#475569",
        fontSize: "0.8rem"
      }}>
        Propulsé par Qwen3 · FastAPI · PostgreSQL · Epitech Lyon 2026
      </p>
    </div>
  )
}

export default App
