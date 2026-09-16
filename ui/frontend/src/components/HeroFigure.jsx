import { useEffect, useRef, useState } from 'react'
import ProvenanceLine from './ProvenanceLine'

/**
 * The single largest figure on a screen: gold serif on burgundy.
 *
 * It counts up exactly once per signed-in session: the flag is held in
 * sessionStorage, so navigating away and back does not replay it and neither
 * does a refresh. Signing out clears it, so the next login counts up again.
 * Under prefers-reduced-motion it never animates and the final value is
 * painted immediately.
 */
const COUNTED_KEY = 'dineastra.heroCounted'

function hasCountedUp() {
  try {
    return window.sessionStorage.getItem(COUNTED_KEY) === 'yes'
  } catch {
    return false
  }
}

function markCountedUp() {
  try {
    window.sessionStorage.setItem(COUNTED_KEY, 'yes')
  } catch {
    /* storage blocked: the figure still lands on the right value */
  }
}

export function resetHeroCountUp() {
  try {
    window.sessionStorage.removeItem(COUNTED_KEY)
  } catch {
    /* nothing to clear */
  }
}

function prefersReducedMotion() {
  if (typeof window === 'undefined' || !window.matchMedia) return false
  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function HeroFigure({
  value,
  formatter,
  label,
  sublabel,
  delta,
  deltaDirection,
  deltaLabel,
  caption,
  provenance,
}) {
  const shouldAnimate = !hasCountedUp() && !prefersReducedMotion()
  const [shown, setShown] = useState(shouldAnimate ? 0 : value)
  const frameRef = useRef(null)
  const settleRef = useRef(null)

  useEffect(() => {
    if (!shouldAnimate || typeof value !== 'number') {
      setShown(value)
      return undefined
    }

    markCountedUp()
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

    // requestAnimationFrame does not fire while the tab is in the background,
    // which would leave the largest figure on the screen frozen part-way up.
    // This settles it on the true value regardless of whether a frame ever ran.
    settleRef.current = setTimeout(() => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
      setShown(value)
    }, durationMs + 200)

    return () => {
      if (frameRef.current) cancelAnimationFrame(frameRef.current)
      if (settleRef.current) clearTimeout(settleRef.current)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value])

  return (
    <div className="hero-figure">
      {label ? <p className="hero-figure__label">{label}</p> : null}
      <p className="hero-figure__value">{formatter ? formatter(shown) : shown}</p>
      {sublabel ? <p className="hero-figure__sublabel">{sublabel}</p> : null}
      {delta ? (
        <p className={`hero-figure__delta hero-figure__delta--${deltaDirection || 'flat'}`}>
          <b>{delta}</b> {deltaLabel}
        </p>
      ) : null}
      {caption ? <p className="hero-figure__caption">{caption}</p> : null}
      {provenance ? (
        <ProvenanceLine provenance={provenance} tone="gold" className="hero-figure__provenance" />
      ) : null}
    </div>
  )
}

export default HeroFigure
