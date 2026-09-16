/*
 * The two charts on the command centre.
 *
 * Both draw only figures the API already computed -- nothing here derives a
 * number. Both are bar charts on purpose: a trading day is a discrete event,
 * and a smooth curve drawn through thirty of them invents values between days
 * that never existed.
 *
 * Series colour is assigned by identity and fixed: dine-in is always indigo,
 * delivery always gold, events always green. The legend carries each series'
 * written total, so the reader never has to rely on colour alone.
 */

import { useState } from 'react'
import { formatCompactCurrency, formatCurrency } from '../lib/format'

const CHANNELS = [
  { key: 'dine_in_revenue', label: 'Dining room', css: 'series-1' },
  { key: 'delivery_revenue', label: 'Delivery', css: 'series-2' },
  { key: 'events_revenue', label: 'Private events', css: 'series-3' },
]

function shortDate(value) {
  const [, month, day] = value.split('-')
  return `${day}/${month}`
}

function niceCeiling(value) {
  if (value <= 0) return 1
  const magnitude = 10 ** Math.floor(Math.log10(value))
  return Math.ceil(value / magnitude) * magnitude
}

/** A tooltip that stays inside the chart however near the edge the cursor is. */
function Tooltip({ x, total, children }) {
  const side = x > 60 ? 'right' : 'left'
  return (
    <div
      className={`chart-tip chart-tip--${side}`}
      style={{ left: `${x}%` }}
      role="status"
    >
      {children}
      {total ? <b className="chart-tip__total">{total}</b> : null}
    </div>
  )
}

function RevenueTrend({ rows }) {
  const [hover, setHover] = useState(null)
  if (!rows?.length) return null

  const maximum = niceCeiling(Math.max(...rows.map((row) => row.total_revenue)))
  const totals = CHANNELS.map((channel) => ({
    ...channel,
    total: rows.reduce((sum, row) => sum + (row[channel.key] || 0), 0),
  }))
  const active = hover === null ? null : rows[hover]

  return (
    <div className="chart">
      <div className="chart-legend">
        {totals.map((channel) => (
          <span key={channel.key}>
            <i className={`swatch swatch--${channel.css}`} aria-hidden="true" />
            {channel.label}
            <b>{formatCompactCurrency(channel.total)}</b>
          </span>
        ))}
      </div>

      <div className="chart-plot" onMouseLeave={() => setHover(null)}>
        <div className="chart-scale" aria-hidden="true">
          <span>{formatCompactCurrency(maximum)}</span>
          <span>{formatCompactCurrency(maximum / 2)}</span>
          <span>0</span>
        </div>

        <div
          className="chart-bars"
          role="img"
          aria-label={`Net sales by channel for each of the ${rows.length} days in the reporting window`}
        >
          {rows.map((row, index) => (
            <button
              type="button"
              key={row.date}
              className={`bar-slot ${hover === index ? 'bar-slot--active' : ''}`}
              style={{ '--i': index }}
              onMouseEnter={() => setHover(index)}
              onFocus={() => setHover(index)}
              onBlur={() => setHover(null)}
              aria-label={`${row.date}: ${formatCurrency(row.total_revenue)}`}
            >
              <span className="bar-stack">
                {CHANNELS.map((channel) => {
                  const value = row[channel.key] || 0
                  if (!value) return null
                  return (
                    <span
                      key={channel.key}
                      className={`bar-part bar-part--${channel.css}`}
                      style={{ height: `${(value / maximum) * 100}%` }}
                    />
                  )
                })}
              </span>
            </button>
          ))}
        </div>

        {active ? (
          <Tooltip
            x={((hover + 0.5) / rows.length) * 100}
            total={formatCurrency(active.total_revenue)}
          >
            <strong>
              {active.day_of_week?.slice(0, 3)} {shortDate(active.date)}
            </strong>
            {CHANNELS.map((channel) =>
              active[channel.key] ? (
                <span key={channel.key}>
                  <i className={`swatch swatch--${channel.css}`} aria-hidden="true" />
                  {channel.label}
                  <em>{formatCurrency(active[channel.key])}</em>
                </span>
              ) : null,
            )}
            <span className="chart-tip__meta">
              {active.covers} covers
            </span>
          </Tooltip>
        ) : null}
      </div>

      <div className="chart-axis-labels" aria-hidden="true">
        <span>{shortDate(rows[0].date)}</span>
        <span>{shortDate(rows[Math.floor((rows.length - 1) / 2)].date)}</span>
        <span>{shortDate(rows[rows.length - 1].date)}</span>
      </div>
    </div>
  )
}

/**
 * Food cost against the standing target.
 *
 * Bars are coloured by state, not by identity: at or under target, over it,
 * and past the escalation threshold the cost policy sets two points above.
 * Those are status colours and carry a written label in the legend, never
 * colour alone.
 */
export function CostTrend({ rows, targetPct = 31 }) {
  const [hover, setHover] = useState(null)
  if (!rows?.length) return null

  const escalation = targetPct + 2
  const ceiling = niceCeiling(Math.max(...rows.map((r) => r.food_cost_pct), escalation) * 1.1)
  const state = (value) =>
    value >= escalation ? 'over' : value > targetPct ? 'warn' : 'ok'
  const active = hover === null ? null : rows[hover]

  return (
    <div className="chart chart--cost">
      <div className="chart-legend">
        <span><i className="swatch swatch--ok" aria-hidden="true" />At or under target</span>
        <span><i className="swatch swatch--warn" aria-hidden="true" />Over target</span>
        <span><i className="swatch swatch--over" aria-hidden="true" />Past escalation</span>
      </div>

      <div className="chart-plot" onMouseLeave={() => setHover(null)}>
        <div className="chart-scale" aria-hidden="true">
          <span>{ceiling}%</span>
          <span>{(ceiling / 2).toFixed(0)}%</span>
          <span>0</span>
        </div>

        <div
          className="chart-bars"
          role="img"
          aria-label={`Food cost percentage for each of the ${rows.length} days, against the ${targetPct}% standing target`}
        >
          <i
            className="target-rule"
            style={{ bottom: `${(targetPct / ceiling) * 100}%` }}
            aria-hidden="true"
          >
            <b>{targetPct}% target</b>
          </i>
          {rows.map((row, index) => (
            <button
              type="button"
              key={row.date}
              className={`bar-slot ${hover === index ? 'bar-slot--active' : ''}`}
              style={{ '--i': index }}
              onMouseEnter={() => setHover(index)}
              onFocus={() => setHover(index)}
              onBlur={() => setHover(null)}
              aria-label={`${row.date}: food cost ${row.food_cost_pct}%`}
            >
              <span className="bar-stack">
                <span
                  className={`bar-part bar-part--${state(row.food_cost_pct)}`}
                  style={{ height: `${(row.food_cost_pct / ceiling) * 100}%` }}
                />
              </span>
            </button>
          ))}
        </div>

        {active ? (
          <Tooltip x={((hover + 0.5) / rows.length) * 100}>
            <strong>
              {active.day_of_week?.slice(0, 3)} {shortDate(active.date)}
            </strong>
            <span>
              Food cost<em>{active.food_cost_pct}%</em>
            </span>
            <span>
              Against target
              <em>
                {active.food_cost_pct > targetPct ? '+' : ''}
                {(active.food_cost_pct - targetPct).toFixed(1)} pts
              </em>
            </span>
            {active.labor_cost_pct ? (
              <span className="chart-tip__meta">
                Prime cost {active.prime_cost_pct}%
              </span>
            ) : null}
          </Tooltip>
        ) : null}
      </div>

      <div className="chart-axis-labels" aria-hidden="true">
        <span>{shortDate(rows[0].date)}</span>
        <span>{shortDate(rows[Math.floor((rows.length - 1) / 2)].date)}</span>
        <span>{shortDate(rows[rows.length - 1].date)}</span>
      </div>
    </div>
  )
}

export default RevenueTrend
