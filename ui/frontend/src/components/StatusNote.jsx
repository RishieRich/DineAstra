/**
 * Loading and error states.
 *
 * Loading draws the shape of the page that is coming rather than a sentence
 * about it: a heading, a lead line, a row of tiles and a panel. The reader
 * sees where things will be before they are there, and the screen does not
 * rearrange itself the moment the data lands. The spoken status is still in
 * the DOM for a screen reader, which has no use for a grey rectangle.
 *
 * An error says what broke and what to do about it, in the same voice as the
 * rest of the app, on a surface that looks like the surfaces around it.
 */

const TILE_KEYS = ['one', 'two', 'three', 'four']

function StatusNote({ loading, error, emptyMessage }) {
  if (loading) {
    return (
      <div className="skeleton-stack">
        <p className="sr-only" role="status">Reading the workspace records.</p>
        <div className="skeleton skeleton--title" aria-hidden="true" />
        <div className="skeleton skeleton--line" aria-hidden="true" />
        <div className="skeleton skeleton--hero" aria-hidden="true" />
        <div className="skeleton-grid" aria-hidden="true">
          {TILE_KEYS.map((key) => (
            <div key={key} className="skeleton skeleton--tile" />
          ))}
        </div>
        <div className="skeleton skeleton--block" aria-hidden="true" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-card" role="alert">
        <h2>That did not load.</h2>
        <p>
          The workspace could not read the records for this view. Check the
          data service is running, then reload the page.
        </p>
        <p className="error-card__detail">{error.message}</p>
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
