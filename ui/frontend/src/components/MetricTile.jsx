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
    <div className="flex h-full flex-col justify-between rounded-md border border-line bg-paper p-md">
      <p className="text-xs tracking-[0.14em] text-muted">{label}</p>
      <p
        className={`mt-sm font-serif ${
          emphasis ? 'text-4xl' : 'text-3xl'
        } text-burgundy`}
      >
        {value}
      </p>
      {delta ? <p className={`mt-xs text-sm ${deltaTone}`}>{delta}</p> : null}
      {provenance ? (
        <ProvenanceLine provenance={provenance} className="mt-sm" />
      ) : null}
    </div>
  )
}

export default MetricTile
