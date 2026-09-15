import { useCallback, useRef, useState } from 'react'
import DataTable from '../components/DataTable'
import DocumentViewer from '../components/DocumentViewer'
import ProvenanceLine from '../components/ProvenanceLine'
import SectionHeading from '../components/SectionHeading'
import StatusNote from '../components/StatusNote'
import { api } from '../lib/api'
import { useSession } from '../lib/session'
import { useResource } from '../lib/useResource'

const BRAIN_CHIPS = [
  'What does the brand standard require every department to do daily?',
  'Why did the Solstice Analytics event settle below its segment floor?',
  'What is the food cost target?',
]

function Brain() {
  const { token } = useSession()
  const [reloadKey, setReloadKey] = useState(0)
  const { data, error, loading } = useResource(
    (t) => api.brainDocuments(t),
    [reloadKey],
  )

  const [scope, setScope] = useState(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState(null)
  const [asking, setAsking] = useState(false)
  const [checklist, setChecklist] = useState(null)
  const [building, setBuilding] = useState(false)
  const [viewer, setViewer] = useState(null)
  const [uploadNote, setUploadNote] = useState(null)
  const [uploadError, setUploadError] = useState(null)
  const [dragging, setDragging] = useState(false)
  const fileRef = useRef(null)

  const ask = useCallback(
    async (asked) => {
      const text = (asked ?? '').trim()
      if (!text) return
      setAsking(true)
      setAnswer(null)
      try {
        setAnswer(await api.brainAsk(token, text, scope))
      } catch (err) {
        setAnswer({ answer: err.message, citations: [], provenance: [] })
      } finally {
        setAsking(false)
      }
    },
    [scope, token],
  )

  const buildChecklist = useCallback(
    async (docId) => {
      setBuilding(true)
      setChecklist(null)
      try {
        setChecklist(await api.brainChecklist(token, docId))
      } catch (err) {
        setChecklist({ error: err.message })
      } finally {
        setBuilding(false)
      }
    },
    [token],
  )

  const openCitation = useCallback(
    async (citation) => {
      try {
        const doc = await api.brainDocument(token, citation.document_id)
        setViewer({ doc, citation })
      } catch (err) {
        setUploadError(err.message)
      }
    },
    [token],
  )

  const handleFiles = useCallback(
    async (files) => {
      const file = files?.[0]
      if (!file) return
      setUploadError(null)
      setUploadNote(null)
      try {
        const stored = await api.brainUpload(token, file)
        setUploadNote(`${stored.title} is loaded and searchable now.`)
        setReloadKey((key) => key + 1)
      } catch (err) {
        setUploadError(err.message)
      }
    },
    [token],
  )

  if (loading || error || !data) {
    return <StatusNote loading={loading} error={error} />
  }

  return (
    <div className="flex flex-col gap-xl">
      <SectionHeading
        eyebrow="Operating brain"
        title="Turn operating documents into useful answers"
        support="Ask a question and get the exact clause alongside the figure that clause governs."
      />

      <div>
        <SectionHeading
          title="Documents"
          support={
            scope
              ? `Questions are scoped to one document. Clear the scope to search all of them.`
              : 'Questions search every document.'
          }
          action={
            scope ? (
              <button
                type="button"
                onClick={() => setScope(null)}
                className="rounded-sm border border-line px-md py-xs text-sm text-ink"
              >
                Clear scope
              </button>
            ) : null
          }
        />

        <div className="mt-md grid gap-md sm:grid-cols-2">
          {data.documents.map((doc) => {
            const scoped = scope === doc.id
            return (
              <div
                key={doc.id}
                className={`flex h-full flex-col justify-between rounded-md border p-md ${
                  scoped ? 'border-burgundy' : 'border-line'
                }`}
              >
                <div>
                  <p className="font-serif text-xl text-ink">{doc.title}</p>
                  <p className="mt-xs text-xs text-muted">
                    {doc.department}
                    {doc.last_verified
                      ? ` · last verified ${doc.last_verified}`
                      : ' · uploaded this session'}
                  </p>
                  <p className="mt-sm text-sm text-muted">
                    {doc.word_count} words across {doc.section_count} sections.
                  </p>
                </div>
                <div className="mt-md flex flex-wrap gap-sm">
                  <button
                    type="button"
                    onClick={() => setScope(scoped ? null : doc.id)}
                    aria-pressed={scoped}
                    className={`rounded-sm border px-md py-xs text-sm ${
                      scoped
                        ? 'border-burgundy bg-burgundy text-gold'
                        : 'border-line text-ink'
                    }`}
                  >
                    {scoped ? 'Scoped' : 'Ask this one'}
                  </button>
                  <button
                    type="button"
                    onClick={() => openCitation({ document_id: doc.id })}
                    className="rounded-sm border border-line px-md py-xs text-sm text-ink"
                  >
                    Open
                  </button>
                  {doc.has_checklist ? (
                    <button
                      type="button"
                      onClick={() => buildChecklist(doc.id)}
                      className="rounded-sm border border-burgundy px-md py-xs text-sm text-burgundy"
                    >
                      Generate checklist
                    </button>
                  ) : null}
                </div>
              </div>
            )
          })}
        </div>
      </div>

      <div>
        <SectionHeading title="Add a document" />
        <div
          onDragOver={(event) => {
            event.preventDefault()
            setDragging(true)
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(event) => {
            event.preventDefault()
            setDragging(false)
            handleFiles(event.dataTransfer.files)
          }}
          className={`mt-md rounded-md border border-dashed p-lg text-center ${
            dragging ? 'border-burgundy' : 'border-line'
          }`}
        >
          <p className="text-sm text-ink">
            Drop a markdown or text file here, or
          </p>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="mt-sm rounded-sm border border-burgundy px-md py-xs text-sm text-burgundy"
          >
            Choose a file
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".md,.markdown,.txt"
            className="sr-only"
            onChange={(event) => handleFiles(event.target.files)}
          />
          <p className="mt-sm text-xs text-muted">
            Markdown or plain text, up to 5 MB. It stays for this session only.
          </p>
          {uploadNote ? (
            <p className="mt-sm text-sm text-positive">{uploadNote}</p>
          ) : null}
          {uploadError ? (
            <p className="mt-sm text-sm text-negative" role="alert">
              {uploadError}
            </p>
          ) : null}
        </div>
      </div>

      {building || checklist ? (
        <div>
          <SectionHeading
            title="Draft checklist"
            support="Review it against the document before adopting it."
          />
          {building ? (
            <p className="py-lg text-sm text-muted" role="status">
              Reading the document and drafting the tasks.
            </p>
          ) : checklist?.error ? (
            <p className="py-lg text-sm text-negative">{checklist.error}</p>
          ) : (
            <div className="mt-md">
              <p className="text-sm text-ink">
                {checklist.task_count} tasks across{' '}
                {checklist.department_count} departments, from{' '}
                {checklist.document_title} section {checklist.section}. Today{' '}
                {checklist.today.tasks_signed_off} of{' '}
                {checklist.today.tasks_total} were signed off (
                {checklist.today.signoff_formatted}).
              </p>
              <div className="mt-md">
                <DataTable
                  columns={[
                    { key: 'number', header: 'No', align: 'right', nowrap: true },
                    { key: 'department', header: 'Department' },
                    { key: 'text', header: 'Task' },
                    { key: 'line', header: 'Line', align: 'right', nowrap: true },
                  ]}
                  rows={checklist.tasks}
                  getRowKey={(row) => `${row.department}-${row.number}`}
                />
              </div>
              {checklist.provenance?.map((entry, index) => (
                <ProvenanceLine
                  key={`${entry.source}-${index}`}
                  provenance={entry}
                  className="mt-sm"
                />
              ))}
            </div>
          )}
        </div>
      ) : null}

      <div>
        <SectionHeading title="Ask the documents" />
        <form
          onSubmit={(event) => {
            event.preventDefault()
            ask(question)
          }}
          className="mt-md flex flex-col gap-md"
        >
          <label htmlFor="brain-question" className="text-sm text-muted">
            {scope
              ? `Your question, scoped to one document`
              : 'Your question, across every document'}
          </label>
          <textarea
            id="brain-question"
            rows={2}
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask what a policy says, and what the figure behind it is doing."
            className="w-full rounded-sm border border-line bg-paper p-md text-ink"
          />
          <div>
            <button
              type="submit"
              disabled={asking || !question.trim()}
              className={`rounded-sm border px-md py-sm text-sm ${
                asking || !question.trim()
                  ? 'border-line text-muted'
                  : 'border-burgundy bg-burgundy text-gold'
              }`}
            >
              {asking ? 'Reading' : 'Ask'}
            </button>
          </div>
        </form>

        <div className="mt-md flex flex-wrap gap-sm">
          {BRAIN_CHIPS.map((chip) => (
            <button
              key={chip}
              type="button"
              onClick={() => {
                setQuestion(chip)
                ask(chip)
              }}
              className="rounded-sm border border-line px-md py-xs text-left text-sm text-ink"
            >
              {chip}
            </button>
          ))}
        </div>

        {answer ? (
          <div className="mt-lg rounded-md border border-line p-lg">
            <p className="text-base leading-relaxed text-ink">{answer.answer}</p>

            {answer.metric ? (
              <div className="mt-md border-t border-line pt-md">
                <p className="text-xs tracking-[0.14em] text-muted">
                  The figure this clause governs
                </p>
                <p className="mt-xs font-serif text-2xl text-burgundy">
                  {answer.metric.formatted}
                  <span className="ml-sm text-sm text-muted">
                    {answer.metric.label}
                  </span>
                </p>
              </div>
            ) : null}

            {answer.citations?.length ? (
              <div className="mt-md border-t border-line pt-md">
                <p className="text-xs tracking-[0.14em] text-muted">Cited</p>
                {answer.citations.map((citation) => (
                  <button
                    key={`${citation.document_id}-${citation.heading_number}`}
                    type="button"
                    onClick={() => openCitation(citation)}
                    className="mt-sm block w-full border-l-2 border-gold pl-md text-left text-sm text-muted"
                  >
                    {citation.quote}
                    <span className="mt-xs block text-xs text-burgundy underline underline-offset-4">
                      {citation.document_title}, section {citation.heading}
                      {citation.last_verified
                        ? ` · last verified ${citation.last_verified}`
                        : ''}
                    </span>
                  </button>
                ))}
              </div>
            ) : null}

            {answer.provenance?.length ? (
              <div className="mt-md border-t border-line pt-md">
                {answer.provenance.map((entry, index) => (
                  <ProvenanceLine
                    key={`${entry.source}-${index}`}
                    provenance={entry}
                    className="mt-xs"
                  />
                ))}
              </div>
            ) : null}
          </div>
        ) : null}
      </div>

      {viewer ? (
        <DocumentViewer
          document={viewer.doc}
          citation={viewer.citation}
          onClose={() => setViewer(null)}
        />
      ) : null}
    </div>
  )
}

export default Brain
