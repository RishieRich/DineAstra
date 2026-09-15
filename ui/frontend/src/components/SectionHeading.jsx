/**
 * Section heading with an optional eyebrow and supporting line.
 * The eyebrow is letter-spaced small type, set as written.
 */
function SectionHeading({ eyebrow, title, support, action }) {
  return (
    <div className="section-heading">
      <div>
        {eyebrow ? (
          <p className="eyebrow">{eyebrow}</p>
        ) : null}
        <h2>{title}</h2>
        {support ? <p className="section-heading__support">{support}</p> : null}
      </div>
      {action ? <div className="section-heading__action">{action}</div> : null}
    </div>
  )
}

export default SectionHeading
