import { useState } from 'react'

/**
 * One metric: label, formatted value, an optional signed movement, and its
 * provenance. The value arrives already formatted by the backend -- this
 * component never builds a currency string.
 *
 * Provenance is on hover rather than always on screen. Six tiles each
 * carrying three lines of source text turned the most important row on the
 * dashboard into a wall of small print; the claim that every figure is
 * traceable is kept by making it one hover away, not by printing it six
 * times. The tooltip is reachable by keyboard, and the source is still in
 * the DOM for a screen reader.
 */
function MetricTile({ label, value, delta, deltaDirection, provenance, emphasis }) {
  const [open, setOpen] = useState(false)

  const deltaTone =
    deltaDirection === 'up'
      ? 'text-positive'
      : deltaDirection === 'down'
        ? 'text-negative'
        : 'text-muted'

  const parts = provenance
    ? [provenance.source, provenance.window, provenance.note].filter(Boolean)
    : []

  return (
    <div
      className={`metric-card ${emphasis ? 'metric-card--emphasis' : ''}`}
      onMouseEnter={() => setOpen(true)}
      onMouseLeave={() => setOpen(false)}
    >
      <p className="metric-card__label">{label}</p>
      <p className="metric-card__value">{value}</p>
      {delta ? (
        <p className={`metric-card__delta ${deltaTone}`}>{delta}</p>
      ) : (
        <p className="metric-card__delta text-muted">Current period</p>
      )}

      {parts.length ? (
        <>
          <button
            type="button"
            className="metric-card__source-toggle"
            onFocus={() => setOpen(true)}
            onBlur={() => setOpen(false)}
            aria-label={`Where ${label} comes from: ${parts.join('. ')}`}
          >
            Source
          </button>
          {open ? (
            <p className="metric-card__source" role="status">
              {parts.join(' · ')}
            </p>
          ) : null}
        </>
      ) : null}
    </div>
  )
}

export default MetricTile
