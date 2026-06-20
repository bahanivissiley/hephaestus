import { useCallback, useEffect, useState } from "react"
import { Check, X, Inbox, RotateCcw } from "lucide-react"

const API = "http://localhost:8000"

type PendingPlace = {
  id: string
  type: "destination" | "hotel" | "attraction" | "restaurant"
  name: string
  source: string
  description: string | null
  destination?: string
}

const TYPE_LABEL: Record<PendingPlace["type"], string> = {
  destination: "Destination",
  hotel: "Hôtel",
  attraction: "Attraction",
  restaurant: "Restaurant",
}

// Les destinations d'abord : tant qu'une ville n'est pas validée,
// ses lieux validés restent invisibles sur le site.
const TYPE_ORDER: PendingPlace["type"][] = ["destination", "hotel", "attraction", "restaurant"]

export default function Admin() {
  const [items, setItems] = useState<PendingPlace[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [busy, setBusy] = useState<string | null>(null)

  const load = useCallback(() => {
    setLoading(true)
    setError(false)
    fetch(`${API}/places/pending`)
      .then(res => {
        if (!res.ok) throw new Error()
        return res.json()
      })
      .then((data: PendingPlace[]) => {
        const sorted = [...data].sort(
          (a, b) => TYPE_ORDER.indexOf(a.type) - TYPE_ORDER.indexOf(b.type)
        )
        setItems(sorted)
      })
      .catch(() => setError(true))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    load()
  }, [load])

  const act = async (place: PendingPlace, action: "validate" | "reject") => {
    setBusy(place.id)
    try {
      const res =
        action === "validate"
          ? await fetch(`${API}/places/${place.type}/${place.id}/validate`, { method: "PATCH" })
          : await fetch(`${API}/places/${place.type}/${place.id}`, { method: "DELETE" })
      if (!res.ok) throw new Error()
      setItems(prev => prev.filter(p => p.id !== place.id))
    } catch {
      setError(true)
    } finally {
      setBusy(null)
    }
  }

  const hasPendingDestination = items.some(p => p.type === "destination")

  return (
    <main className="container" style={{ maxWidth: 880 }}>
      <div className="explore-head">
        <h1 className="display" style={{ fontSize: "clamp(2rem, 4vw, 2.8rem)" }}>
          Lieux en attente.
        </h1>
        <p className="lead">
          Tout ce que l'agent a découvert. Validez pour publier sur le site, rejetez pour
          supprimer.
        </p>
      </div>

      {hasPendingDestination && (
        <p className="admin-hint">
          Validez la destination avant ses lieux : une ville non validée n'apparaît pas sur le
          site, même si ses hôtels sont approuvés.
        </p>
      )}

      <div className="admin-list">
        {loading &&
          Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="admin-row" aria-hidden="true">
              <div className="admin-row-info" style={{ display: "grid", gap: "0.5rem" }}>
                <div className="skeleton-line shimmer w40" />
                <div className="skeleton-line shimmer w60" />
              </div>
            </div>
          ))}

        {!loading && error && (
          <div className="state-box">
            <h3>Impossible de charger la liste</h3>
            <p>Vérifiez que le serveur est démarré, puis réessayez.</p>
            <button className="btn btn-primary" onClick={load}>
              <RotateCcw size={16} strokeWidth={1.75} />
              Réessayer
            </button>
          </div>
        )}

        {!loading && !error && items.length === 0 && (
          <div className="state-box">
            <Inbox size={44} strokeWidth={1.5} />
            <h3>Rien en attente</h3>
            <p>
              Tout est à jour. Les prochaines découvertes de l'agent apparaîtront ici.
            </p>
          </div>
        )}

        {!loading &&
          !error &&
          items.map(p => (
            <div key={p.id} className="admin-row">
              <span className="place-type">{TYPE_LABEL[p.type]}</span>
              <div className="admin-row-info">
                <h3>
                  {p.name}
                  {p.destination ? ` · ${p.destination}` : ""}
                </h3>
                <p>
                  Source : {p.source}
                  {p.description ? ` · ${p.description}` : ""}
                </p>
              </div>
              <div className="admin-actions">
                <button
                  className="btn btn-primary"
                  disabled={busy === p.id}
                  onClick={() => act(p, "validate")}
                >
                  <Check size={15} strokeWidth={2} />
                  Valider
                </button>
                <button
                  className="btn btn-danger"
                  disabled={busy === p.id}
                  onClick={() => act(p, "reject")}
                >
                  <X size={15} strokeWidth={2} />
                  Rejeter
                </button>
              </div>
            </div>
          ))}
      </div>
    </main>
  )
}
