import { Link, useNavigate, useParams } from 'react-router-dom'
import DataTable from '../components/DataTable'
import ProvenanceLine from '../components/ProvenanceLine'
import SectionHeading from '../components/SectionHeading'
import StatusNote from '../components/StatusNote'
import Waterfall from '../components/Waterfall'
import { api } from '../lib/api'
import { formatDateShort } from '../lib/format'
import { useResource } from '../lib/useResource'

function BanquetDetail() {
  const { eventId } = useParams()
  const navigate = useNavigate()
  const { data, error, loading } = useResource(
    (token) => api.banquetEvent(token, eventId),
    [eventId],
  )

  if (loading || error || !data) {
    return <StatusNote loading={loading} error={error} />
  }

  const { event, waterfall, peer, cause } = data

  return (
    <div className="flex flex-col gap-xl">
      <div>
        <Link
          to="/banquets"
          className="text-sm text-burgundy underline underline-offset-4"
        >
          Back to all events
        </Link>
        <SectionHeading
          eyebrow={`${event.id} · ${event.date_formatted}`}
          title={event.name}
          support={`${event.segment} · ${event.covers} covers · ${event.venue}`}
        />
      </div>

      <div className="grid gap-xl lg:grid-cols-2">
        <div>
          <SectionHeading title="Where the money went" />
          <div className="mt-md">
            <Waterfall waterfall={waterfall} />
          </div>
        </div>

        <div className="flex flex-col gap-lg">
          <div>
            <SectionHeading title="Against its peers" />
            <div className="mt-md rounded-md border border-line p-md">
              <p className="text-sm text-muted">
                {peer.segment} average across {peer.event_count} events
              </p>
              <p className="mt-xs font-serif text-3xl text-burgundy">
                {peer.average_margin_formatted}
              </p>
              <p className="mt-sm text-sm text-ink">
                This event sits{' '}
                <span
                  className={
                    peer.delta_pts < 0 ? 'text-negative' : 'text-positive'
                  }
                >
                  {peer.delta_formatted}
                </span>{' '}
                against that average.
              </p>
              <ProvenanceLine provenance={peer.provenance} className="mt-md" />
            </div>
          </div>

          {cause ? (
            <div className="rounded-md border border-burgundy p-md">
              <p className="text-xs tracking-[0.14em] text-muted">
                Why the margin sits here
              </p>
              <p className="mt-sm font-serif text-xl text-burgundy">
                {cause.headline}
              </p>
              <p className="mt-sm text-sm text-ink">{cause.detail}</p>
              {cause.citation ? (
                <blockquote className="mt-md border-l-2 border-gold pl-md text-sm text-muted">
                  {cause.policy_string}
                  <footer className="mt-sm text-xs text-muted">
                    {cause.citation.document_title}, section{' '}
                    {cause.citation.heading}
                  </footer>
                </blockquote>
              ) : null}
            </div>
          ) : (
            <div className="rounded-md border border-line p-md">
              <p className="text-sm text-muted">
                This event settled within its segment floor. Nothing needs
                explaining.
              </p>
            </div>
          )}
        </div>
      </div>

      <div>
        <SectionHeading
          title="Every event in this segment"
          support="Equally weighted per event, so one large event does not mask a pattern."
        />
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
                key: 'margin_formatted',
                header: 'Margin',
                align: 'right',
                render: (row) => (
                  <span
                    className={row.id === event.id ? 'text-burgundy' : 'text-ink'}
                  >
                    {row.margin_formatted}
                    {row.id === event.id ? ' this event' : ''}
                  </span>
                ),
              },
            ]}
            rows={peer.peers}
            getRowKey={(row) => row.id}
            onRowClick={(row) => navigate(`/banquets/${row.id}`)}
          />
        </div>
      </div>
    </div>
  )
}

export default BanquetDetail
