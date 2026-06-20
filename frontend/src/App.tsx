import { Routes, Route, useLocation } from "react-router-dom"
import { useEffect } from "react"
import Nav from "./components/Nav"
import Footer from "./components/Footer"
import Landing from "./pages/Landing"
import Explore from "./pages/Explore"
import Chat from "./pages/Chat"
import Admin from "./pages/Admin"

function ScrollToTop() {
  const { pathname } = useLocation()
  useEffect(() => {
    window.scrollTo(0, 0)
  }, [pathname])
  return null
}

function App() {
  const { pathname } = useLocation()
  return (
    <>
      <ScrollToTop />
      <Nav />
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/explorer" element={<Explore />} />
        <Route path="/chat" element={<Chat />} />
        <Route path="/admin" element={<Admin />} />
      </Routes>
      {/* Pas de footer sur l'atelier de chat (plein écran) */}
      {pathname !== "/chat" && <Footer />}
    </>
  )
}

export default App
