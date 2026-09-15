import { useEffect, useRef } from 'react'

/**
 * Opens a cited section in the context of its whole document, with the
 * quoted lines marked in gold. A citation you cannot open is a claim, not a
 * citation.
 *
 * Markdown markers are rendered rather than shown, but line numbering follows
 * the source file exactly, so a citation's line span still lines up with the
 * document on disk.
 */
function renderLine(line) {
  const heading = line.match(/^(#{1,6})\s+(.*)$/)
  if (heading) {
    return { text: heading[2], emphasis: true, heading: heading[1].length }
  }
  const bold = line.match(/^\*\*(.+?)\*\*$/)
  if (bold) {
    return { text: bold[1], emphasis: true, heading: 0 }
  }
  return { text: line, emphasis: false, heading: 0 }
}
function DocumentViewer({ document: doc, citation, onClose }) {
  const closeRef = useRef(null)
  const markRef = useRef(null)

  useEffect(() => {
    closeRef.current?.focus()
    markRef.current?.scrollIntoView({ block: 'center', behavior: 'auto' })
    function onKeyDown(event) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose, citation])

  if (!doc) return null

  const from = citation?.line_start ?? 0
  const to = citation?.line_end ?? 0

  return (
    <div
      className="fixed inset-0 z-10 flex items-start justify-center overflow-y-auto bg-burgundy-deep p-md"
      role="dialog"
      aria-modal="true"
      aria-label={`${doc.title}, section ${citation?.heading ?? ''}`}
    >
      <div className="my-lg w-full max-w-3xl rounded-md border border-line bg-paper p-lg">
        <div className="flex items-start justify-between gap-md border-b border-line pb-md">
          <div>
            <p className="text-xs tracking-[0.14em] text-muted">
              {citation ? `Section ${citation.heading}` : 'Document'}
            </p>
            <h2 className="mt-xs font-serif text-2xl text-ink">{doc.title}</h2>
            {doc.last_verified ? (
              <p className="mt-xs text-xs text-muted">
                Last verified {doc.last_verified}
              </p>
            ) : null}
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="shrink-0 rounded-sm border border-line px-md py-xs text-sm text-ink"
          >
            Close
          </button>
        </div>

        <div className="mt-md max-h-[60vh] overflow-y-auto">
          {doc.lines.map((line, index) => {
            const lineNumber = index + 1
            const marked = lineNumber > from && lineNumber <= to
            const rendered = renderLine(line)
            return (
              <p
                key={lineNumber}
                ref={marked && !markRef.current ? markRef : undefined}
                className={`whitespace-pre-wrap py-px pl-md leading-relaxed ${
                  rendered.heading === 1
                    ? 'font-serif text-xl'
                    : rendered.emphasis
                      ? 'font-serif text-base'
                      : 'text-sm'
                } ${
                  marked
                    ? 'border-l-2 border-gold bg-gold-soft text-ink'
                    : 'border-l-2 border-transparent text-muted'
                }`}
              >
                {rendered.text || ' '}
              </p>
            )
          })}
        </div>
      </div>
    </div>
  )
}

export default DocumentViewer
