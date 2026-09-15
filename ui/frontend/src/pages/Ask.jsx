import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import ProvenanceLine from '../components/ProvenanceLine'
import SectionHeading from '../components/SectionHeading'
import { askStream } from '../lib/askStream'
import { useSession } from '../lib/session'

export const SUGGESTION_CHIPS = [
  'Why has food cost risen since the middle of August?',
  'Which banquet segment earns least, and why?',
  'Aa mahine occupancy kem vadhyu chhe?',
]

function Ask() {
  const location = useLocation()
  const { token } = useSession()
  const [question, setQuestion] = useState('')
  const [meta, setMeta] = useState(null)
  const [answer, setAnswer] = useState('')
  const [done, setDone] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const abortRef = useRef(null)

  const submit = useCallback(
    async (asked) => {
      const text = (asked ?? '').trim()
      if (!text || busy) return

      abortRef.current?.abort()
      const controller = new AbortController()
      abortRef.current = controller

      setBusy(true)
      setError(null)
      setMeta(null)
      setAnswer('')
      setDone(null)

      try {
        await askStream(
          token,
          text,
          {
            onMeta: setMeta,
            onToken: (chunk) => setAnswer((prev) => prev + chunk),
            onDone: setDone,
          },
          controller.signal,
        )
      } catch (err) {
        if (err.name !== 'AbortError') setError(err.message)
      } finally {
        setBusy(false)
      }
    },
    [busy, token],
  )

  // The Overview alert routes here with its question already written, and
  // asks it without a second click.
  useEffect(() => {
    const carried = location.state?.question
    if (carried) {
      setQuestion(carried)
      submit(carried)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state])

  useEffect(() => () => abortRef.current?.abort(), [])

  const askChip = (chip) => {
    setQuestion(chip)
    submit(chip)
  }

  return (
    <div className="flex flex-col gap-lg">
      <SectionHeading
        eyebrow="Ask"
        title="Ask the property a question"
        support="Every figure in an answer is computed first and checked afterwards."
      />

      <form
        onSubmit={(event) => {
          event.preventDefault()
          submit(question)
        }}
        className="flex flex-col gap-md"
      >
        <label htmlFor="question" className="text-sm text-muted">
          Your question
        </label>
        <textarea
          id="question"
          rows={3}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="Ask about occupancy, rate, cost, a banquet event, or a requisition."
          className="w-full rounded-sm border border-line bg-paper p-md text-ink"
        />
        <div>
          <button
            type="submit"
            disabled={busy || !question.trim()}
            className={`rounded-sm border px-md py-sm text-sm ${
              busy || !question.trim()
                ? 'border-line text-muted'
                : 'border-burgundy bg-burgundy text-gold'
            }`}
          >
            {busy ? 'Working' : 'Ask'}
          </button>
        </div>
      </form>

      <div>
        <p className="text-xs tracking-[0.14em] text-muted">Try one of these</p>
        <div className="mt-sm flex flex-wrap gap-sm">
          {SUGGESTION_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => askChip(chip)}
              className="rounded-sm border border-line px-md py-xs text-left text-sm text-ink"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      {error ? (
        <div className="rounded-md border border-line p-lg" role="alert">
          <p className="font-serif text-2xl text-ink">That did not go through.</p>
          <p className="mt-sm text-sm text-muted">{error}</p>
        </div>
      ) : null}

      {meta || answer ? (
        <div className="rounded-md border border-line p-lg">
          <p className="whitespace-pre-wrap text-base leading-relaxed text-ink">
            {answer}
            {busy ? <span className="text-muted"> ...</span> : null}
          </p>

          {meta?.figures && Object.keys(meta.figures).length > 0 ? (
            <div className="mt-lg border-t border-line pt-md">
              <p className="text-xs tracking-[0.14em] text-muted">
                Figures behind this answer
              </p>
              <dl className="mt-sm grid gap-x-lg gap-y-xs sm:grid-cols-2">
                {Object.entries(meta.figures).map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-md text-sm">
                    <dt className="text-muted">{key.replace(/_/g, ' ')}</dt>
                    <dd className="text-ink">{value}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ) : null}

          {meta?.citations?.length ? (
            <div className="mt-md border-t border-line pt-md">
              <p className="text-xs tracking-[0.14em] text-muted">Cited</p>
              {meta.citations.map((citation) => (
                <blockquote
                  key={`${citation.document_id}-${citation.heading_number}`}
                  className="mt-sm border-l-2 border-gold pl-md text-sm text-muted"
                >
                  {citation.quote}
                  <footer className="mt-xs text-xs text-muted">
                    {citation.document_title}, section {citation.heading}
                    {citation.last_verified
                      ? ` · last verified ${citation.last_verified}`
                      : ''}
                  </footer>
                </blockquote>
              ))}
            </div>
          ) : null}

          {meta?.provenance?.length ? (
            <div className="mt-md border-t border-line pt-md">
              {meta.provenance.map((entry, index) => (
                <ProvenanceLine
                  key={`${entry.source}-${index}`}
                  provenance={entry}
                  className="mt-xs"
                />
              ))}
            </div>
          ) : null}

          {done ? (
            <p className="mt-md border-t border-line pt-md text-xs text-muted">
              {meta?.mode === 'mock'
                ? `Answered in sample mode by ${meta.provider}. The figures are computed; the wording is fixed.`
                : `Answered by ${meta?.provider} (${meta?.model}).`}
              {done.guard?.verdict
                ? ` Number check: ${done.guard.verdict}.`
                : ''}
              {done.served === 'template' && meta?.mode !== 'mock'
                ? ' The model answer was not used; the checked template was served instead.'
                : ''}
            </p>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

export default Ask
