import { useCallback, useEffect, useLayoutEffect, useRef, useState, type ReactNode } from "react"
import {
  Send,
  Compass,
  Check,
  CloudSun,
  BedDouble,
  Plane,
  Database,
  Brain,
  Save,
  Globe,
  Sparkles,
  MapPin,
  CalendarDays,
  Hourglass,
  Wallet,
  Star,
  RefreshCw,
  NotebookPen,
  X,
  Menu,
  Plus,
  Trash2,
  MessageSquare,
} from "lucide-react"
import SmartImage from "../components/SmartImage"
import { API, useAuth } from "../context/AuthContext"

type Card = {
  name: string
  image_url: string | null
  subtitle: string
  price: string
  rating: number | null
}

type Category = "hotel" | "attraction" | "restaurant"

type TripDestination = {
  name: string
  country: string | null
  image_url: string | null
}

type TripState = {
  destination: string | null
  origine: string | null
  date_depart: string | null
  duree_jours: number | null
  budget: number | null
}

type ConversationSummary = { id: string; title: string; updated_at: string }

type Weather = { temp_c: string; description: string; humidity: string; wind_kmph: string }
type Flight = { airline: string; price: string; duration: string }
type ItineraryDay = { day: number; theme: string; slots: { time: string; place_name: string }[] }

type StreamEvent =
  | { type: "status"; message: string }
  | { type: "token"; content: string }
  | { type: "trip"; state: TripState; destination: TripDestination | null }
  | { type: "places"; category: Category; items: Card[] }
  | { type: "weather"; temp_c: string; description: string; humidity: string; wind_kmph: string }
  | { type: "flights"; items: Flight[]; date: string | null }
  | { type: "itinerary"; days: ItineraryDay[] }
  | { type: "done"; message: string; state: TripState }
  | { type: "error"; message: string }

type ChatMsg = { role: "user" | "assistant"; content: string }

const SUGGESTIONS = [
  "5 jours à Tokyo en avril, budget 2000 €",
  "Un week-end à Lisbonne en amoureux",
  "Marrakech en famille, plutôt culture et gastronomie",
]

const CATEGORY_LABEL: Record<Category, string> = {
  hotel: "Hôtels",
  attraction: "Attractions",
  restaurant: "Restaurants",
}

function statusIcon(message: string) {
  const m = message.toLowerCase()
  if (m.includes("météo")) return CloudSun
  if (m.includes("hôtel")) return BedDouble
  if (m.includes("vol")) return Plane
  if (m.includes("base de données")) return Database
  if (m.includes("analyse")) return Brain
  if (m.includes("sauvegarde")) return Save
  if (m.includes("recherche")) return Globe
  return Sparkles
}

/** Convertit le markdown léger de l'agent (###, **, listes) en éléments React, sans innerHTML. */
function renderAgentText(text: string): ReactNode[] {
  const bold = (line: string, key: string): ReactNode[] =>
    line.split(/\*\*(.+?)\*\*/g).map((part, i) =>
      i % 2 === 1 ? <strong key={`${key}-${i}`}>{part}</strong> : part
    )

  const nodes: ReactNode[] = []
  let listItems: ReactNode[] = []
  const flushList = (key: string) => {
    if (listItems.length) {
      nodes.push(<ul key={key}>{listItems}</ul>)
      listItems = []
    }
  }

  text.split("\n").forEach((rawLine, i) => {
    const line = rawLine.trim()
    if (!line || line === "---") {
      flushList(`ul-${i}`)
      return
    }
    if (/^#{2,4}\s/.test(line)) {
      flushList(`ul-${i}`)
      nodes.push(<h4 key={`h-${i}`}>{bold(line.replace(/^#{2,4}\s*/, ""), `h-${i}`)}</h4>)
    } else if (/^[-*]\s/.test(line)) {
      listItems.push(<li key={`li-${i}`}>{bold(line.replace(/^[-*]\s*/, ""), `li-${i}`)}</li>)
    } else {
      flushList(`ul-${i}`)
      nodes.push(<p key={`p-${i}`}>{bold(line, `p-${i}`)}</p>)
    }
  })
  flushList("ul-end")
  return nodes
}

export default function Chat() {
  const [message, setMessage] = useState("")
  const [messages, setMessages] = useState<ChatMsg[]>([])
  const [statuses, setStatuses] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  // Carnet
  const [tripState, setTripState] = useState<TripState | Record<string, never>>({})
  const [destination, setDestination] = useState<TripDestination | null>(null)
  const [places, setPlaces] = useState<Partial<Record<Category, Card[]>>>({})
  const [weather, setWeather] = useState<Weather | null>(null)
  const [flights, setFlights] = useState<Flight[]>([])
  const [itinerary, setItinerary] = useState<ItineraryDay[]>([])
  const [carnetOpen, setCarnetOpen] = useState(false)
  const [swapBusy, setSwapBusy] = useState<string | null>(null)

  // Auth + persistance des conversations
  const { token, user } = useAuth()
  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [convId, setConvId] = useState<string | null>(null)
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const saveDirty = useRef(false)
  const convIdRef = useRef<string | null>(null)
  convIdRef.current = convId
  // Nom de la destination courante (pour rafraîchir le carnet si elle change).
  const destNameRef = useRef<string | null>(null)

  const authHeaders = useCallback(
    (): Record<string, string> => (token ? { Authorization: `Bearer ${token}` } : {}),
    [token],
  )

  const refreshConversations = useCallback(async () => {
    if (!token) {
      setConversations([])
      return
    }
    try {
      const r = await fetch(`${API}/conversations`, { headers: authHeaders() })
      if (r.ok) setConversations(await r.json())
    } catch {
      /* hors ligne : on garde la liste actuelle */
    }
  }, [token, authHeaders])

  useEffect(() => {
    refreshConversations()
  }, [refreshConversations])

  const resetCarnet = () => {
    setDestination(null)
    setPlaces({})
    setWeather(null)
    setFlights([])
    setItinerary([])
  }

  const newTrip = () => {
    setMessages([])
    setTripState({})
    resetCarnet()
    destNameRef.current = null
    setConvId(null)
    setStatuses([])
    setSidebarOpen(false)
  }

  const loadConversation = async (id: string) => {
    try {
      const r = await fetch(`${API}/conversations/${id}`, { headers: authHeaders() })
      if (!r.ok) return
      const d = await r.json()
      const c = d.carnet ?? {}
      setMessages(d.messages ?? [])
      setTripState(d.state ?? {})
      setDestination(c.destination ?? null)
      setPlaces(c.places ?? {})
      setWeather(c.weather ?? null)
      setFlights(c.flights ?? [])
      setItinerary(c.itinerary ?? [])
      destNameRef.current = c.destination?.name ?? null
      setConvId(id)
      setStatuses([])
      setSidebarOpen(false)
    } catch {
      /* ignore */
    }
  }

  const deleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    try {
      await fetch(`${API}/conversations/${id}`, { method: "DELETE", headers: authHeaders() })
    } catch {
      /* ignore */
    }
    if (id === convId) newTrip()
    refreshConversations()
  }

  const scrollRef = useRef<HTMLDivElement>(null)
  // Suit le bas de la conversation pendant la génération, mais ne ramène
  // pas l'utilisateur de force s'il est remonté pour relire.
  const pinnedRef = useRef(true)
  const onChatScroll = () => {
    const el = scrollRef.current
    if (!el) return
    pinnedRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 120
  }
  useLayoutEffect(() => {
    const el = scrollRef.current
    if (el && pinnedRef.current) el.scrollTop = el.scrollHeight
  }, [messages, statuses, loading])

  // Sauvegarde le voyage courant (messages + carnet + état). Crée la
  // conversation au premier enregistrement, la met à jour ensuite.
  const persistConversation = useCallback(async () => {
    if (!token) return
    const carnet = { destination, places, weather, flights, itinerary }
    const body = JSON.stringify({ messages, carnet, state: tripState })
    try {
      const id = convIdRef.current
      const r = await fetch(`${API}/conversations${id ? `/${id}` : ""}`, {
        method: id ? "PUT" : "POST",
        headers: { "Content-Type": "application/json", ...authHeaders() },
        body,
      })
      if (r.ok) {
        const d = await r.json()
        if (!id) setConvId(d.id)
        refreshConversations()
      }
    } catch {
      /* sauvegarde best-effort */
    }
  }, [token, destination, places, weather, flights, itinerary, messages, tripState, authHeaders, refreshConversations])

  // Déclenché quand la génération se termine (loading → false) si un envoi
  // a eu lieu : on enregistre avec l'état le plus à jour.
  useEffect(() => {
    if (loading || !saveDirty.current) return
    saveDirty.current = false
    void persistConversation()
  }, [loading, persistConversation])

  const appendAssistantText = (text: string) => {
    setMessages(prev => {
      const last = prev[prev.length - 1]
      if (last?.role === "assistant") {
        return [...prev.slice(0, -1), { role: "assistant", content: text }]
      }
      return [...prev, { role: "assistant", content: text }]
    })
  }

  const sendMessage = async (forced?: string) => {
    const userMessage = (forced ?? message).trim()
    if (!userMessage || loading) return
    const historyPayload = messages
    setMessage("")
    setMessages(prev => [...prev, { role: "user", content: userMessage }])
    setLoading(true)
    setStatuses([])
    pinnedRef.current = true

    try {
      const res = await fetch(`${API}/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage, history: historyPayload, state: tripState }),
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

        const parts = buffer.split("\n\n")
        buffer = parts.pop() ?? ""

        for (const part of parts) {
          const line = part.trim()
          if (!line.startsWith("data: ")) continue
          const event: StreamEvent = JSON.parse(line.slice(6))

          if (event.type === "status") {
            setStatuses(prev => [...prev, event.message])
          } else if (event.type === "token") {
            text += event.content
            appendAssistantText(text)
          } else if (event.type === "trip") {
            setTripState(event.state)
            if (event.destination) {
              const newName = event.destination.name
              // Destination changée en cours de route → on rafraîchit le carnet
              // (sinon les hôtels/lieux de l'ancienne ville resteraient affichés).
              if (
                destNameRef.current &&
                destNameRef.current.toLowerCase() !== newName.toLowerCase()
              ) {
                setPlaces({})
                setWeather(null)
                setFlights([])
                setItinerary([])
              }
              destNameRef.current = newName
              setDestination(event.destination)
            }
          } else if (event.type === "places") {
            setPlaces(prev => ({ ...prev, [event.category]: event.items }))
          } else if (event.type === "weather") {
            setWeather(event)
          } else if (event.type === "flights") {
            setFlights(event.items)
          } else if (event.type === "itinerary") {
            setItinerary(event.days)
          } else if (event.type === "done") {
            appendAssistantText(event.message)
            setTripState(event.state ?? {})
            setStatuses([])
          } else if (event.type === "error") {
            appendAssistantText(event.message)
            setStatuses([])
          }
        }
      }
    } catch {
      appendAssistantText("Erreur de connexion au serveur. Vérifiez que le backend est démarré.")
    }
    setStatuses([])
    if (user) saveDirty.current = true
    setLoading(false)
  }

  const swapPlace = async (category: Category, card: Card, index: number) => {
    const destName = destination?.name ?? (tripState as TripState).destination
    if (!destName || swapBusy) return
    setSwapBusy(card.name)
    try {
      const st = tripState as TripState
      const budgetMax =
        category === "hotel" && st.budget && st.duree_jours
          ? Math.floor(st.budget / st.duree_jours)
          : null
      const res = await fetch(`${API}/chat/alternative`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          place_type: category,
          current_place: card.name,
          destination: destName,
          budget_max: budgetMax,
        }),
      })
      const data = await res.json()
      const alt = data.alternative
      if (alt) {
        const next: Card = {
          name: alt.name,
          image_url: alt.image_url ?? null,
          subtitle: alt.category ?? alt.cuisine ?? "",
          price:
            category === "hotel"
              ? alt.price_min
                ? `${alt.price_min} à ${alt.price_max} € / nuit`
                : ""
              : category === "attraction"
                ? (alt.price ?? "")
                : (alt.price_range ?? ""),
          rating: alt.rating ?? null,
        }
        setPlaces(prev => {
          const list = [...(prev[category] ?? [])]
          list[index] = next
          return { ...prev, [category]: list }
        })
      }
    } catch {
      /* silencieux : la carte reste en place */
    } finally {
      setSwapBusy(null)
    }
  }

  const st = tripState as TripState
  const carnetHasContent =
    destination || weather || flights.length > 0 || itinerary.length > 0 ||
    Object.values(places).some(list => list && list.length > 0)
  const carnetCount =
    Object.values(places).reduce((n, list) => n + (list?.length ?? 0), 0) + itinerary.length

  return (
    <div className="workshop">
      {/* ───── Sidebar : mes voyages ───── */}
      <aside className={`chat-sidebar${sidebarOpen ? " open" : ""}`} aria-label="Mes voyages">
        <div className="sidebar-head">
          <span>Mes voyages</span>
          <button className="icon-btn" onClick={() => setSidebarOpen(false)} aria-label="Fermer">
            <X size={16} strokeWidth={2} />
          </button>
        </div>
        <button className="sidebar-new" onClick={newTrip}>
          <Plus size={15} strokeWidth={2} />
          Nouveau voyage
        </button>
        {!user && (
          <p className="sidebar-hint">Connectez-vous pour sauvegarder et retrouver vos voyages.</p>
        )}
        {user && conversations.length === 0 && (
          <p className="sidebar-hint">Aucun voyage sauvegardé pour l'instant.</p>
        )}
        <div className="sidebar-list">
          {conversations.map(c => (
            <div key={c.id} className={`sidebar-item${c.id === convId ? " active" : ""}`}>
              <button className="sidebar-item-main" onClick={() => loadConversation(c.id)}>
                <MessageSquare size={14} strokeWidth={1.75} />
                <span className="sidebar-item-title">{c.title}</span>
              </button>
              <button
                className="sidebar-del"
                onClick={e => deleteConversation(c.id, e)}
                aria-label="Supprimer"
              >
                <Trash2 size={13} strokeWidth={1.75} />
              </button>
            </div>
          ))}
        </div>
      </aside>
      {sidebarOpen && <div className="sidebar-backdrop" onClick={() => setSidebarOpen(false)} />}

      {/* ───── Conversation ───── */}
      <div className="chat-col">
        <div className="chat-topbar">
          <button
            className="icon-btn"
            onClick={() => setSidebarOpen(o => !o)}
            aria-label="Mes voyages"
          >
            <Menu size={18} strokeWidth={1.75} />
          </button>
          <button className="chat-new" onClick={newTrip}>
            <Plus size={15} strokeWidth={2} />
            Nouveau
          </button>
        </div>
        <div className="chat-scroll" ref={scrollRef} onScroll={onChatScroll}>
          {messages.length === 0 && !loading && (
            <div className="chat-suggest">
              <Compass size={40} strokeWidth={1.5} color="var(--ember)" />
              <h2>Où partons-nous ?</h2>
              <p>
                Décrivez votre voyage en une phrase. L'agent collecte ce qui manque, vérifie
                les données en temps réel et remplit votre carnet de voyage.
              </p>
              <div className="suggest-chips">
                {SUGGESTIONS.map(s => (
                  <button key={s} className="pill" onClick={() => sendMessage(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="msg-user">
                <span>{m.content}</span>
              </div>
            ) : (
              <div key={i} className="msg-agent">
                <span className="agent-mark">
                  <Compass size={17} strokeWidth={1.75} />
                </span>
                <div className="agent-text">{renderAgentText(m.content)}</div>
              </div>
            )
          )}

          {statuses.length > 0 && (
            <div className="activity" aria-live="polite">
              {statuses.map((s, i) => {
                const Icon = statusIcon(s)
                const isCurrent = i === statuses.length - 1
                return (
                  <div key={i} className={`activity-row${isCurrent ? " current" : ""}`}>
                    {isCurrent ? (
                      <Icon size={15} strokeWidth={1.75} className="live" />
                    ) : (
                      <Check size={15} strokeWidth={2} className="check" />
                    )}
                    {s}
                  </div>
                )
              })}
            </div>
          )}
        </div>

        <div className="chat-input-bar">
          <div className="chat-input-inner">
            <label className="chat-input">
              <input
                value={message}
                onChange={e => setMessage(e.target.value)}
                onKeyDown={e => e.key === "Enter" && sendMessage()}
                placeholder="Décrivez votre voyage..."
                aria-label="Votre message à l'agent"
              />
              <button
                className="btn btn-primary"
                onClick={() => sendMessage()}
                disabled={loading}
                aria-label="Envoyer"
              >
                <Send size={16} strokeWidth={1.75} />
              </button>
            </label>
          </div>
        </div>
      </div>

      {/* ───── Carnet de voyage ───── */}
      <aside className={`carnet${carnetOpen ? " open" : ""}`} aria-label="Carnet de voyage">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <p className="carnet-title">Votre voyage</p>
          <button
            className="pcard-swap"
            style={{ display: carnetOpen ? "inline-flex" : "none", margin: 0 }}
            onClick={() => setCarnetOpen(false)}
          >
            <X size={14} strokeWidth={2} />
            Fermer
          </button>
        </div>

        {!carnetHasContent && (
          <div className="carnet-empty">
            <NotebookPen size={36} strokeWidth={1.5} />
            <p>
              Votre carnet se remplit pendant la conversation : destination, météo, hôtels,
              lieux à visiter et itinéraire apparaîtront ici.
            </p>
          </div>
        )}

        {destination && (
          <div className="carnet-dest">
            <SmartImage
              src={destination.image_url ?? undefined}
              seed={`travelmind-dest-${destination.name.toLowerCase()}`}
              alt={destination.name}
              w={860}
              h={300}
            />
            <div className="carnet-dest-label">
              <p className="name">{destination.name}</p>
              {destination.country && <p className="meta">{destination.country}</p>}
            </div>
          </div>
        )}

        {(destination || st.origine || st.budget || st.date_depart || st.duree_jours) && (
          <div className="trip-chips">
            <span className={`trip-chip${st.destination ? "" : " ghost"}`}>
              <MapPin size={13} strokeWidth={1.75} />
              {st.destination ?? "Destination ?"}
            </span>
            <span className={`trip-chip${st.origine ? "" : " ghost"}`}>
              <Plane size={13} strokeWidth={1.75} />
              {st.origine ? `Départ : ${st.origine}` : "Départ ?"}
            </span>
            <span className={`trip-chip${st.date_depart ? "" : " ghost"}`}>
              <CalendarDays size={13} strokeWidth={1.75} />
              {st.date_depart ?? "Dates ?"}
            </span>
            <span className={`trip-chip${st.duree_jours ? "" : " ghost"}`}>
              <Hourglass size={13} strokeWidth={1.75} />
              {st.duree_jours ? `${st.duree_jours} jours` : "Durée ?"}
            </span>
            <span className={`trip-chip${st.budget ? "" : " ghost"}`}>
              <Wallet size={13} strokeWidth={1.75} />
              {st.budget ? `${st.budget} €` : "Budget ?"}
            </span>
          </div>
        )}

        {weather && (
          <div className="weather-chip">
            <CloudSun size={26} strokeWidth={1.5} />
            <div>
              {weather.temp_c}°C, {weather.description}
              <div className="sub">
                Humidité {weather.humidity}%, vent {weather.wind_kmph} km/h
              </div>
            </div>
          </div>
        )}

        {(["hotel", "attraction", "restaurant"] as Category[]).map(cat => {
          const list = places[cat]
          if (!list?.length) return null
          return (
            <div key={cat}>
              <p className="carnet-title" style={{ marginBottom: "0.7rem" }}>
                {CATEGORY_LABEL[cat]}
              </p>
              <div className="pcard-row">
                {list.map((c, i) => (
                  <article key={`${c.name}-${i}`} className="pcard">
                    <div className="pcard-img">
                      <SmartImage
                        src={c.image_url ?? undefined}
                        seed={`travelmind-${cat}-${c.name.toLowerCase().replace(/\s+/g, "-")}`}
                        alt={c.name}
                        w={400}
                        h={240}
                      />
                    </div>
                    <div className="pcard-body">
                      <h5>{c.name}</h5>
                      {c.subtitle && <p className="sub">{c.subtitle}</p>}
                      <div className="pcard-foot">
                        <span className="price">{c.price}</span>
                        {c.rating != null && (
                          <span className="rating">
                            <Star size={11} strokeWidth={1.75} fill="currentColor" />
                            {c.rating}
                          </span>
                        )}
                      </div>
                      <button
                        className="pcard-swap"
                        disabled={swapBusy !== null}
                        onClick={() => swapPlace(cat, c, i)}
                      >
                        <RefreshCw
                          size={12}
                          strokeWidth={2}
                          className={swapBusy === c.name ? "live" : undefined}
                        />
                        Remplacer
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            </div>
          )
        })}

        {flights.length > 0 && (
          <div>
            <p className="carnet-title" style={{ marginBottom: "0.7rem" }}>
              Vols
            </p>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
              {flights.map((f, i) => (
                <div key={i} className="weather-chip" style={{ padding: "0.65rem 0.9rem" }}>
                  <Plane size={18} strokeWidth={1.75} />
                  <div>
                    {f.airline}
                    <div className="sub">
                      {f.price}, durée {f.duration}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {itinerary.length > 0 && (
          <div>
            <p className="carnet-title" style={{ marginBottom: "0.8rem" }}>
              Itinéraire
            </p>
            <div className="tl">
              {itinerary.map(day => (
                <div key={day.day}>
                  <p className="tl-day-name">
                    Jour {day.day}
                    {day.theme ? ` : ${day.theme}` : ""}
                  </p>
                  {day.slots.length > 0 && (
                    <div className="tl-slots">
                      {day.slots.map((s, i) => (
                        <div key={i} className="tl-slot">
                          <span className="time">{s.time}</span>
                          <span>{s.place_name}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}
      </aside>

      {/* Bascule carnet (mobile) */}
      <button className="btn btn-primary carnet-toggle" onClick={() => setCarnetOpen(o => !o)}>
        <NotebookPen size={16} strokeWidth={1.75} />
        Carnet{carnetCount > 0 ? ` (${carnetCount})` : ""}
      </button>
    </div>
  )
}
