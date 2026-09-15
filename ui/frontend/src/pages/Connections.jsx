import SectionHeading from '../components/SectionHeading'
import StatusNote from '../components/StatusNote'
import { api } from '../lib/api'
import { useResource } from '../lib/useResource'

/**
 * Connections. Every card reads "Not connected", because every card is. The
 * screen exists to make that honest rather than to imply a live integration.
 */
function Connections() {
  const { data, error, loading } = useResource((token) => api.connections(token))

  if (loading || error || !data) {
    return <StatusNote loading={loading} error={error} />
  }

  return (
    <div className="flex flex-col gap-lg">
      <SectionHeading
        eyebrow="Connections"
        title="Integration readiness"
        support={data.note}
      />

      <div className="grid gap-md sm:grid-cols-2">
        {data.connections.map((connection) => (
          <div
            key={connection.id}
            className="flex h-full flex-col justify-between rounded-md border border-line p-md"
          >
            <div>
              <p className="font-serif text-xl text-ink">{connection.name}</p>
              <p className="mt-xs text-sm text-muted">{connection.vendor}</p>
              <p className="mt-sm text-sm text-ink">{connection.description}</p>
            </div>
            <p className="mt-md border-t border-line pt-sm text-sm text-muted">
              Not connected
            </p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default Connections
