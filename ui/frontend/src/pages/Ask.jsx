import { useCallback, useEffect, useRef, useState } from 'react'
import { useLocation } from 'react-router-dom'
import ProvenanceLine from '../components/ProvenanceLine'
import SectionHeading from '../components/SectionHeading'
import { askStream } from '../lib/askStream'
import { useSession } from '../lib/session'

export const SUGGESTION_CHIPS = [
  'Why has food cost risen since the middle of August?',
  'Which event segment earns least, and why?',
  'Aa mahine covers kem vadhya chhe?',
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

  const submit = useCallback(async (asked) => {
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
      await askStream(token, text, {
        onMeta: setMeta,
        onToken: (chunk) => setAnswer((previous) => previous + chunk),
        onDone: setDone,
      }, controller.signal)
    } catch (err) {
      if (err.name !== 'AbortError') setError(err.message)
    } finally {
      setBusy(false)
    }
  }, [busy, token])

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
    <div className="page-stack ask-page">
      <SectionHeading
        eyebrow="Ask DineAstra"
        title="Talk to the data you have loaded"
        support="The answer layer uses computed figures, policy context and the latest accepted record version."
        action={<span className="status-chip status-chip--live"><i /> Guarded answers</span>}
      />

      <section className={`ask-workspace ${answer || error ? 'ask-workspace--answered' : ''}`}>
        {!answer && !error ? (
          <div className="ask-empty">
            <span className="ask-spark" aria-hidden="true">✦</span>
            <h3>What would you like to understand?</h3>
            <p>Ask about revenue, food cost, events, standards or an operating exception.</p>
            <div className="ask-suggestions cascade">
              {SUGGESTION_CHIPS.map((chip) => (
                <button key={chip} type="button" onClick={() => askChip(chip)}>{chip}</button>
              ))}
            </div>
          </div>
        ) : null}

        {error ? (
          <div className="ask-answer ask-answer--error" role="alert">
            <p className="eyebrow">Could not answer</p>
            <h3>That question did not go through.</h3>
            <p>{error}</p>
          </div>
        ) : null}

        {meta || answer ? (
          <div className="ask-answer">
            <div className="ask-answer__question"><span>You asked</span><strong>{question}</strong></div>
            <div className="ask-answer__body">
              <span className="ask-spark" aria-hidden="true">✦</span>
              <p>{answer}{busy ? <span className="typing-dot"> …</span> : null}</p>
            </div>

            {meta?.figures && Object.keys(meta.figures).length > 0 ? (
              <div className="answer-evidence">
                <p className="eyebrow">Figures used</p>
                <dl>
                  {Object.entries(meta.figures).map(([key, value]) => (
                    <div key={key}><dt>{key.replace(/_/g, ' ')}</dt><dd>{value}</dd></div>
                  ))}
                </dl>
              </div>
            ) : null}

            {meta?.citations?.length ? (
              <div className="answer-citations">
                <p className="eyebrow">Policy context</p>
                {meta.citations.map((citation) => (
                  <blockquote key={`${citation.document_id}-${citation.heading_number}`}>
                    {citation.quote}
                    <footer>{citation.document_title}, section {citation.heading}{citation.last_verified ? ` · verified ${citation.last_verified}` : ''}</footer>
                  </blockquote>
                ))}
              </div>
            ) : null}

            {meta?.provenance?.length ? (
              <div className="answer-provenance">
                {meta.provenance.map((entry, index) => <ProvenanceLine key={`${entry.source}-${index}`} provenance={entry} />)}
              </div>
            ) : null}

            {done ? (
              <p className="answer-guard">
                {meta?.mode === 'mock' ? `Sample-mode wording · ${meta.provider}` : `${meta?.provider} · ${meta?.model}`}
                {done.guard?.verdict ? ` · Number check ${done.guard.verdict}` : ''}
              </p>
            ) : null}
          </div>
        ) : null}

        <form className="ask-composer" onSubmit={(event) => { event.preventDefault(); submit(question) }}>
          <label htmlFor="question" className="sr-only">Ask about your operations</label>
          <input
            id="question"
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask about sales, food cost, events or standards…"
          />
          <button type="submit" disabled={busy || !question.trim()} aria-label="Send question">→</button>
        </form>
        <p className="ask-privacy">Latest accepted facts are aggregated before an answer is generated. Row-by-row customer data is not sent in sample mode.</p>
      </section>
    </div>
  )
}

export default Ask
