import { createContext, useContext, useEffect, useState, type ReactNode } from "react"

export const API = "http://localhost:8000"

type User = { email: string }

type AuthCtx = {
  user: User | null
  token: string | null
  ready: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string) => Promise<void>
  logout: () => void
}

const Ctx = createContext<AuthCtx | null>(null)
const TOKEN_KEY = "tm_token"

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [user, setUser] = useState<User | null>(null)
  const [ready, setReady] = useState(false)

  // Valide le token au montage / changement et récupère l'utilisateur.
  useEffect(() => {
    if (!token) {
      setUser(null)
      setReady(true)
      return
    }
    let cancelled = false
    fetch(`${API}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
      .then(r => (r.ok ? r.json() : Promise.reject()))
      .then(d => {
        if (!cancelled) setUser({ email: d.email })
      })
      .catch(() => {
        if (!cancelled) {
          localStorage.removeItem(TOKEN_KEY)
          setToken(null)
          setUser(null)
        }
      })
      .finally(() => {
        if (!cancelled) setReady(true)
      })
    return () => {
      cancelled = true
    }
  }, [token])

  const authenticate = async (path: "login" | "register", email: string, password: string) => {
    const res = await fetch(`${API}/auth/${path}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    })
    const data = await res.json().catch(() => ({}))
    if (!res.ok) throw new Error(data.detail || "Erreur d'authentification")
    localStorage.setItem(TOKEN_KEY, data.access_token)
    setToken(data.access_token)
    setUser({ email: data.email })
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }

  return (
    <Ctx.Provider
      value={{
        user,
        token,
        ready,
        login: (e, p) => authenticate("login", e, p),
        register: (e, p) => authenticate("register", e, p),
        logout,
      }}
    >
      {children}
    </Ctx.Provider>
  )
}

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth() {
  const c = useContext(Ctx)
  if (!c) throw new Error("useAuth doit être utilisé dans AuthProvider")
  return c
}
