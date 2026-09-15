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
      <div className="attention-card attention-card--quiet">
        <p className="eyebrow">Today</p>
        <p className="attention-card__title">Nothing needs you.</p>
        <p className="attention-card__copy">
          No threshold in the workspace policies was crossed today.
        </p>
      </div>
    )
  }

  return (
    <button
      type="button"
      onClick={() => navigate('/ask', { state: { question: alert.question } })}
      className="attention-card"
    >
      <p className="eyebrow eyebrow--gold">
        Needs your attention
      </p>
      <p className="attention-card__title">{alert.headline}</p>
      <p className="attention-card__copy">{alert.detail}</p>
      <p className="attention-card__ask">
        Ask DineAstra: {alert.question} →
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
