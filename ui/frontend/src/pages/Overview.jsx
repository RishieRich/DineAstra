import { useState } from 'react'
import { Link } from 'react-router-dom'
import AlertBlock from '../components/AlertBlock'
import DataTable from '../components/DataTable'
import DigestPreview from '../components/DigestPreview'
import HeroFigure from '../components/HeroFigure'
import MetricTile from '../components/MetricTile'
import SectionHeading from '../components/SectionHeading'
import StatusNote from '../components/StatusNote'
import { api } from '../lib/api'
import { formatCompactCurrency, formatPercent } from '../lib/format'
import { useResource } from '../lib/useResource'

function Overview() {
  const { data, error, loading } = useResource((token) => api.overview(token))
  const [showDigest, setShowDigest] = useState(false)

  if (loading || error || !data) return <StatusNote loading={loading} error={error} />

  const metricByKey = Object.fromEntries(data.metrics.map((metric) => [metric.key, metric]))
  const foodCost = metricByKey.food_cost_pct
  const gop = metricByKey.gop_pct
  const standards = metricByKey.checklist_signoff_pct

  return (
    <div className="page-stack">
      <SectionHeading
        eyebrow={`${data.day_of_week} · ${data.date_formatted}`}
        title="Command centre"
        support="One operating view across revenue, margin, events and daily standards."
        action={
          <div className="heading-actions">
            <Link to="/data" className="secondary-button">Load data</Link>
            <button type="button" onClick={() => setShowDigest(true)} className="primary-button compact-button">GM digest →</button>
          </div>
        }
      />

      <div className="overview-hero-grid">
        <HeroFigure
          value={data.hero.value}
          formatter={formatCompactCurrency}
          label="Portfolio revenue · trailing 30 days"
          caption={`Exact value ${data.hero.exact_formatted}. Includes the latest accepted version of every loaded outlet-day.`}
          provenance={data.hero.provenance}
        />
        <AlertBlock alert={data.alert} />
      </div>

      <section>
        <div className="mini-section-heading">
          <div><p className="eyebrow">Daily pulse</p><h3>The business in six signals</h3></div>
          <span>Updated from {data.mode}</span>
        </div>
        <div className="metric-grid">
          {data.metrics.map((metric) => (
            <MetricTile
              key={metric.key}
              label={metric.label}
              value={metric.formatted}
              delta={metric.delta_formatted ? `${metric.delta_formatted} ${metric.delta_label}` : null}
              deltaDirection={metric.delta_direction}
              provenance={metric.provenance}
            />
          ))}
        </div>
      </section>

      <div className="overview-lower-grid">
        <section className="surface-card operating-pulse">
          <div className="card-heading">
            <div><p className="eyebrow">Operating pulse</p><h3>Margin and standards</h3></div>
            <Link to="/ask">Ask why →</Link>
          </div>
          <div className="pulse-row">
            <div><span>Food cost</span><strong>{foodCost?.formatted}</strong></div>
            <div className="pulse-track"><i style={{ width: `${Math.min(foodCost?.value || 0, 100)}%` }} /></div>
            <small>Target 31.0%</small>
          </div>
          <div className="pulse-row pulse-row--positive">
            <div><span>GOP margin</span><strong>{gop?.formatted}</strong></div>
            <div className="pulse-track"><i style={{ width: `${Math.min(gop?.value || 0, 100)}%` }} /></div>
            <small>Current period</small>
          </div>
          <div className="pulse-row pulse-row--gold">
            <div><span>Standards signed off</span><strong>{standards?.formatted}</strong></div>
            <div className="pulse-track"><i style={{ width: `${Math.min(standards?.value || 0, 100)}%` }} /></div>
            <small>Daily completion</small>
          </div>
        </section>

        <section className="surface-card event-card">
          <div className="card-heading">
            <div><p className="eyebrow">Events today</p><h3>Banquet book</h3></div>
            <Link to="/banquets">All events →</Link>
          </div>
          <p className="event-margin-note">Corporate segment margin is {formatPercent(data.corporate_margin.value)}.</p>
          <DataTable
            columns={[
              { key: 'id', header: 'Event', nowrap: true },
              { key: 'name', header: 'Name' },
              { key: 'covers', header: 'Covers', align: 'right', nowrap: true },
              { key: 'revenue_formatted', header: 'Revenue', align: 'right' },
              { key: 'margin_formatted', header: 'Margin', align: 'right' },
            ]}
            rows={data.banquets_today}
            getRowKey={(row) => row.id}
            emptyMessage="No banquet event was held today."
          />
        </section>
      </div>

      <section className="roadmap-strip">
        <div><p className="eyebrow eyebrow--gold">Product roadmap</p><h3>Clearly separated from the working prototype</h3></div>
        <span>Direct POS sync</span><span>Loyalty wallet</span><span>Maintenance SLA</span><span>Menu engineering</span>
      </section>

      {showDigest ? <DigestPreview digest={data.digest} onClose={() => setShowDigest(false)} /> : null}
    </div>
  )
}

export default Overview
