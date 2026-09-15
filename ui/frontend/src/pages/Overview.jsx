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

  if (loading || error || !data) {
    return <StatusNote loading={loading} error={error} />
  }

  return (
    <div className="flex flex-col gap-xl">
      <SectionHeading
        eyebrow={`${data.day_of_week} · ${data.date_formatted}`}
        title="Today at the property"
        support="Every figure below is computed from the property's own records."
        action={
          <button
            type="button"
            onClick={() => setShowDigest(true)}
            className="rounded-sm border border-burgundy px-md py-sm text-sm text-burgundy"
          >
            Send to GM
          </button>
        }
      />

      <HeroFigure
        value={data.hero.value}
        formatter={formatCompactCurrency}
        label={data.hero.label}
        caption={`Exactly ${data.hero.exact_formatted}.`}
        provenance={data.hero.provenance}
      />

      <AlertBlock alert={data.alert} />

      <div>
        <SectionHeading title="The day in figures" />
        <div className="mt-md grid gap-md sm:grid-cols-2 lg:grid-cols-3">
          {data.metrics.map((metric) => (
            <MetricTile
              key={metric.key}
              label={metric.label}
              value={metric.formatted}
              delta={
                metric.delta_formatted
                  ? `${metric.delta_formatted} ${metric.delta_label}`
                  : null
              }
              deltaDirection={metric.delta_direction}
              provenance={metric.provenance}
            />
          ))}
        </div>
      </div>

      <div>
        <SectionHeading
          title="Banquets today"
          support={`Corporate segment margin is running at ${formatPercent(
            data.corporate_margin.value,
          )}.`}
          action={
            <Link
              to="/banquets"
              className="text-sm text-burgundy underline underline-offset-4"
            >
              All events
            </Link>
          }
        />
        <div className="mt-md">
          <DataTable
            columns={[
              { key: 'id', header: 'Event' },
              { key: 'name', header: 'Name' },
              { key: 'segment', header: 'Segment' },
              { key: 'covers', header: 'Covers', align: 'right' },
              {
                key: 'revenue_formatted',
                header: 'Revenue',
                align: 'right',
              },
              {
                key: 'margin_formatted',
                header: 'Margin',
                align: 'right',
              },
            ]}
            rows={data.banquets_today}
            getRowKey={(row) => row.id}
            emptyMessage="No banquet event was held today."
          />
        </div>
      </div>

      {showDigest ? (
        <DigestPreview digest={data.digest} onClose={() => setShowDigest(false)} />
      ) : null}
    </div>
  )
}

export default Overview
