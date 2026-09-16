# Claude Code handover prompt

Copy the prompt below into Claude Code if this session ends before the work is complete.

---

Continue the DineAstra customer-demo implementation in:

`D:\AI_Projects\ARQ\ARQ_DineAstra`

Read these files first and treat them as the source of truth:

1. `IMPLEMENTATION_CHECKLIST.md` — the live ledger, including what is deliberately not done
2. `constitution.md` — the twelve rules, rule X amended at the rebrand
3. `HANDOFF.md` §5 — the load-bearing figures the demo depends on
4. `README.md`
5. `ui/backend/data_import_service.py` — the three-dataset importer
6. `ui/backend/repository.py` — the only module that reads `data/`
7. `agents/registry.py` — the 21 metrics, the only place a figure is computed
8. `ui/frontend/src/pages/DataStudio.jsx` and `Overview.jsx`

The product is a working restaurant and hospitality intelligence prototype, not
a static mockup. Preserve the React/Vite frontend, FastAPI backend, deterministic
seeded data, metric registry, number guard, provenance, events, purchasing proof,
document brain, and Ask AI flows.

## State as of this handover

Everything on the checklist is complete. Tests: **53 passing**. Frontend build
passes; lint shows five legacy React warnings, none in new code.

The three Data Studio items that were open are now done: Events and Requisitions
sheets, the downloadable reject report, and reset-to-sample with confirmation.

Six defects were found by audit and fixed, each with a regression test. They are
listed in `IMPLEMENTATION_CHECKLIST.md` under "Correctness work completed in the
continuation session". The two most important to understand before changing
anything:

- **"Today" is pinned.** `repo.anchor_date()` always returns `ANCHOR_DATE`
  (2026-09-14). Uploads dated later are merged and reachable from the date
  selector, but they do not move the demo's business date. This was a decision,
  not an accident — an earlier version let a single upload restate every figure
  in `HANDOFF.md` §5.
- **An upload restates F&B, not a whole day.** `overlay_daily_row` patches only
  the fields an upload actually carries; the rooms side of a seeded day survives.
  A date with no rooms record reports occupancy, ADR and RevPAR as absent, never
  as zero.

## Rules that matter most

- **Every figure is computed in `agents/registry.py`.** If you need a variant of
  a metric, add a parameter to `MetricContext` — do not compute it inline in a
  route or in `analysis.py`. That is what broke rule I before.
- **Provenance names the file the rows really came from.** `_source_of()` in the
  registry does this; use it rather than hardcoding a filename.
- **Restart the backend after editing anything under `data/`.** `repository`
  caches those files with `lru_cache` for the life of the process. A stale
  process is what made the demo login appear broken.
- On Windows, `PYTHONIOENCODING=utf-8` before piping anything that prints `₹`.

## Useful commands

```powershell
# backend and frontend
.\.venv\Scripts\python.exe -m uvicorn ui.backend.main:app --port 8000
cd ui\frontend; npm run dev

# tests, build, lint
.\.venv\Scripts\python.exe -m pytest tests -q
cd ui\frontend; npm run build; npm run lint

# regenerate the customer template after changing importer columns
.\.venv\Scripts\python.exe scripts\build_sample_workbook.py

# check no screen scrolls horizontally at 375px (both servers must be running)
.\.venv\Scripts\python.exe scripts\responsive_audit.py
```

Login is `owner@dineastra.demo` / `dineastra`.

## What is genuinely left

1. **Keyboard focus rings and `prefers-reduced-motion` have not been re-verified
   since the rebrand.** The 375px half of that check is now automated in
   `scripts/responsive_audit.py`; extending the same CDP harness to tab through
   focusable elements and to assert the hero figure paints immediately under
   `prefers-reduced-motion` is the natural next step.
2. **No screen browses uploaded events separately from seeded ones.** They are
   ingested, versioned and merged, and appear in the existing events and proof
   screens tagged `Data Studio` in their provenance — but a customer cannot yet
   filter to "the events I loaded".
3. **The Gemini key in `HANDOFF.md` §8 still wants rotating.** Nothing was ever
   committed, but the key touched local disk.

Do not overwrite the architecture, delete user work, commit runtime import
history, or claim roadmap features work. Update `IMPLEMENTATION_CHECKLIST.md` as
each item is verified, and keep this file current if major choices change.

---
