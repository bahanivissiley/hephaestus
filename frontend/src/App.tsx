import { useState } from "react"

function App() {
  const [message, setMessage] = useState("")
  const [response, setResponse] = useState("")
  const [loading, setLoading] = useState(false)

  const sendMessage = async () => {
    if (!message.trim()) return
    setLoading(true)
    try {
      const res = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history: [] })
      })
      const data = await res.json()
      setResponse(data.message)
    } catch {
      setResponse("Erreur de connexion au serveur")
    }
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
        <div style={{
          display: "flex",
          gap: "0.75rem",
          marginBottom: response ? "1.5rem" : "0"
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

        {/* Response */}
        {response && (
          <div style={{
            background: "rgba(56,189,248,0.05)",
            border: "1px solid rgba(56,189,248,0.2)",
            borderRadius: "10px",
            padding: "1.25rem",
            color: "#e2e8f0",
            fontSize: "0.9rem",
            lineHeight: "1.7",
            maxHeight: "400px",
            overflowY: "auto",
            whiteSpace: "pre-wrap"
          }}>
            {response}
          </div>
        )}
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