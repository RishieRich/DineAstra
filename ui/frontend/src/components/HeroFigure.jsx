import { useEffect, useRef, useState } from 'react'
import ProvenanceLine from './ProvenanceLine'

/**
 * The single largest figure on a screen: gold serif on burgundy.
 *
 * It counts up exactly once per signed-in session -- the flag below is
 * module scope, so navigating away and back does not replay it, and a fresh
 * login (a full page load) starts it over. Under prefers-reduced-motion it
 * never animates and the final value is painted immediately.
 */
let hasCountedUpThisSession = false

function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function HeroFigure({ value, formatter, label, caption, provenance }) {
  const shouldAnimate = !hasCountedUpThisSession && !prefersReducedMotion()
  const [shown, setShown] = useState(shouldAnimate ? 0 : value)
  const frameRef = useRef(null)

  useEffect(() => {
    if (!shouldAnimate || typeof value !== 'number') {
      setShown(value)
      return undefined
    }

    hasCountedUpThisSession = true
    const durationMs = 900
    const startedAt = performance.now()

    const step = (now) => {
      const elapsed = now - startedAt
      const progress = Math.min(1, elapsed / durationMs)
      // ease-out cubic: fast first, settles on the true figure
      const eased = 1 - Math.pow(1 - progress, 3)
      setShown(value * eased)
      if (progress < 1) {
        frameRef.current = requestAnimationFrame(step)
      } else {
        setShown(value)
      }
    }

    frameRef.current = requestAnimationFrame(step)
    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  return (
    <div className="rounded-md bg-burgundy p-lg">
      {label ? (
        <p className="text-xs tracking-[0.18em] text-gold-soft">{label}</p>
      ) : null}
      <p className="mt-sm font-serif text-5xl text-gold sm:text-6xl">
        {formatter ? formatter(shown) : shown}
      </p>
      {caption ? <p className="mt-sm text-sm text-gold-soft">{caption}</p> : null}
      {provenance ? (
        <ProvenanceLine provenance={provenance} tone="gold" className="mt-md" />
      ) : null}
    </div>
  )
}

export default HeroFigure
