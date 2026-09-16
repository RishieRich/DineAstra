import { useEffect, useRef, useState } from 'react'

/**
 * The WhatsApp preview for the GM digest. It previews and copies; it does
 * not send, because nothing is connected and the Connections screen says so.
 *
 * The sheet sits over a dimmed, blurred command centre rather than over a
 * solid panel: the reader is checking a message about the figures they were
 * just looking at, and losing sight of them entirely makes the preview feel
 * like a different screen instead of a step on this one.
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
      className="digest-overlay"
      role="dialog"
      aria-modal="true"
      aria-label="WhatsApp digest preview"
    >
      <div className="digest-sheet">
        <div className="digest-sheet__head">
          <div>
            <p className="eyebrow">WhatsApp preview</p>
            <h2>Send to GM</h2>
          </div>
          <button ref={closeRef} type="button" onClick={onClose} className="ghost-button">
            Close
          </button>
        </div>

        <pre className="digest-message">{digest.text}</pre>

        <div className="digest-sheet__foot">
          <button type="button" onClick={handleCopy} className="primary-button compact-button">
            {copied ? (
              <>
                <span aria-hidden="true">✓</span> Copied
              </>
            ) : (
              'Copy message'
            )}
          </button>
          <p>
            WhatsApp Business is not connected. Copy the message and send it
            yourself.
          </p>
        </div>
      </div>
    </div>
  )
}

export default DigestPreview
