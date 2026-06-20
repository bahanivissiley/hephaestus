import { useCallback, useEffect, useMemo, useState } from "react"
import { useSearchParams } from "react-router-dom"
import { MapPin, Search, Wallet, Star, Clock, UtensilsCrossed, Compass, RotateCcw } from "lucide-react"
import SmartImage from "../components/SmartImage"

const API = "http://localhost:8000"

type Place = {
  id: string
  type: "hotel" | "attraction" | "restaurant"
  name: string
  destination: string
  country: string
  category?: string
  price_min?: number | null
  price_max?: number | null
  price?: string | null
  price_range?: string | null
  duration_hours?: number | null
  cuisine?: string | null
  rating: number | null
  location?: string | null
  description?: string | null
  image_url?: string | null
}

type DestinationOption = { name: string }

const CATEGORIES = [
  { key: "", label: "Tous" },
  { key: "hotel", label: "Hôtels" },
  { key: "attraction", label: "Attractions" },
  { key: "restaurant", label: "Restaurants" },
] as const

const TYPE_LABEL: Record<Place["type"], string> = {
  hotel: "Hôtel",
  attraction: "Attraction",
  restaurant: "Restaurant",
}

function placePrice(p: Place): string | null {
  if (p.type === "hotel" && p.price_min != null) {
    return p.price_max && p.price_max !== p.price_min
      ? `${p.price_min} à ${p.price_max} € / nuit`
      : `${p.price_min} € / nuit`
  }
  if (p.type === "attraction") return p.price ?? null
  if (p.type === "restaurant") return p.price_range ?? null
  return null
}

function placeMeta(p: Place): string {
  if (p.type === "restaurant" && p.cuisine) return p.cuisine
  if (p.type === "attraction" && p.duration_hours) return `Environ ${p.duration_hours} h de visite`
  if (p.type === "hotel" && p.category) return p.category
  return p.location ?? ""
}

export default function Explore() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [category, setCategory] = useState<string>(searchParams.get("category") ?? "")
  const [destination, setDestination] = useState<string>(searchParams.get("destination") ?? "")
  const [budget, setBudget] = useState<string>("")
  const [query, setQuery] = useState<string>("")

  const [destinations, setDestinations] = useState<DestinationOption[]>([])
  const [places, setPlaces] = useState<Place[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [shown, setShown] = useState(24)

  useEffect(() => {
    fetch(`${API}/destinations`)
      .then(res => res.json())
      .then((data: DestinationOption[]) => Array.isArray(data) && setDestinations(data))
      .catch(() => {})
  }, [])

  const load = useCallback(() => {
    setLoading(true)
    setError(false)
    setShown(24)
    const params = new URLSearchParams({ limit: "100" })
    if (category) params.set("category", category)
    if (destination) params.set("destination", destination)
    if (budget) params.set("budget_max", budget)

    fetch(`${API}/places?${params}`)
      .then(res => {
        if (!res.ok) throw new Error()
        return res.json()
      })
      .then((data: Place[]) => setPlaces(Array.isArray(data) ? data : []))
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [category, destination, budget])

  useEffect(() => {
    load()
  }, [load])

  // Garde l'URL en phase avec les filtres (partage de lien possible)
  useEffect(() => {
    const next = new URLSearchParams()
    if (category) next.set("category", category)
    if (destination) next.set("destination", destination)
    setSearchParams(next, { replace: true })
  }, [category, destination, setSearchParams])

  const visible = useMemo(() => {
    if (!query.trim()) return places
    const q = query.trim().toLowerCase()
    return places.filter(p => p.name.toLowerCase().includes(q))
  }, [places, query])

  const resetFilters = () => {
    setCategory("")
    setDestination("")
    setBudget("")
    setQuery("")
  }

  return (
    <main>
      <div className="container explore-head">
        <h1 className="display">Explorer les lieux.</h1>
        <p className="lead">
          Hôtels, attractions et restaurants approuvés par notre équipe, ville par ville.
        </p>
      </div>

      <div className="filter-bar">
        <div className="container filter-inner">
          <div className="pills" role="group" aria-label="Filtrer par catégorie">
            {CATEGORIES.map(c => (
              <button
                key={c.key}
                className={`pill${category === c.key ? " on" : ""}`}
                onClick={() => setCategory(c.key)}
              >
                {c.label}
              </button>
            ))}
          </div>

          <label className="filter-field">
            <MapPin size={16} strokeWidth={1.75} />
            <select value={destination} onChange={e => setDestination(e.target.value)} aria-label="Ville">
              <option value="">Toutes les villes</option>
              {destinations.map(d => (
                <option key={d.name} value={d.name}>
                  {d.name}
                </option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <Wallet size={16} strokeWidth={1.75} />
            <input
              type="number"
              min={0}
              placeholder="Budget max €"
              value={budget}
              onChange={e => setBudget(e.target.value)}
              aria-label="Budget maximum par nuit en euros"
            />
          </label>

          <label className="filter-field">
            <Search size={16} strokeWidth={1.75} />
            <input
              type="search"
              placeholder="Rechercher"
              value={query}
              onChange={e => setQuery(e.target.value)}
              aria-label="Rechercher un lieu par nom"
            />
          </label>
        </div>
      </div>

      <div className="container">
        {!loading && !error && (
          <p className="results-meta">
            {visible.length} {visible.length > 1 ? "lieux" : "lieu"}
            {destination ? ` à ${destination}` : ""}
          </p>
        )}

        <div className="place-grid">
          {loading &&
            Array.from({ length: 6 }).map((_, i) => (
              <div key={i} className="skeleton-card" aria-hidden="true">
                <div className="skeleton-img shimmer" />
                <div className="skeleton-body">
                  <div className="skeleton-line shimmer w40" />
                  <div className="skeleton-line shimmer" />
                  <div className="skeleton-line shimmer w60" />
                </div>
              </div>
            ))}

          {!loading && error && (
            <div className="state-box">
              <Compass size={44} strokeWidth={1.5} />
              <h3>Impossible de charger les lieux</h3>
              <p>Vérifiez que le serveur est démarré, puis réessayez.</p>
              <button className="btn btn-primary" onClick={load}>
                <RotateCcw size={16} strokeWidth={1.75} />
                Réessayer
              </button>
            </div>
          )}

          {!loading && !error && visible.length === 0 && (
            <div className="state-box">
              <MapPin size={44} strokeWidth={1.5} />
              <h3>Aucun lieu ne correspond</h3>
              <p>Essayez une autre ville, élargissez le budget ou videz la recherche.</p>
              <button className="btn btn-ghost" onClick={resetFilters}>
                Réinitialiser les filtres
              </button>
            </div>
          )}

          {!loading &&
            !error &&
            visible.slice(0, shown).map(p => (
              <article key={p.id} className="place-card">
                <div className="place-card-img">
                  <SmartImage
                    src={p.image_url ?? undefined}
                    seed={`travelmind-${p.type}-${p.name.toLowerCase().replace(/\s+/g, "-")}`}
                    alt={`${p.name}, ${p.destination}`}
                    w={800}
                    h={600}
                  />
                </div>
                <div className="place-card-body">
                  <span className="place-type">{TYPE_LABEL[p.type]}</span>
                  <h3>{p.name}</h3>
                  <p className="place-meta">
                    {p.type === "restaurant" ? (
                      <UtensilsCrossed size={14} strokeWidth={1.75} />
                    ) : p.type === "attraction" ? (
                      <Clock size={14} strokeWidth={1.75} />
                    ) : (
                      <MapPin size={14} strokeWidth={1.75} />
                    )}
                    {placeMeta(p)} · {p.destination}
                  </p>
                  <div className="place-foot">
                    <span className="place-price">{placePrice(p) ?? ""}</span>
                    {p.rating != null && (
                      <span className="place-rating">
                        <Star size={14} strokeWidth={1.75} fill="currentColor" />
                        {p.rating}/10
                      </span>
                    )}
                  </div>
                </div>
              </article>
            ))}
        </div>

        {!loading && !error && visible.length > shown && (
          <div style={{ display: "flex", justifyContent: "center", paddingBottom: "4.5rem" }}>
            <button className="btn btn-ghost" onClick={() => setShown(s => s + 24)}>
              Voir plus ({visible.length - shown} restants)
            </button>
          </div>
        )}
      </div>
    </main>
  )
}
