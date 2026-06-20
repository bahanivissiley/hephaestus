import { useState } from "react"
import { X, LogIn, UserPlus } from "lucide-react"
import { useAuth } from "../context/AuthContext"

export default function AuthModal({ onClose }: { onClose: () => void }) {
  const { login, register } = useAuth()
  const [mode, setMode] = useState<"login" | "register">("login")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setBusy(true)
    try {
      if (mode === "login") await login(email, password)
      else await register(email, password)
      onClose()
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur")
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="auth-overlay" onClick={onClose}>
      <div className="auth-modal" onClick={e => e.stopPropagation()}>
        <button className="auth-close" onClick={onClose} aria-label="Fermer">
          <X size={18} strokeWidth={2} />
        </button>

        <h3>{mode === "login" ? "Connexion" : "Créer un compte"}</h3>
        <p className="auth-sub">
          {mode === "login"
            ? "Retrouvez vos voyages sauvegardés."
            : "Sauvegardez vos carnets de voyage et votre historique."}
        </p>

        <form onSubmit={submit} className="auth-form">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={e => setEmail(e.target.value)}
              required
              autoComplete="email"
              placeholder="vous@exemple.com"
            />
          </label>
          <label>
            Mot de passe
            <input
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              required
              minLength={6}
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              placeholder="••••••••"
            />
          </label>

          {error && <p className="auth-error">{error}</p>}

          <button type="submit" className="btn btn-primary auth-submit" disabled={busy}>
            {mode === "login" ? <LogIn size={16} strokeWidth={1.75} /> : <UserPlus size={16} strokeWidth={1.75} />}
            {busy ? "…" : mode === "login" ? "Se connecter" : "S'inscrire"}
          </button>
        </form>

        <button
          className="auth-switch"
          onClick={() => {
            setMode(mode === "login" ? "register" : "login")
            setError(null)
          }}
        >
          {mode === "login" ? "Pas encore de compte ? S'inscrire" : "Déjà un compte ? Se connecter"}
        </button>
      </div>
    </div>
  )
}
