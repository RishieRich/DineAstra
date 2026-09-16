# DineAstra

DineAstra is a working restaurant and hospitality intelligence prototype. A customer can load daily Excel, CSV, or text records; inspect current KPIs and trends; retain changed rows as history; and ask governed questions over the same data.

DineAstra is a daily operating view for a multi-outlet restaurant group. The
sample estate is **Astra House Group**: four outlets in Bengaluru -- three
dining rooms and one delivery-only kitchen, 250 seats between them -- trading
around ₹7 lakh on a weekday and ₹10 lakh on a weekend.

The project runs locally with generated sample data and no paid services. AI keys are optional: figures are always calculated by the application, and model-written answers are checked against those figures before display.

## Run locally

Use two PowerShell terminals at the repository root.

Backend:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn ui.backend.main:app --port 8000
```

Frontend:

```powershell
Set-Location ui/frontend
npm install
npm run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173). Use `owner@dineastra.demo` / `dineastra`, or choose **Explore with sample data** on the login screen.

Confirm the API at [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health).

## Customer demo journey

1. Open **Command centre** and choose an as-of date and 7, 30, 60, or 90-day reporting window.
2. Review net sales, covers, average spend, food cost, prime cost and operating margin, then the channel and cost charts beneath them.
3. Open **Data Studio** and download the prepared Excel template. It carries three sheets: Daily Operations, Events and Requisitions.
4. Upload the workbook unchanged. Each sheet is recognised by its own columns and reported separately. Re-uploading it is idempotent and creates no duplicates.
5. Change sales or cost for the same outlet and date, then upload again. DineAstra closes the old version and activates the new one.
6. Return to the command centre to see refreshed KPIs, then open **Ask DineAstra** to query the governed data.

The canonical workbook is [dineastra_daily_operations_template.xlsx](ui/frontend/public/samples/dineastra_daily_operations_template.xlsx), which Data Studio serves. It is generated, not hand-kept:

```powershell
.\.venv\Scripts\python.exe scripts\build_sample_workbook.py
```

That script reads the importer's own column names and refuses to write a template whose sheets no longer match them, so a renamed column fails here rather than in front of a customer. CSV and text examples of the daily sheet are written alongside it.

### Daily Operations columns

| Column | Requirement |
| --- | --- |
| `date` | Business date in `YYYY-MM-DD` format |
| `outlet` | Stable outlet name |
| `dine_in_sales` | Dining-room sales, number without a currency symbol |
| `delivery_sales` | Optional. Leave blank for an outlet that does not deliver |
| `covers` | Non-negative whole number |
| `food_cost_pct` | Percentage from 0 to 100, against that outlet's whole day |
| `labour_cost_pct` | Percentage from 0 to 100, against that outlet's whole day |
| `checklist_total` | Non-negative whole number |
| `checklist_signed_off` | Whole number no greater than checklist total |
| `notes` | Optional free text |

### Events columns

| Column | Requirement |
| --- | --- |
| `event_id` | Stable booking reference; re-uploading one corrects that event |
| `event_name` | Free text |
| `segment` | One of `corporate`, `group`, `wedding`, `celebration` |
| `date` | Event date in `YYYY-MM-DD` format |
| `covers` | Non-negative whole number |
| `venue` | Optional free text |
| `revenue` | Greater than zero, no currency symbol |
| `food_cost` | Required; `beverage_cost`, `labour_cost` and `other_cost` optional |

There is no margin column. Net and margin are computed from revenue and costs
on load, because a figure in this product is computed by the application or it
is not shown.

### Requisitions columns

| Column | Requirement |
| --- | --- |
| `requisition_id` | Stable line reference |
| `date` | Requisition date in `YYYY-MM-DD` format |
| `item`, `department`, `vendor` | Free text, all required |
| `unit_cost` | Non-negative number |
| `quantity` | Non-negative whole number |

The line total is unit cost times quantity, computed on load.

### How a load behaves

The type-2 history key is `date + outlet` for daily rows, and the id for events
and requisitions. An unchanged row is skipped; a changed row closes the previous
record with `valid_to` and creates a new current version.

A bad row does not fail the file. Valid rows load, invalid ones are returned
with the row number and the reason, and a CSV report of the rejected rows —
each one carrying its original values beside the reason — can be downloaded
from Data Studio and re-uploaded once corrected.

Uploaded dates later than the seeded window are merged and reachable from the
dashboard's date selector, but they do not move the demo's fixed business date
of 14 September 2026.

**Start again** in Data Studio discards every uploaded record and returns to
seeded sample data. It requires the exact confirmation phrase `RESET` and
cannot be undone.

Local runtime history is stored in `data/runtime/import_history.json`, reject
reports in `data/runtime/reject_reports/`, and both are ignored by Git.

## Optional AI configuration

The local `.env` is already present with blank placeholders and is ignored by Git. Add a key only if model-written prose is required.

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | First optional provider |
| `GROQ_API_KEY` / `GROQ_MODEL` | Second optional provider |
| `DARPAN_PROVIDER` | Internal compatibility setting: `mock`, `gemini`, or `groq` |
| `DARPAN_SECRET` | Session signing secret; set a long value before deployment |

With blank keys and `DARPAN_PROVIDER=mock`, every screen and the deterministic Ask AI demonstration remain functional.

## Architecture

```text
agents/             metric routing, model providers, number guard, traces
ui/backend/         FastAPI routes, analysis, repository, file intake
ui/frontend/        React + Vite application and design system
data/               deterministic sample facts and operating documents
scripts/            seed the dataset, generate the customer template
tests/              backend, guard, Ask AI, document, import and provenance tests
```

## Verify changes

```powershell
.\.venv\Scripts\python.exe -m pytest tests -q
Set-Location ui/frontend
npm run build
npm run lint
```

For the presentation flow, see [DEMO.md](DEMO.md). For resumable engineering status, see [IMPLEMENTATION_CHECKLIST.md](IMPLEMENTATION_CHECKLIST.md) and [CLAUDE_HANDOVER.md](CLAUDE_HANDOVER.md).

## Prototype boundaries

The sample company, outlets, documents, vendors, and records are fictional. Daily Operations, Events and Requisitions intake, row-level rejection reporting, reset to sample data, versioning, dashboards, events, purchasing proof, document search, and governed Ask AI are working. Direct POS connections, loyalty, scheduled imports, maintenance SLAs, and menu engineering are explicitly presented as roadmap items.
