import { useEffect, useState } from 'react'
import { useLocation } from 'react-router-dom'
import SectionHeading from '../components/SectionHeading'

/**
 * Ask, phase 3: the shell only. The chips fill the box and the box does not
 * submit anywhere yet -- the agent layer arrives in phase 4. The empty state
 * says so rather than pretending to think.
 */
export const SUGGESTION_CHIPS = [
  'Why has food cost risen since the middle of August?',
  'Which banquet segment earns least, and why?',
  'Aa mahine occupancy kem vadhyu chhe?',
]

function Ask() {
  const location = useLocation()
  const [question, setQuestion] = useState('')

  // The Overview alert routes here with its question already written.
  useEffect(() => {
    if (location.state?.question) setQuestion(location.state.question)
  }, [location.state])

  return (
    <div className="flex flex-col gap-lg">
      <SectionHeading
        eyebrow="Ask"
        title="Ask the property a question"
        support="Answers are computed from the property's own records and cite where each figure came from."
      />

      <form
        onSubmit={(event) => event.preventDefault()}
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
          placeholder="Ask about occupancy, cost, or any event."
          className="w-full rounded-sm border border-line bg-paper p-md text-ink"
        />
        <div>
          <button
            type="submit"
            disabled
            className="rounded-sm border border-line px-md py-sm text-sm text-muted"
          >
            Ask
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
              onClick={() => setQuestion(chip)}
              className="rounded-sm border border-line px-md py-xs text-left text-sm text-ink"
            >
              {chip}
            </button>
          ))}
        </div>
      </div>

      <div className="rounded-md border border-line p-lg">
        <p className="font-serif text-2xl text-ink">
          Darpan cannot answer yet.
        </p>
        <p className="mt-sm text-sm text-muted">
          The answering layer is not wired up in this build. The figures behind
          these questions are already computed and visible on Overview,
          Banquets and Proof.
        </p>
      </div>
    </div>
  )
}

export default Ask
