import { Link } from "react-router-dom"
import { Compass } from "lucide-react"

export default function Footer() {
  return (
    <footer className="footer-wrap">
      <div className="footer">
        <div className="container footer-inner">
          <Link to="/" className="brand">
            <Compass size={22} strokeWidth={1.75} />
            TravelMind
          </Link>
          <div className="footer-links">
            <Link to="/explorer">Explorer</Link>
            <Link to="/chat">Planifier mon voyage</Link>
            <Link to="/admin">Admin</Link>
          </div>
          <p className="footer-note">Projet Hephaestus, Epitech Lyon</p>
        </div>
      </div>
    </footer>
  )
}
