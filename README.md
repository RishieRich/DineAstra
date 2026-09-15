# Darpan

A daily briefing for a hotel general manager, built so that every figure on
the screen can be traced to the record it came from.

It runs end to end on generated sample data with no API keys. With a key, a
model writes the prose; the figures are computed either way, and an answer
whose numbers do not match what was computed is thrown away before it reaches
the screen.

## Quickstart

Two terminals, both at the repository root. Nothing to configure, no `.env`.

**Backend**

```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # Windows
# source .venv/bin/activate && pip install -r requirements.txt   # macOS / Linux
.venv/Scripts/python -m uvicorn ui.backend.main:app --port 8000
```

**Frontend**

```bash
cd ui/frontend
npm install
npm run dev
```

Open http://localhost:5173 and sign in with `owner@darpan.demo` / `darpan`.

### Verify it came up correctly

```bash
curl localhost:8000/api/health
# {"status":"ok", ... "mode":"sample data", "today":"2026-09-14", "metric_count":21}
```

The backend log should read `Answering through mock (sample-data)`. That is
the intended state with no keys: the prose is canned, every figure in it is
computed.

Then follow [DEMO.md](DEMO.md) — six steps, about four minutes.

## Running with a model

Optional. Copy `.env.example` to `.env`, or set the variables in your shell.

| Variable | Default | Notes |
| --- | --- | --- |
| `GEMINI_API_KEY` | unset | Enables Gemini. |
| `GEMINI_MODEL` | `gemini-flash-latest` | Validated at startup. |
| `GROQ_API_KEY` | unset | Tried after Gemini. |
| `GROQ_MODEL` | `llama-3.3-70b-versatile` | Validated at startup. |
| `DARPAN_PROVIDER` | unset | Force `mock`, `gemini` or `groq`. |
| `DARPAN_SECRET` | demo value | Signs the session token. |

Providers resolve in order — Gemini, Groq, mock — and a provider is only used
if its key works *and* its configured model id is actually callable. A wrong
model id logs the ids the key can reach and falls through; the app keeps
serving every screen either way.

## What is where

```
agents/            metric registry, router, agents, guard, providers, traces
  registry.py      the 21 metrics; the only place a figure is computed
  guard.py         checks every number in a model answer against the payload
  mock_bank.py     canned prose; placeholders only, never digits
ui/backend/        FastAPI: routes, repository, analysis, brain service
ui/frontend/       Vite + React + Tailwind; tokens.css holds every colour
data/              generated JSON and the four hand-written policy documents
scripts/seed_data.py   regenerates data/ deterministically
tests/             guard, routing, ask path, property brain
prompts/           the three agent prompts
```

## Regenerating the data

```bash
.venv/Scripts/python scripts/seed_data.py
```

Deterministic: a fixed seed and a fixed simulated "today" of 2026-09-14, never
`date.today()`. Run it twice and the files are byte-identical, so the demo
shows the same alert and the same anomaly whenever it is run. The script
asserts its own load-bearing figures, so drift fails loudly rather than
quietly changing the story.

## Tests

```bash
.venv/Scripts/python -m pytest tests/ -q
```

## Notes

The data is invented. The property, its documents, its vendors and its staff
do not exist. The anomalies in it are deliberate, and each one has a cause
written into the property's own policy documents so the app can find it.
