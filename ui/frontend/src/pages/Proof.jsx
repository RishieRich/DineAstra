import DataTable from '../components/DataTable'
import ProvenanceLine from '../components/ProvenanceLine'
import SectionHeading from '../components/SectionHeading'
import StatusNote from '../components/StatusNote'
import { api } from '../lib/api'
import { useResource } from '../lib/useResource'

/**
 * Proof: two requisitions raised the same day for the same item, side by
 * side, with the rule that caught them. The pair is computed by the API, not
 * chosen by this screen.
 */
function SubmissionCard({ side }) {
  return (
    <div className="flex h-full flex-col rounded-md border border-line p-md">
      <p className="text-xs tracking-[0.14em] text-muted">{side.verdict}</p>
      <p className="mt-sm font-serif text-3xl text-burgundy">
        {side.unit_cost_formatted}
        <span className="ml-sm text-sm text-muted">per unit</span>
      </p>
      <dl className="mt-md flex flex-col gap-sm text-sm">
        <div className="flex justify-between gap-md border-b border-line pb-xs">
          <dt className="text-muted">Reference</dt>
          <dd className="text-ink">{side.id}</dd>
        </div>
        <div className="flex justify-between gap-md border-b border-line pb-xs">
          <dt className="text-muted">Department</dt>
          <dd className="text-ink">{side.department}</dd>
        </div>
        <div className="flex justify-between gap-md border-b border-line pb-xs">
          <dt className="text-muted">Vendor</dt>
          <dd className="text-ink">{side.vendor}</dd>
        </div>
        <div className="flex justify-between gap-md border-b border-line pb-xs">
          <dt className="text-muted">Quantity</dt>
          <dd className="text-ink">{side.quantity}</dd>
        </div>
        <div className="flex justify-between gap-md">
          <dt className="text-muted">Line total</dt>
          <dd className="text-ink">{side.total_cost_formatted}</dd>
        </div>
      </dl>
    </div>
  )
}

function Proof() {
  const { data, error, loading } = useResource((token) => api.submissions(token))

  if (loading || error || !data) {
    return <StatusNote loading={loading} error={error} />
  }

  const pair = data.contrast_pair

  return (
    <div className="flex flex-col gap-xl">
      <SectionHeading
        eyebrow={`Requisitions · ${data.date_formatted}`}
        title="Proof"
        support={`${data.count} requisition lines worth ${data.total_value_formatted} were raised today.`}
      />

      {pair ? (
        <div>
          <SectionHeading
            title={`Two rates for ${pair.item}, same day`}
            support={pair.rule}
          />

          {/* Side by side from 768px up; stacked below it. */}
          <div className="mt-md grid gap-md md:grid-cols-2">
            <SubmissionCard side={pair.baseline} />
            <SubmissionCard side={pair.outlier} />
          </div>

          <div className="mt-md rounded-md border border-burgundy p-md">
            <p className="text-sm text-ink">
              The spread is {pair.spread_formatted}, worth{' '}
              {pair.value_at_risk_formatted} on the dearer line alone. Both
              lines are held until a cause is recorded.
            </p>
            {pair.citation ? (
              <blockquote className="mt-md border-l-2 border-gold pl-md text-sm text-muted">
                {pair.citation.quote}
                <footer className="mt-sm text-xs text-muted">
                  {pair.citation.document_title}, section {pair.citation.heading}
                </footer>
              </blockquote>
            ) : null}
          </div>
        </div>
      ) : (
        <div className="rounded-md border border-line p-lg">
          <p className="font-serif text-2xl text-ink">
            No variance to show today.
          </p>
          <p className="mt-sm text-sm text-muted">
            No two requisitions for the same item were raised far enough apart
            to breach the variance rule.
          </p>
        </div>
      )}

      <div>
        <SectionHeading title="Every requisition raised today" />
        <div className="mt-md">
          <DataTable
            columns={[
              { key: 'id', header: 'Reference' },
              { key: 'item', header: 'Item' },
              { key: 'department', header: 'Department' },
              { key: 'vendor', header: 'Vendor' },
              { key: 'quantity', header: 'Qty', align: 'right' },
              { key: 'unit_cost_formatted', header: 'Unit', align: 'right' },
              { key: 'total_cost_formatted', header: 'Total', align: 'right' },
            ]}
            rows={data.submissions}
            getRowKey={(row) => row.id}
            emptyMessage="No requisitions were raised on this date."
          />
        </div>
        <ProvenanceLine provenance={data.provenance} className="mt-md" />
      </div>
    </div>
  )
}

export default Proof
