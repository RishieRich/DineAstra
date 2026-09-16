import { useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import AlertBlock from '../components/AlertBlock'
import DataTable from '../components/DataTable'
import DigestPreview from '../components/DigestPreview'
import HeroFigure from '../components/HeroFigure'
import MetricTile from '../components/MetricTile'
import RevenueTrend, { CostTrend } from '../components/RevenueTrend'
import SectionHeading from '../components/SectionHeading'
import StatusNote from '../components/StatusNote'
import { api } from '../lib/api'
import { formatCurrency, formatPercent } from '../lib/format'
import { useResource } from '../lib/useResource'

function Overview() {
  // A link may name the day it wants shown -- Data Studio sends the reader
  // straight to the date they just loaded, rather than to the default.
  const [searchParams] = useSearchParams()
  const [asOfDate, setAsOfDate] = useState(searchParams.get('date') || '')
  // Sixty days by default, not thirty. The documented food-cost step falls on
  // 16 August, and a thirty-day window ending on the demo's business date
  // starts exactly there -- so every bar lands on the same side of the
  // target and the chart has nothing to say. Sixty days spans the step.
  const [windowDays, setWindowDays] = useState(60)
  const { data: resource, error, loading } = useResource(async (token) => {
    const status = await api.dataStatus(token)
    // Open on the business date the property is reporting, not on whatever
    // the latest upload happened to be dated. A file loaded for next week
    // should be reachable from the selector, not become the default view.
    const overview = await api.overview(
      token,
      asOfDate || status.today || status.available_date_range.last,
      windowDays,
    )
    return { overview, status }
  }, [asOfDate, windowDays])
  const [showDigest, setShowDigest] = useState(false)

  if (loading || error || !resource) return <StatusNote loading={loading} error={error} />

  const { overview: data, status } = resource

  const metricByKey = Object.fromEntries(data.metrics.map((metric) => [metric.key, metric]))
  const secondaryByKey = Object.fromEntries(
    data.secondary_metrics.map((metric) => [metric.key, metric]),
  )
  const foodCost = metricByKey.food_cost_pct
  const primeCost = metricByKey.prime_cost_pct
  const gop = metricByKey.gop_pct
  const standards = secondaryByKey.checklist_signoff_pct

  return (
    <div className="page-stack">
      <SectionHeading
        eyebrow={`${data.day_of_week} · ${data.date_formatted}`}
        title="Command centre"
        support="Four outlets, one view: what sold, what it cost, and what needs attention."
        action={
          <div className="heading-actions">
            <Link to="/data" className="secondary-button">Load data</Link>
            <button type="button" onClick={() => setShowDigest(true)} className="primary-button compact-button">GM digest →</button>
          </div>
        }
      />

      <div className="dashboard-filterbar">
        <div>
          <label htmlFor="as-of-date">As of business date</label>
          <input
            id="as-of-date"
            type="date"
            min={status.available_date_range.first}
            max={status.available_date_range.last}
            value={data.date}
            onChange={(event) => setAsOfDate(event.target.value)}
          />
        </div>
        <div>
          <label htmlFor="reporting-window">Reporting window</label>
          <select id="reporting-window" value={windowDays} onChange={(event) => setWindowDays(Number(event.target.value))}>
            <option value={7}>Trailing 7 days</option>
            <option value={30}>Trailing 30 days</option>
            <option value={60}>Trailing 60 days</option>
            <option value={90}>Trailing 90 days</option>
          </select>
        </div>
        <div className="available-range">
          <span>Available data</span>
          <strong>{status.available_date_range.first} → {status.available_date_range.last}</strong>
        </div>
        <div className="last-update">
          <span>Last successful load</span>
          <strong>{status.last_updated_at ? new Date(status.last_updated_at).toLocaleString('en-IN') : 'Seeded sample baseline'}</strong>
        </div>
      </div>

      <div className="overview-hero-grid">
        <HeroFigure
          value={data.hero.value}
          formatter={formatCurrency}
          label={data.hero.label}
          sublabel={data.hero.sublabel}
          delta={data.hero.delta_formatted}
          deltaDirection={data.hero.delta_direction}
          deltaLabel={data.hero.delta_label}
          caption={`${data.period.formatted} across the ${data.window_days}-day reporting window.`}
          provenance={data.hero.provenance}
        />
        <AlertBlock alert={data.alert} />
      </div>

      <section>
        <div className="mini-section-heading">
          <div><p className="eyebrow">The day</p><h3>What the estate traded</h3></div>
          <span>Compared with the same day of the week</span>
        </div>
        <div className="metric-grid cascade">
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

        <div className="metric-strip">
          {data.secondary_metrics.map((metric) => (
            <div key={metric.key} title={`${metric.provenance.source} · ${metric.provenance.window}`}>
              <span>{metric.label}</span>
              <strong>{metric.formatted}</strong>
            </div>
          ))}
        </div>
      </section>

      <div className="chart-grid">
        <section className="surface-card chart-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">Where the sales came from</p>
              <h3>Net sales by channel, day by day</h3>
            </div>
            <span>{data.trend.length} trading days · hover for a day</span>
          </div>
          <RevenueTrend rows={data.trend} />
        </section>
        <section className="surface-card chart-card">
          <div className="card-heading">
            <div>
              <p className="eyebrow">Cost control</p>
              <h3>Food cost vs target</h3>
            </div>
            <span>Hover for a day</span>
          </div>
          <CostTrend rows={data.trend} targetPct={data.food_cost_target_pct} />
        </section>
      </div>

      <div className="overview-lower-grid">
        <section className="surface-card operating-pulse">
          <div className="card-heading">
            <div><p className="eyebrow">Operating pulse</p><h3>Margin and standards</h3></div>
            <Link to="/ask">Ask why →</Link>
          </div>
          <div className="pulse-row">
            <div><span>Prime cost</span><strong>{primeCost?.formatted}</strong></div>
            <div className="pulse-track"><i style={{ width: `${Math.min(primeCost?.value || 0, 100)}%` }} /></div>
            <small>Food {foodCost?.formatted} plus labour. Under 60% is healthy.</small>
          </div>
          <div className="pulse-row pulse-row--positive">
            <div><span>Operating margin</span><strong>{gop?.formatted}</strong></div>
            <div className="pulse-track"><i style={{ width: `${Math.min(gop?.value || 0, 100)}%` }} /></div>
            <small>After prime cost and overhead</small>
          </div>
          <div className="pulse-row pulse-row--gold">
            <div><span>Standards signed off</span><strong>{standards?.formatted}</strong></div>
            <div className="pulse-track"><i style={{ width: `${Math.min(standards?.value || 0, 100)}%` }} /></div>
            <small>34 daily tasks across six departments</small>
          </div>
        </section>

        <section className="surface-card event-card">
          <div className="card-heading">
            <div><p className="eyebrow">Events today</p><h3>Private dining</h3></div>
            <Link to="/banquets">All events →</Link>
          </div>
          <p className="event-margin-note">Corporate events average {formatPercent(data.corporate_margin.value)} margin, against a 60% floor.</p>
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
            emptyMessage="No private event was booked for this date."
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
