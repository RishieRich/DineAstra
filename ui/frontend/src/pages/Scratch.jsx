import DataTable from '../components/DataTable'
import HeroFigure from '../components/HeroFigure'
import MetricTile from '../components/MetricTile'
import ProvenanceLine from '../components/ProvenanceLine'
import SectionHeading from '../components/SectionHeading'
import Shell from '../components/Shell'
import {
  formatCompactCurrency,
  formatCurrency,
  formatDateShort,
  formatPercent,
} from '../lib/format'

/**
 * Development-only scratch route: every primitive on one page so the whole
 * kit can be judged at a glance. Not linked from the nav.
 */
const SAMPLE_ROWS = [
  { id: 'BQ-2026-018', name: 'Solstice Analytics Annual Kickoff', date: '2026-09-02', revenue: 500000, margin: 55.6 },
  { id: 'BQ-2026-021', name: 'Ashford Legal Partners Retreat', date: '2026-09-10', revenue: 450000, margin: 61.5 },
  { id: 'BQ-2026-024', name: 'Blueprint Systems Founders Day', date: '2026-09-14', revenue: 480000, margin: 62.6 },
]

function Scratch() {
  return (
    <Shell user={{ name: 'Rohan Ahuja', role: 'General Manager' }}>
      <div className="flex flex-col gap-xl">
        <SectionHeading
          eyebrow="Component scratch"
          title="Primitives"
          support="Every shared component rendered once, on real-shaped data."
        />

        <HeroFigure
          value={4820000}
          formatter={formatCompactCurrency}
          label="Total revenue, trailing 30 days"
          caption="Dining room, delivery and private event sales combined."
          provenance={{
            source: 'daily_property.json',
            window: '16 August to 14 September 2026',
          }}
        />

        <div>
          <SectionHeading title="Metric tiles" />
          <div className="mt-md grid gap-md sm:grid-cols-2 lg:grid-cols-4">
            <MetricTile
              label="Occupancy"
              value={formatPercent(78.3)}
              delta="+2.1 pts against trailing 30 days"
              deltaDirection="up"
              provenance={{ source: 'daily_property.json', window: '14 September 2026' }}
            />
            <MetricTile
              label="ADR"
              value={formatCurrency(9540)}
              delta="-1.4 pts against trailing 30 days"
              deltaDirection="down"
              provenance={{ source: 'daily_property.json', window: '14 September 2026' }}
            />
            <MetricTile
              label="Food cost"
              value={formatPercent(34.5)}
              delta="+3.5 pts against standing target"
              deltaDirection="down"
              provenance={{ source: 'daily_property.json', window: '14 September 2026' }}
            />
            <MetricTile
              label="Corporate banquet margin"
              value={formatPercent(61.2)}
              provenance={{ source: 'banquets.json', window: 'six corporate events' }}
              emphasis
            />
          </div>
        </div>

        <div>
          <SectionHeading title="Data table" support="Ruled, not filled." />
          <div className="mt-md">
            <DataTable
              columns={[
                { key: 'id', header: 'Event' },
                { key: 'name', header: 'Name' },
                {
                  key: 'date',
                  header: 'Date',
                  render: (row) => formatDateShort(row.date),
                },
                {
                  key: 'revenue',
                  header: 'Revenue',
                  align: 'right',
                  render: (row) => formatCurrency(row.revenue),
                },
                {
                  key: 'margin',
                  header: 'Margin',
                  align: 'right',
                  render: (row) => formatPercent(row.margin),
                },
              ]}
              rows={SAMPLE_ROWS}
              getRowKey={(row) => row.id}
            />
          </div>
        </div>

        <div>
          <SectionHeading title="Provenance line" />
          <div className="mt-md">
            <ProvenanceLine
              provenance={{
                source: 'banquets.json',
                window: 'trailing twelve months',
                note: 'peer average weighted equally per event',
              }}
            />
          </div>
        </div>
      </div>
    </Shell>
  )
}

export default Scratch
