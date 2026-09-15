import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import DataTable from '../components/DataTable'
import SectionHeading from '../components/SectionHeading'
import StatusNote from '../components/StatusNote'
import { api } from '../lib/api'
import { formatDateShort } from '../lib/format'
import { useResource } from '../lib/useResource'

function Banquets() {
  const [segment, setSegment] = useState(null)
  const navigate = useNavigate()
  const { data, error, loading } = useResource(
    (token) => api.banquetEvents(token, segment),
    [segment],
  )

  if (loading || error || !data) {
    return <StatusNote loading={loading} error={error} />
  }

  const filters = [{ key: null, label: 'All segments' }].concat(
    data.segments.map((s) => ({ key: s, label: s })),
  )

  return (
    <div className="flex flex-col gap-lg">
      <SectionHeading
        eyebrow="Banquets and events"
        title="Every event, at its settled margin"
        support="Settled margin, never quoted margin, per the costing policy."
      />

      <div className="flex flex-wrap gap-sm">
        {filters.map((filter) => {
          const active = filter.key === segment
          return (
            <button
              key={filter.label}
              type="button"
              onClick={() => setSegment(filter.key)}
              aria-pressed={active}
              className={`rounded-sm border px-md py-xs text-sm ${
                active
                  ? 'border-burgundy bg-burgundy text-gold'
                  : 'border-line text-ink'
              }`}
            >
              {filter.label}
            </button>
          )
        })}
      </div>

      <DataTable
        columns={[
          { key: 'id', header: 'Event' },
          { key: 'name', header: 'Name' },
          { key: 'segment', header: 'Segment' },
          {
            key: 'date',
            header: 'Date',
            render: (row) => formatDateShort(row.date),
          },
          { key: 'covers', header: 'Covers', align: 'right' },
          { key: 'revenue_formatted', header: 'Revenue', align: 'right' },
          {
            key: 'margin_formatted',
            header: 'Margin',
            align: 'right',
            render: (row) => (
              <span className={row.below_floor ? 'text-negative' : 'text-ink'}>
                {row.margin_formatted}
                {row.below_floor ? ' below floor' : ''}
              </span>
            ),
          },
        ]}
        rows={data.events}
        getRowKey={(row) => row.id}
        onRowClick={(row) => navigate(`/banquets/${row.id}`)}
      />
    </div>
  )
}

export default Banquets
