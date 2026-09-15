import { formatPercent } from '../lib/format'

/**
 * The event margin waterfall: contracted revenue, four cost lines, net.
 *
 * Every bar is drawn as a share of contracted revenue, so the cost segments
 * and the net segment visually sum to the whole bar above them. The backend
 * has already confirmed the arithmetic (waterfall.sums_to_net); this only
 * draws it.
 */
function Waterfall({ waterfall }) {
  const start = waterfall.steps.find((step) => step.kind === 'start')
  const costs = waterfall.steps.filter((step) => step.kind === 'cost')
  const net = waterfall.steps.find((step) => step.kind === 'end')

  return (
    <div className="flex flex-col gap-md">
      <div>
        <div className="flex items-baseline justify-between gap-md">
          <p className="text-sm text-ink">{start.label}</p>
          <p className="font-serif text-xl text-burgundy">{start.formatted}</p>
        </div>
        <div className="mt-xs h-3 w-full rounded-sm bg-burgundy" />
      </div>

      <div>
        <p className="text-xs tracking-[0.14em] text-muted">
          Where it went
        </p>
        <div className="mt-xs flex h-3 w-full overflow-hidden rounded-sm border border-line">
          {costs.map((step) => (
            <div
              key={step.key}
              style={{ width: `${step.share_pct}%` }}
              className="h-full border-r border-paper bg-muted"
              title={`${step.label} ${step.formatted}`}
            />
          ))}
          <div
            style={{ width: `${net.share_pct}%` }}
            className="h-full bg-gold"
            title={`${net.label} ${net.formatted}`}
          />
        </div>
      </div>

      <dl className="flex flex-col gap-sm">
        {costs.map((step) => (
          <div
            key={step.key}
            className="flex items-baseline justify-between gap-md border-b border-line pb-sm"
          >
            <dt className="text-sm text-ink">{step.label}</dt>
            <dd className="text-sm text-muted">
              <span className="text-ink">{step.formatted}</span>{' '}
              {formatPercent(step.share_pct)} of revenue
            </dd>
          </div>
        ))}
        <div className="flex items-baseline justify-between gap-md pt-xs">
          <dt className="font-serif text-xl text-ink">{net.label}</dt>
          <dd className="font-serif text-xl text-burgundy">
            {net.formatted}{' '}
            <span className="text-sm text-muted">
              {formatPercent(net.share_pct)} margin
            </span>
          </dd>
        </div>
      </dl>
    </div>
  )
}

export default Waterfall
