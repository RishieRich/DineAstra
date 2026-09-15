/**
 * Section heading with an optional eyebrow and supporting line.
 * The eyebrow is letter-spaced small type, set as written.
 */
function SectionHeading({ eyebrow, title, support, action }) {
  return (
    <div className="flex flex-wrap items-end justify-between gap-md border-b border-line pb-sm">
      <div>
        {eyebrow ? (
          <p className="mb-xs text-xs tracking-[0.18em] text-muted">{eyebrow}</p>
        ) : null}
        <h2 className="font-serif text-2xl text-ink">{title}</h2>
        {support ? <p className="mt-xs text-sm text-muted">{support}</p> : null}
      </div>
      {action ? <div>{action}</div> : null}
    </div>
  )
}

export default SectionHeading
