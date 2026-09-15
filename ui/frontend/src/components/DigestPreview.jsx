import { useEffect, useRef, useState } from 'react'

/**
 * The WhatsApp preview for the GM digest. It previews and copies; it does
 * not send, because nothing is connected and the Connections screen says so.
 */
function DigestPreview({ digest, onClose }) {
  const [copied, setCopied] = useState(false)
  const closeRef = useRef(null)

  useEffect(() => {
    closeRef.current?.focus()
    function onKeyDown(event) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(digest.text)
      setCopied(true)
    } catch {
      // Clipboard permission refused: select-and-copy still works, so say so
      // rather than claiming success.
      setCopied(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-10 flex items-center justify-center bg-burgundy-deep p-md"
      role="dialog"
      aria-modal="true"
      aria-label="WhatsApp digest preview"
    >
      <div className="w-full max-w-lg rounded-md border border-line bg-paper p-lg">
        <div className="flex items-start justify-between gap-md">
          <div>
            <p className="text-xs tracking-[0.14em] text-muted">
              WhatsApp preview
            </p>
            <h2 className="mt-xs font-serif text-2xl text-ink">Send to GM</h2>
          </div>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            className="rounded-sm border border-line px-md py-xs text-sm text-ink"
          >
            Close
          </button>
        </div>

        <pre className="mt-md max-h-80 overflow-y-auto whitespace-pre-wrap rounded-sm border border-line bg-paper p-md font-sans text-sm leading-relaxed text-ink">
          {digest.text}
        </pre>

        <div className="mt-md flex flex-wrap items-center gap-md">
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-sm border border-burgundy bg-burgundy px-md py-sm text-sm text-gold"
          >
            {copied ? 'Copied' : 'Copy message'}
          </button>
          <p className="text-xs text-muted">
            WhatsApp Business is not connected. Copy the message and send it
            yourself.
          </p>
        </div>
      </div>
    </div>
  )
}

export default DigestPreview
