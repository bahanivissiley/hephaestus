import { useState } from "react"
import { Link, NavLink } from "react-router-dom"
import { Compass, ArrowRight, User as UserIcon, LogOut } from "lucide-react"
import { useAuth } from "../context/AuthContext"
import AuthModal from "./AuthModal"

export default function Nav() {
  const { user, logout } = useAuth()
  const [authOpen, setAuthOpen] = useState(false)

  return (
    <header className="nav">
      <div className="container nav-inner">
        <Link to="/" className="brand">
          <Compass size={24} strokeWidth={1.75} />
          TravelMind
        </Link>
        <nav className="nav-links">
          <NavLink to="/explorer" className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
            Explorer
          </NavLink>

          {user ? (
            <span className="nav-account">
              <span className="nav-user" title={user.email}>
                <UserIcon size={15} strokeWidth={1.75} />
                {user.email}
              </span>
              <button className="nav-link nav-logout" onClick={logout} aria-label="Se déconnecter">
                <LogOut size={15} strokeWidth={1.75} />
              </button>
            </span>
          ) : (
            <button className="nav-link" onClick={() => setAuthOpen(true)}>
              Connexion
            </button>
          )}

          <Link to="/chat" className="btn btn-primary">
            Planifier mon voyage
            <ArrowRight size={16} strokeWidth={1.75} />
          </Link>
        </nav>
      </div>

      {authOpen && <AuthModal onClose={() => setAuthOpen(false)} />}
    </header>
  )
}
