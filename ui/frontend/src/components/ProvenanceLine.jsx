/**
 * The line under a figure that says where the figure came from.
 * Nothing in this app shows a number without one of these nearby.
 *
 * provenance: { source, window, computed_at, note }
 * tone: "muted" on paper, "gold" on burgundy.
 */
function ProvenanceLine({ provenance, tone = 'muted', className = '' }) {
  if (!provenance) return null

  const parts = [provenance.source, provenance.window, provenance.note].filter(
    Boolean,
  )
  if (parts.length === 0) return null

  const toneClass = tone === 'gold' ? 'text-gold-soft' : 'text-muted'

  return (
    <p className={`text-xs leading-relaxed ${toneClass} ${className}`}>
      {parts.join(' · ')}
    </p>
  )
}

export default ProvenanceLine
