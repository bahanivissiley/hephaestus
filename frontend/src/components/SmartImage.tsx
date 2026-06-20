import { useState } from "react"

type Props = {
  /** Nom du fichier attendu dans frontend/public/images/ (ex: "dest-tokyo.jpg") */
  name?: string
  /** URL directe (ex: image_url venant de l'API) qui prime sur le fichier local */
  src?: string
  /** Graine du visuel de secours si le fichier ou l'URL manque */
  seed: string
  alt: string
  className?: string
  w?: number
  h?: number
  priority?: boolean
}

/**
 * Image avec chaîne de secours : URL API ou fichier local /images/<name>,
 * et si absent, photo de remplacement stable (picsum, seed descriptive).
 * Le site reste donc présentable avant même d'avoir déposé les vraies images.
 */
export default function SmartImage({ name, src, seed, alt, className, w = 900, h = 1200, priority }: Props) {
  const initial = src || (name ? `/images/${name}` : `https://picsum.photos/seed/${seed}/${w}/${h}`)
  const [current, setCurrent] = useState(initial)

  return (
    <img
      src={current}
      alt={alt}
      className={className}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : undefined}
      onError={() => {
        const fallback = `https://picsum.photos/seed/${seed}/${w}/${h}`
        if (current !== fallback) setCurrent(fallback)
      }}
    />
  )
}
