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
  const [uploadError, setUploadError] = useState(null)
  const [form, setForm] = useState(initialForm)
  const fileRef = useRef(null)

  const loadFile = useCallback(async (file) => {
    if (!file) return
    setBusy(true)
    setNotice(null)
    setUploadError(null)
    try {
      const result = await api.dataUpload(token, file)
      setNotice(
        `${result.processed} rows checked · ${result.created} new · ${result.updated} versioned · ${result.unchanged} unchanged.`,
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

  if (loading || error || !data) return <StatusNote loading={loading} error={error} />

  const updateField = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }))

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
        <article><span>Outlets represented</span><strong>{data.outlets || '—'}</strong><small>Across loaded files</small></article>
        <article><span>Latest business date</span><strong className="date-stat">{data.latest_date || 'Sample baseline'}</strong><small>Drives the latest dashboard</small></article>
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
            <small>or select a file · maximum 5 MB</small>
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
          <strong>{uploadError ? 'Import needs attention' : 'Import complete'}</strong>
          <span>{uploadError || notice}</span>
          {!uploadError ? <Link to="/overview">See refreshed KPIs →</Link> : null}
        </div>
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

      <section className="roadmap-strip">
        <div><p className="eyebrow eyebrow--gold">Roadmap</p><h3>Next on the integration layer</h3></div>
        <span>Direct POS sync</span><span>Scheduled imports</span><span>Automated anomaly alerts</span>
      </section>
    </div>
  )
}

export default DataStudio
