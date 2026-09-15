/**
 * Loading and error states. An error says what broke and what to do about
 * it, in the same voice as the rest of the app.
 */
function StatusNote({ loading, error, emptyMessage }) {
  if (loading) {
    return (
      <p className="py-xl text-sm text-muted" role="status">
        Reading the workspace records.
      </p>
    )
  }

  if (error) {
    return (
      <div className="rounded-md border border-line p-lg" role="alert">
        <p className="font-serif text-2xl text-ink">That did not load.</p>
        <p className="mt-sm text-sm text-muted">{error.message}</p>
      </div>
    )
  }

  return (
    <p className="py-xl text-sm text-muted">
      {emptyMessage || 'Nothing to show here.'}
    </p>
  )
}

export default StatusNote
