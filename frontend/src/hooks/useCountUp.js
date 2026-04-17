import { useEffect, useRef, useState } from 'react'

/**
 * Animates a numeric value from its previous value to `target`.
 * Returns the current animated value (float).
 */
export function useCountUp(target, duration = 650) {
  const [val, setVal] = useState(target)
  const prevRef = useRef(target)
  const rafRef  = useRef(null)

  useEffect(() => {
    const from = prevRef.current
    const to   = target
    if (from === to) return

    cancelAnimationFrame(rafRef.current)
    const start = performance.now()

    const tick = (now) => {
      const t    = Math.min((now - start) / duration, 1)
      const ease = 1 - Math.pow(1 - t, 3)           // ease-out cubic
      setVal(from + (to - from) * ease)
      if (t < 1) {
        rafRef.current = requestAnimationFrame(tick)
      } else {
        setVal(to)
        prevRef.current = to
      }
    }

    rafRef.current = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(rafRef.current)
  }, [target, duration])

  return val
}
