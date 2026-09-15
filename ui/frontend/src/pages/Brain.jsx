import SectionHeading from '../components/SectionHeading'

/**
 * Property Brain, phase 3: the shell. Document cards, the drop zone and the
 * checklist flow arrive in phase 5; until then the screen says what it will
 * do rather than miming it.
 */
const BRAIN_CHIPS = [
  'What does the brand standard require every department to do daily?',
  'Why did the Solstice Analytics event settle below its segment floor?',
  'When was the brand standard last verified?',
]

function Brain() {
  return (
    <div className="flex flex-col gap-lg">
      <SectionHeading
        eyebrow="Property brain"
        title="The property's own documents, searchable"
        support="Brand standards, costing policy, procurement policy and expense policy."
      />

      <div className="rounded-md border border-line p-lg">
        <p className="font-serif text-2xl text-ink">No documents loaded yet.</p>
        <p className="mt-sm text-sm text-muted">
          The document layer is not wired up in this build. The four property
          documents already sit in the repository and their clauses are quoted
          on the Banquets and Proof screens.
        </p>
      </div>

      <div>
        <p className="text-xs tracking-[0.14em] text-muted">
          What you will be able to ask
        </p>
        <div className="mt-sm flex flex-wrap gap-sm">
          {BRAIN_CHIPS.map((chip) => (
            <span
              key={chip}
              className="rounded-sm border border-line px-md py-xs text-sm text-muted"
            >
              {chip}
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Brain
