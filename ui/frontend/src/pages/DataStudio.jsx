import { useCallback, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import SectionHeading from '../components/SectionHeading'
import StatusNote from '../components/StatusNote'
import { api } from '../lib/api'
import { useSession } from '../lib/session'
import { useResource } from '../lib/useResource'

const initialForm = {
  date: '2026-09-16',
  outlet: 'Astra House - Bengaluru',
  net_sales: '452800',
  covers: '571',
  food_cost_pct: '32.4',
  labour_cost_pct: '25.1',
  checklist_total: '34',
  checklist_signed_off: '33',
  notes: 'One closing check pending',
}

function DataStudio() {
  const { token } = useSession()
  const [reloadKey, setReloadKey] = useState(0)
  const { data, error, loading } = useResource((t) => api.dataStatus(t), [reloadKey])
  const [dragging, setDragging] = useState(false)
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState(null)
  const [noticeTitle, setNoticeTitle] = useState('Import complete')
  const [uploadError, setUploadError] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [lastImport, setLastImport] = useState(null)
  const [reportError, setReportError] = useState(null)
  const [resetOpen, setResetOpen] = useState(false)
  const [resetPhrase, setResetPhrase] = useState('')
  const [resetError, setResetError] = useState(null)
  const fileRef = useRef(null)

  const loadFile = useCallback(async (file) => {
    if (!file) return
    setBusy(true)
    setNotice(null)
    setUploadError(null)
    try {
      const result = await api.dataUpload(token, file)
      setLastImport(result)
      setNoticeTitle(result.rejected ? 'Loaded, with rows held back' : 'Import complete')
      const sheets = Object.values(result.datasets || {})
        .map((entry) => `${entry.processed} ${entry.label.toLowerCase()}`)
        .join(', ')
      const accepted = `${sheets || `${result.processed} rows`} accepted · ${result.created} new · ${result.updated} versioned · ${result.unchanged} unchanged`
      setNotice(
        result.rejected
          ? `${accepted} · ${result.rejected} rejected.`
          : `${accepted}.`,
      )
      setReloadKey((key) => key + 1)
    } catch (err) {
      setUploadError(err.message)
    } finally {
      setBusy(false)
    }
  }, [token])

  async function submitEntry(event) {
    event.preventDefault()
    setBusy(true)
    setNotice(null)
    setUploadError(null)
    try {
      const result = await api.dataQuickEntry(token, {
        ...form,
        net_sales: Number(form.net_sales),
        covers: Number(form.covers),
        food_cost_pct: Number(form.food_cost_pct),
        labour_cost_pct: Number(form.labour_cost_pct),
        checklist_total: Number(form.checklist_total),
        checklist_signed_off: Number(form.checklist_signed_off),
      })
      setLastImport(null)
      setNoticeTitle('Import complete')
      setNotice(
        result.unchanged
          ? 'This record already matches the current version. Nothing was duplicated.'
          : 'Daily record loaded. The command centre and Ask AI now use this version.',
      )
      setReloadKey((key) => key + 1)
    } catch (err) {
      setUploadError(err.message)
    } finally {
      setBusy(false)
    }
  }

  async function downloadRejects() {
    setReportError(null)
    try {
      await api.dataRejectReport(token, lastImport.batch_id)
    } catch (err) {
      setReportError(err.message)
    }
  }

  async function confirmReset(event) {
    event.preventDefault()
    setBusy(true)
    setResetError(null)
    try {
      const result = await api.dataReset(token, resetPhrase)
      setLastImport(null)
      setUploadError(null)
      setNoticeTitle('Back on sample data')
      setNotice(
        `${result.removed_current_records} uploaded records and ${result.removed_versions} retained versions were discarded. The workspace is back on seeded sample data.`,
      )
      setResetOpen(false)
      setResetPhrase('')
      setReloadKey((key) => key + 1)
    } catch (err) {
      setResetError(err.message)
    } finally {
      setBusy(false)
    }
  }

  if (loading || error || !data) return <StatusNote loading={loading} error={error} />

  const updateField = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))
  const loadedDatasets = Object.values(data.datasets || {})
  const latestDate = data.datasets?.daily?.latest_date || data.latest_date

  return (
    <div className="page-stack">
      <SectionHeading
        eyebrow="Data Studio"
        title="Bring operational data into one trusted view"
        support="Upload files or enter one day manually. Repeated outlet-and-date rows become a versioned history instead of silent overwrites."
        action={<span className="status-chip status-chip--live"><i /> Intake ready</span>}
      />

      <div className="data-stat-grid">
        <article><span>Current records</span><strong>{data.current_records}</strong><small>Active outlet-day versions</small></article>
        <article><span>Historical versions</span><strong>{data.historical_versions}</strong><small>Retained changes</small></article>
        <article>
          <span>Records loaded</span>
          <strong>{loadedDatasets.length ? loadedDatasets.map((entry) => entry.records).reduce((a, b) => a + b, 0) : '—'}</strong>
          <small>{loadedDatasets.length ? loadedDatasets.map((entry) => entry.label).join(' · ') : 'Daily, events and requisitions'}</small>
        </article>
        <article><span>Latest business date</span><strong className="date-stat">{data.latest_date || 'Sample baseline'}</strong><small>Reachable from the date selector</small></article>
      </div>

      <div className="data-layout">
        <section className="surface-card upload-card">
          <div className="card-heading">
            <div><p className="eyebrow">File intake</p><h3>Load Excel, CSV or text</h3></div>
            <span className="step-number">01</span>
          </div>
          <button
            type="button"
            className={`drop-zone ${dragging ? 'drop-zone--active' : ''}`}
            onClick={() => fileRef.current?.click()}
            onDragEnter={(event) => { event.preventDefault(); setDragging(true) }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragging(false)}
            onDrop={(event) => {
              event.preventDefault()
              setDragging(false)
              loadFile(event.dataTransfer.files?.[0])
            }}
          >
            <span className="upload-glyph" aria-hidden="true">↑</span>
            <strong>{busy ? 'Reading your data…' : 'Drop a daily operations file here'}</strong>
            <small>daily operations, events and requisitions · maximum 5 MB</small>
          </button>
          <input
            ref={fileRef}
            className="sr-only"
            type="file"
            accept=".xlsx,.csv,.txt"
            onChange={(event) => loadFile(event.target.files?.[0])}
          />

          <div className="sample-files">
            <p>Start with a prepared sample</p>
            <div>
              <a href="/samples/dineastra_daily_operations_template.xlsx" download>Excel template</a>
              <a href="/samples/dineastra_daily_operations_sample.csv" download>CSV sample</a>
              <a href="/samples/dineastra_daily_operations_sample.txt" download>Text sample</a>
            </div>
          </div>
        </section>

        <section className="surface-card quick-entry-card">
          <div className="card-heading">
            <div><p className="eyebrow">Quick entry</p><h3>Add one outlet-day</h3></div>
            <span className="step-number">02</span>
          </div>
          <form className="entry-form" onSubmit={submitEntry}>
            <label>Business date<input type="date" value={form.date} onChange={updateField('date')} required /></label>
            <label>Outlet<input value={form.outlet} onChange={updateField('outlet')} required /></label>
            <label>Net sales (₹)<input type="number" min="0" value={form.net_sales} onChange={updateField('net_sales')} required /></label>
            <label>Covers<input type="number" min="0" value={form.covers} onChange={updateField('covers')} required /></label>
            <label>Food cost %<input type="number" min="0" max="100" step="0.1" value={form.food_cost_pct} onChange={updateField('food_cost_pct')} required /></label>
            <label>Labour cost %<input type="number" min="0" max="100" step="0.1" value={form.labour_cost_pct} onChange={updateField('labour_cost_pct')} required /></label>
            <label>Checklist total<input type="number" min="0" value={form.checklist_total} onChange={updateField('checklist_total')} required /></label>
            <label>Signed off<input type="number" min="0" value={form.checklist_signed_off} onChange={updateField('checklist_signed_off')} required /></label>
            <label className="entry-form__wide">Notes<input value={form.notes} onChange={updateField('notes')} /></label>
            <button type="submit" className="primary-button entry-form__wide" disabled={busy}>Save daily record <span>→</span></button>
          </form>
        </section>
      </div>

      {notice || uploadError ? (
        <div className={`inline-notice ${uploadError ? 'inline-notice--error' : ''}`} role={uploadError ? 'alert' : 'status'}>
          <strong>{uploadError ? 'Import needs attention' : noticeTitle}</strong>
          <span>{uploadError || notice}</span>
          {!uploadError ? (
            <Link to={latestDate ? `/overview?date=${latestDate}` : "/overview"}>
              See refreshed KPIs →
            </Link>
          ) : null}
        </div>
      ) : null}

      {lastImport?.rejected ? (
        <section className="surface-card reject-card" aria-labelledby="reject-heading">
          <div className="card-heading">
            <div>
              <p className="eyebrow eyebrow--gold">Rows not loaded</p>
              <h3 id="reject-heading">
                {lastImport.rejected} of {lastImport.rejected + lastImport.processed} rows were rejected
              </h3>
            </div>
            <button type="button" className="ghost-button" onClick={downloadRejects}>
              Download the report
            </button>
          </div>
          <p className="reject-card__lead">
            Everything else in the file was loaded. Correct these rows and upload them again --
            the report keeps each original row next to the reason it was held back.
          </p>
          <table className="reject-table">
            <thead>
              <tr><th scope="col">Row</th><th scope="col">Why it was held back</th></tr>
            </thead>
            <tbody>
              {lastImport.rejects.map((reject) => (
                <tr key={reject.row}>
                  <td>{reject.row}</td>
                  <td>{reject.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {lastImport.rejected > lastImport.rejects.length ? (
            <small className="reject-card__more">
              Showing the first {lastImport.rejects.length}. The report lists all {lastImport.rejected}.
            </small>
          ) : null}
          {reportError ? <p className="reject-card__error" role="alert">{reportError}</p> : null}
        </section>
      ) : null}

      <section className="surface-card lineage-card">
        <div className="card-heading">
          <div><p className="eyebrow">Version history</p><h3>Every change remains traceable</h3></div>
          <span className="step-number">03</span>
        </div>
        <div className="lineage-flow" aria-label="Import processing stages">
          <div><span>1</span><strong>Validate</strong><small>Columns, values and dates</small></div>
          <b>→</b>
          <div><span>2</span><strong>Version</strong><small>Close old, retain new</small></div>
          <b>→</b>
          <div><span>3</span><strong>Refresh</strong><small>KPIs and Ask AI</small></div>
        </div>
        {data.recent_batches.length ? (
          <div className="batch-list">
            {data.recent_batches.map((batch) => (
              <div key={batch.batch_id}>
                <span className="file-type">{batch.source_file?.split('.').pop()?.toUpperCase() || 'FORM'}</span>
                <strong>{batch.source_file}</strong>
                <small>{new Date(batch.loaded_at).toLocaleString('en-IN')}</small>
                <span className="status-chip status-chip--live"><i /> Loaded</span>
              </div>
            ))}
          </div>
        ) : <p className="empty-copy">No customer uploads yet. The seeded demo data is already powering the workspace.</p>}
      </section>

      <section className="surface-card reset-card">
        <div className="card-heading">
          <div>
            <p className="eyebrow">Start again</p>
            <h3>Return to the seeded sample data</h3>
          </div>
          <span className="step-number">04</span>
        </div>
        <p className="reset-card__lead">
          {data.has_uploads
            ? `This discards ${data.current_records} uploaded records and ${data.historical_versions} retained versions. It cannot be undone.`
            : 'Nothing has been uploaded yet, so the workspace is already on seeded sample data.'}
        </p>
        {!data.has_uploads ? null : resetOpen ? (
          <form className="reset-confirm" onSubmit={confirmReset}>
            <label htmlFor="reset-phrase">
              Type <strong>RESET</strong> to confirm
            </label>
            <input
              id="reset-phrase"
              value={resetPhrase}
              onChange={(event) => setResetPhrase(event.target.value)}
              autoComplete="off"
              placeholder="RESET"
            />
            <button type="submit" className="danger-button" disabled={busy || resetPhrase !== 'RESET'}>
              Discard uploaded data
            </button>
            <button
              type="button"
              className="ghost-button"
              onClick={() => { setResetOpen(false); setResetPhrase(''); setResetError(null) }}
            >
              Keep my data
            </button>
            {resetError ? <p className="reset-card__error" role="alert">{resetError}</p> : null}
          </form>
        ) : (
          <button type="button" className="ghost-button" onClick={() => setResetOpen(true)}>
            Reset to sample data
          </button>
        )}
      </section>

      <section className="roadmap-strip">
        <div><p className="eyebrow eyebrow--gold">Roadmap</p><h3>Next on the integration layer</h3></div>
        <span>Direct POS sync</span><span>Scheduled imports</span><span>Automated anomaly alerts</span>
      </section>
    </div>
  )
}

export default DataStudio
