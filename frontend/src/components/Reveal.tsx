import { useEffect, useRef, type ReactNode } from "react"

type Props = {
  children: ReactNode
  delay?: number
  className?: string
}

/** Révèle son contenu à l'entrée dans le viewport (IntersectionObserver + CSS). */
export default function Reveal({ children, delay = 0, className }: Props) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    const io = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          el.classList.add("in")
          io.disconnect()
        }
      },
      { threshold: 0.15 }
    )
    io.observe(el)
    return () => io.disconnect()
  }, [])

  return (
    <div ref={ref} className={`reveal ${className ?? ""}`} style={delay ? { transitionDelay: `${delay}ms` } : undefined}>
      {children}
    </div>
  )
}
