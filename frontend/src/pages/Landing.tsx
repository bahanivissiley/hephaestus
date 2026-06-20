import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  ArrowRight,
  ArrowUpRight,
  MessagesSquare,
  Radar,
  CalendarCheck,
  PlaneTakeoff,
  CloudSun,
  BadgeCheck,
  Brain,
} from "lucide-react"
import SmartImage from "../components/SmartImage"
import Reveal from "../components/Reveal"

type Destination = {
  name: string
  country: string
  budget_min: number | null
  budget_max: number | null
}

const FALLBACK_DESTINATIONS: Destination[] = [
  { name: "Tokyo", country: "Japon", budget_min: 100, budget_max: 200 },
  { name: "Paris", country: "France", budget_min: 90, budget_max: 180 },
  { name: "Marrakech", country: "Maroc", budget_min: 40, budget_max: 90 },
  { name: "Lisbonne", country: "Portugal", budget_min: 60, budget_max: 120 },
]

function slugify(name: string) {
  // Retire les accents (caracteres combinants apres normalisation NFD)
  return name
    .toLowerCase()
    .normalize("NFD")
    .split("")
    .filter(c => c.charCodeAt(0) < 0x0300 || c.charCodeAt(0) > 0x036f)
    .join("")
    .replace(/\s+/g, "-")
}

export default function Landing() {
  const [destinations, setDestinations] = useState<Destination[]>(FALLBACK_DESTINATIONS)

  useEffect(() => {
    fetch("http://localhost:8000/destinations")
      .then(res => res.json())
      .then((data: Destination[]) => {
        if (Array.isArray(data) && data.length >= 4) setDestinations(data.slice(0, 4))
      })
      .catch(() => {})
  }, [])

  return (
    <main>
      {/* ───── Hero : split asymétrique ───── */}
      <section className="hero">
        <div className="container hero-grid">
          <div className="hero-copy">
            <h1 className="display">
              Votre voyage, planifié <span className="accent-word">heure par heure</span>.
            </h1>
            <p className="lead">
              Une conversation avec notre agent suffit : vols, hôtels, restaurants, météo et
              lieux à visiter, tout est vérifié en temps réel.
            </p>
            <div className="hero-ctas">
              <Link to="/chat" className="btn btn-primary">
                Planifier mon voyage
                <ArrowRight size={18} strokeWidth={1.75} />
              </Link>
              <Link to="/explorer" className="btn btn-ghost">
                Explorer les destinations
              </Link>
            </div>
          </div>
          <div className="hero-visual">
            <div className="hero-ring" aria-hidden="true" />
            <SmartImage
              name="hero-main.jpg"
              seed="travelmind-hero-city-sunset"
              alt="Voyageuse face à une vieille ville au coucher du soleil"
              className="hero-main-img"
              w={960}
              h={1200}
              priority
            />
            <SmartImage
              name="hero-detail.jpg"
              seed="travelmind-hero-detail-journal"
              alt="Carnet de voyage, billets et appareil photo sur une table"
              className="hero-detail-img"
              w={640}
              h={640}
            />
          </div>
        </div>
      </section>

      {/* ───── Destinations : galerie asymétrique ───── */}
      <section className="section" id="destinations">
        <div className="container">
          <Reveal>
            <div className="section-head">
              <h2 className="display">Commencez par une ville.</h2>
              <p className="lead">
                Quatre destinations vérifiées par notre équipe. D'autres arrivent à mesure que
                l'agent les découvre.
              </p>
            </div>
          </Reveal>
          <div className="dest-grid">
            {destinations.map((d, i) => (
              <Reveal key={d.name} delay={i * 70} className={i === 3 ? "dest-wide" : undefined}>
                <Link to={`/explorer?destination=${encodeURIComponent(d.name)}`} className="dest-card">
                  <SmartImage
                    name={`dest-${slugify(d.name)}.jpg`}
                    seed={`travelmind-${slugify(d.name)}`}
                    alt={`${d.name}, ${d.country}`}
                    w={900}
                    h={1100}
                  />
                  <div className="dest-card-label">
                    <div>
                      <p className="name">{d.name}</p>
                      <p className="meta">
                        {d.country}
                        {d.budget_min && d.budget_max ? ` · ${d.budget_min} à ${d.budget_max} € / jour` : ""}
                      </p>
                    </div>
                    <span className="go" aria-hidden="true">
                      <ArrowUpRight size={18} strokeWidth={1.75} />
                    </span>
                  </div>
                </Link>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* ───── Méthode : étapes + aperçu réel du chat ───── */}
      <section className="section" id="methode">
        <div className="container method-grid">
          <Reveal>
            <div>
              <div className="section-head" style={{ marginBottom: "1.2rem" }}>
                <h2 className="display">Une conversation suffit.</h2>
              </div>
              <div className="steps">
                <div className="step">
                  <span className="step-icon">
                    <MessagesSquare size={22} strokeWidth={1.75} />
                  </span>
                  <div>
                    <h3>Dites votre envie</h3>
                    <p>
                      Une ville, des dates, un budget. S'il manque quelque chose, l'agent pose
                      la bonne question.
                    </p>
                  </div>
                </div>
                <div className="step">
                  <span className="step-icon">
                    <Radar size={22} strokeWidth={1.75} />
                  </span>
                  <div>
                    <h3>Il vérifie tout</h3>
                    <p>Vols, hôtels, météo du jour : les données sont réelles, pas inventées.</p>
                  </div>
                </div>
                <div className="step">
                  <span className="step-icon">
                    <CalendarCheck size={22} strokeWidth={1.75} />
                  </span>
                  <div>
                    <h3>Partez avec un plan</h3>
                    <p>
                      Un itinéraire jour par jour, heure par heure, avec des alternatives à la
                      demande.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </Reveal>
          <Reveal delay={120}>
            {/* Aperçu réel du produit : mini version de la conversation */}
            <div className="chat-preview" aria-label="Aperçu d'une conversation avec l'agent">
              <p className="bubble user">Je veux 5 jours à Tokyo en avril, autour de 2000 €.</p>
              <p className="status">
                <span className="status-dot" aria-hidden="true" />
                Vérification de la météo à Tokyo...
              </p>
              <p className="bubble agent">
                Jour 1 : Asakusa au lever du jour, le Senso-ji à 8h30 avant la foule, puis le
                quartier de Yanaka à pied. Déjeuner chez Onigiri Bongo, 12h30...
              </p>
            </div>
          </Reveal>
        </div>
      </section>

      {/* ───── Bloc sombre : l'agent (bento) + appel final ───── */}
      <div className="dark-block">
        <section className="section">
          <div className="container">
            <Reveal>
              <div className="section-head">
                <p className="eyebrow">Sous le capot</p>
                <h2 className="display">Un agent, pas un simple chatbot.</h2>
              </div>
            </Reveal>
            <div className="bento">
              <Reveal className="bento-cell bento-img">
                <SmartImage
                  name="agent-cote.jpg"
                  seed="travelmind-coast-aerial"
                  alt="Vue aérienne d'un littoral au soleil"
                  w={900}
                  h={1100}
                />
              </Reveal>
              <Reveal delay={60}>
                <div className="bento-cell" style={{ height: "100%" }}>
                  <PlaneTakeoff size={26} strokeWidth={1.75} />
                  <h3>Vols et hôtels en direct</h3>
                  <p>Les prix viennent de Booking.com au moment où vous demandez.</p>
                </div>
              </Reveal>
              <Reveal delay={120}>
                <div className="bento-cell" style={{ height: "100%" }}>
                  <CloudSun size={26} strokeWidth={1.75} />
                  <h3>Météo réelle</h3>
                  <p>La météo du jour entre dans le planning, pas une moyenne de saison.</p>
                </div>
              </Reveal>
              <Reveal delay={90}>
                <div className="bento-cell bento-ember" style={{ height: "100%" }}>
                  <BadgeCheck size={26} strokeWidth={1.75} />
                  <h3>Lieux vérifiés</h3>
                  <p>Chaque découverte de l'agent est validée par notre équipe avant publication.</p>
                </div>
              </Reveal>
              <Reveal delay={150}>
                <div className="bento-cell" style={{ height: "100%" }}>
                  <Brain size={26} strokeWidth={1.75} />
                  <h3>Il retient vos envies</h3>
                  <p>Budget, dates, préférences : la conversation garde le fil, vous ne répétez rien.</p>
                </div>
              </Reveal>
            </div>
          </div>
        </section>

        <div className="container cta-band">
          <Reveal>
            <h2 className="display">Prêt à partir ?</h2>
          </Reveal>
          <Reveal delay={100}>
            <Link to="/chat" className="btn btn-primary">
              Planifier mon voyage
              <ArrowRight size={18} strokeWidth={1.75} />
            </Link>
          </Reveal>
        </div>
      </div>
    </main>
  )
}
