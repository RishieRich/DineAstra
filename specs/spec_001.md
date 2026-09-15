# 08 · Build plan

Six phases. Do not start a phase until the previous one's acceptance criteria all pass. Commit at the end of each phase with the message given.

The ordering is deliberate: **a complete working app with zero keys comes before any model call.** If you run out of time or context, stop after Phase 3 and the result is still a demoable product.

---

## Phase 0 · Scaffold

Create the full folder tree from spec 02. Every directory, every `__init__.py`, empty placeholder files where content comes later. `.gitignore` covering `.env`, `node_modules`, `__pycache__`, `.venv`, `data/runtime/*.jsonl`.

Set up `ui/frontend` with Vite, React, Tailwind 3.4 and the proxy to port 8000. Set up `ui/backend` with FastAPI, CORS for `localhost:5173`, and `GET /api/health` returning a hardcoded payload.

**Acceptance**

- `uvicorn ui.backend.main:app --port 8000` starts from the repo root with no errors
- `npm run dev` serves on 5173 and renders a page reading `Darpan`
- `curl localhost:8000/api/health` returns JSON
- `import agents` works from the repo root

Commit: `phase 0: scaffold`

---

## Phase 1 · Data and design foundation

Write `scripts/seed_data.py` and generate everything in `data/`. Hand-write the four documents in `data/docs/`. Follow spec 04 exactly, including all planted anomalies. Every one of them is load-bearing for the demo.

Write `ui/backend/repository.py` with every accessor from spec 02.

Write `ui/frontend/src/styles/tokens.css` with all tokens from spec 03, wire Tailwind to extend from them, load both fonts, and build `lib/format.js` with Indian numbering.

Build `components/Shell.jsx`, `SectionHeading.jsx`, `MetricTile.jsx`, `HeroFigure.jsx`, `DataTable.jsx`, `ProvenanceLine.jsx`. Put them on a scratch route so you can see them all at once.

**Acceptance**

- `python scripts/seed_data.py` regenerates `data/` deterministically. Run twice, files are byte-identical
- `daily_property.json` has 120 days, occupancy is higher Monday to Thursday than Friday to Sunday, and food cost steps up around 16 August
- `BQ-2026-018` exists with margin exactly 55.6 and six corporate events average 61.2
- `brand-standard.md` contains the section 4.2 paragraph verbatim and yields 34 daily tasks across 6 departments when counted by hand
- The contrast pair `SUB-004182` and `SUB-004183` exists
- `format.js` turns `482300` into `₹4,82,300` and `4820000` into `₹48.20L`
- The component scratch page shows gold serif figures on burgundy with no shadows and no gradients

Commit: `phase 1: seed data, tokens, primitives`

---

## Phase 2 · Metrics and read endpoints

Write `agents/registry.py` with all 21 metrics from spec 06, each with its compute function returning a full `MetricResult` including formatted output and provenance.

Write the read routes: `overview.py`, `banquet.py`, `operations.py`, `system.py`. No agents yet, no model, no chat.

Write `auth.py` and the login route.

**Acceptance**

- Every metric in `METRICS` has a compute function and returns a populated `provenance`
- `GET /api/overview` returns the full payload from spec 07 with a non-null `alert` for `2026-09-14`
- `GET /api/overview?date=` for a quiet day returns `alert: null`
- `GET /api/banquet/events/BQ-2026-018` returns a waterfall summing exactly to net, `peer.average_margin_pct` of 61.2 and a populated `cause` with the retrieved policy string
- `GET /api/operations/submissions?date=2026-09-14` returns a computed `contrast_pair`, not a hardcoded one
- Login with `owner@darpan.demo` / `darpan` returns a token; a wrong password returns the exact 401 message from spec 07
- No route handler exceeds forty lines
- No currency string is built anywhere in `routes/`

Commit: `phase 2: metric registry and read API`

---

## Phase 3 · The screens, still no model

Build Login, Overview, Banquet list, Banquet detail, Proof and Connections exactly as specified in spec 05, using the real endpoints. Build the Ask and Brain screens as shells with their empty states and suggestion chips, non-functional.

Write `agents/mock_bank.py` in full now, before any provider exists.

**Acceptance**

- With no `.env` file at all, every screen renders fully populated
- The hero figure counts up once after login and never again, and does not count up under `prefers-reduced-motion`
- The Overview alert block is clickable and routes to `/ask` with the question pre-filled
- The banquet waterfall renders and its segments visually sum to the whole
- The Proof contrast pair renders side by side on desktop and stacked below 768px
- `Send to GM` opens the WhatsApp preview with the Hinglish digest and a working copy button
- Every Connections card reads `Not connected` with no green indicator anywhere
- The `Sample data` chip is visible on every screen
- Search the frontend source for a hex colour literal: zero results outside `tokens.css`
- Search the frontend source for `box-shadow`, `gradient`, `backdrop-filter`, `text-transform: uppercase`: zero results
- No emoji in any frontend source file

Commit: `phase 3: all screens on real data, mock mode`

At this point you have a demoable product. If context is running short, stop here and say so.

---

## Phase 4 · Agents and the guard

Write `providers/base.py`, `mock.py`, `gemini.py`, `groq.py` and `resolve_provider()` with startup model validation per rule VIII.

Write `router.py`, `metric_agent.py`, `document_agent.py`, `narrator.py`, `guard.py`, `trace.py` and the three prompt files.

Wire `POST /api/ask` as SSE with the three-event contract. Make the Ask screen live.

**Acceptance**

- With no keys: all three Ask suggestion chips return correct answers, streaming word by word, with provenance. The figures are computed from the JSON, not canned. Only the prose is canned
- With a `GEMINI_API_KEY`: the same three questions return model-written prose with identical figures
- With a deliberately wrong `GEMINI_MODEL`: startup logs a warning listing available ids, falls through to Groq or mock, and the app still serves every screen
- The Gujarati chip returns romanised Gujarati with English financial nouns preserved
- `guard.py` unit test: feed a narration containing `₹2,00,000` when the payload holds `₹1,94,000` and assert `verdict == "fail"` and that the template answer is served instead
- `guard.py` unit test: feed a correct narration and assert `pass`
- An unsupported question returns the honest refusal from spec 05 with no model call
- `data/runtime/traces.jsonl` gains one well-formed line per question, in both mock and live mode
- The `meta` SSE event arrives before the first token

Commit: `phase 4: agent layer with number guard`

---

## Phase 5 · Property Brain

Write `checklist_agent.py`. Wire `GET /api/brain/documents`, `POST /api/brain/ask`, `POST /api/brain/generate-checklist` and `POST /api/brain/upload`.

Build the Brain screen: document cards, drop zone, the Generate checklist flow with its reviewable draft table, the document-scoped chat, and clickable citations that open the quoted section with matched lines highlighted.

**Acceptance**

- `Generate checklist` on the brand standard returns 34 tasks across 6 departments, matching a hand count of the document
- In mock mode the same result appears after roughly 900 ms
- The Brain chip question returns the hybrid answer citing section 4.2 and the 11 September last-verified date, with both the document and the metric in its provenance
- Clicking a citation opens the quoted section in context with the matched lines highlighted in gold
- Uploading a small markdown file makes it immediately searchable in the same session
- Uploading a 6 MB file returns a clear, non-apologetic rejection

Commit: `phase 5: property brain`

---

## Phase 6 · Finish

Run the whole demo script from spec 05 end to end on a fresh clone with no `.env`, then again with keys. Fix what breaks.

Write `README` quickstart verification. Check mobile at 375px width on every screen. Check keyboard navigation and focus rings. Check `prefers-reduced-motion`.

Self-critique pass against spec 03's banned list and against the constitution, rule by rule. Fix, then report what you changed.

**Acceptance**

- Fresh clone, no `.env`, two terminals, full demo in under five minutes with nothing broken
- Every screen usable at 375px
- Every interactive element reachable by keyboard with a visible gold focus ring
- Every rule in `constitution.md` demonstrably satisfied, with a one-line note per rule saying how
- A `DEMO.md` written at the repo root: the six-step script from the previous brief, with the exact clicks

Commit: `phase 6: demo ready`

---

## Reporting back

At the end of each phase, output:

1. Which acceptance criteria pass, one line each.
2. Anything you could not satisfy and why. Do not silently skip.
3. Any place you disagreed with the spec, what you did instead, and the reason. Disagreement is welcome, silence is not.

Do not summarise the code back. The repository is the artefact.