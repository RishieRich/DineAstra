import ProvenanceLine from './ProvenanceLine'

/**
 * One metric: label, formatted value, an optional signed movement, and its
 * provenance. The value arrives already formatted by the backend -- this
 * component never builds a currency string.
 */
function MetricTile({ label, value, delta, deltaDirection, provenance, emphasis }) {
  const deltaTone =
    deltaDirection === 'up'
      ? 'text-positive'
      : deltaDirection === 'down'
        ? 'text-negative'
        : 'text-muted'

  return (
    <div className={`metric-card ${emphasis ? 'metric-card--emphasis' : ''}`}>
      <p className="metric-card__label">{label}</p>
      <p
        className="metric-card__value"
      >
        {value}
      </p>
      {delta ? <p className={`metric-card__delta ${deltaTone}`}>{delta}</p> : <p className="metric-card__delta text-muted">Current period</p>}
      {provenance ? (
        <ProvenanceLine provenance={provenance} className="metric-card__source" />
      ) : null}
    </div>
  )
}

export default MetricTile
