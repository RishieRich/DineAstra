import { useNavigate } from 'react-router-dom'
import ProvenanceLine from './ProvenanceLine'

/**
 * The one thing worth the GM's attention today. Clicking it carries the
 * question straight into Ask, pre-filled -- the alert and the answer are the
 * same thread, not two screens.
 */
function AlertBlock({ alert }) {
  const navigate = useNavigate()

  if (!alert) {
    return (
      <div className="rounded-md border border-line p-lg">
        <p className="text-xs tracking-[0.14em] text-muted">Today</p>
        <p className="mt-sm font-serif text-2xl text-ink">Nothing needs you.</p>
        <p className="mt-sm text-sm text-muted">
          No threshold in the property&rsquo;s own policies was crossed today.
        </p>
      </div>
    )
  }

  return (
    <button
      type="button"
      onClick={() => navigate('/ask', { state: { question: alert.question } })}
      className="w-full rounded-md border border-burgundy bg-burgundy p-lg text-left"
    >
      <p className="text-xs tracking-[0.14em] text-gold-soft">
        Needs your attention
      </p>
      <p className="mt-sm font-serif text-2xl text-gold">{alert.headline}</p>
      <p className="mt-sm text-sm text-gold-soft">{alert.detail}</p>
      <p className="mt-md text-sm text-gold">
        Ask Darpan: {alert.question}
      </p>
      <ProvenanceLine
        provenance={alert.provenance}
        tone="gold"
        className="mt-md"
      />
    </button>
  )
}

export default AlertBlock
