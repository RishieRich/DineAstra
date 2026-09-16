# DineAstra customer-demo checklist

This file is the live implementation ledger for the DineAstra prototype. Update it after each verified milestone so another coding agent can continue without repeating completed work.

## Product outcome

Deliver a polished localhost demo that one restaurant or hospitality customer can use to:

- sign in and understand the product immediately;
- inspect current KPIs, trends, exceptions, and events;
- filter the dashboard by an available business date and reporting window;
- download the supplied workbook template;
- load Excel, CSV, or text records incrementally;
- retain changed outlet-date records as type-2 history;
- see accepted records reflected in dashboard metrics;
- ask guarded AI questions over the same governed data;
- distinguish working capabilities from roadmap items.

## Visual direction

- [x] Replace the original minimal Darpan presentation.
- [x] Apply royal indigo, antique gold, pearl, and ink consistently.
- [x] Use Playfair Display for editorial headings and Manrope for UI text.
- [x] Verify all working text is at least 14px unless it is secondary metadata.
- [x] Make KPI cards responsive to long labels and values.
- [x] Add restrained motion to login storytelling and interactive states.
- [x] Check desktop at 1440px and compact layouts near mobile width.
- [x] Remove remaining mojibake or stale customer-facing Darpan labels.

## Core experience

- [x] Split-screen login with instant sample-data access.
- [x] Signed-in sidebar and top navigation shell.
- [x] Command centre route with live backend KPIs.
- [x] Events and banquet drill-down retained.
- [x] Purchasing proof workflow retained.
- [x] Operating document search and checklist generation retained.
- [x] Ask AI route retained with number guard and provenance.
- [x] Add a working as-of date selector and reporting-window dropdown.
- [x] Add revenue and cost trend charts backed by the selected window.
- [x] Show available data range and exact last-updated timestamp.
- [x] Verify every route inside the redesigned shell.

## Data Studio

- [x] Excel, CSV, and UTF-8 text intake endpoint.
- [x] Quick daily-entry form.
- [x] Validation for required columns, dates, percentages, and checklist counts.
- [x] Type-2 versioning by business date plus outlet.
- [x] Idempotent re-upload detection.
- [x] Current imported records override the matching seeded business date.
- [x] Imported records feed the same metrics used by dashboard and Ask AI.
- [x] Downloadable Excel, CSV, and text examples.
- [x] Automated tests for create, update, and unchanged imports.
- [x] Extend the workbook and importer to additional sheets such as Events and Requisitions.
- [x] Add a downloadable reject/error report for invalid rows.
- [x] Add reset-to-sample-data control with explicit confirmation.

## Correctness work completed in the continuation session

These were defects found by audit rather than checklist items, and each is now
fixed with a test that fails if it regresses.

- [x] The running backend had cached the pre-rebrand `users.json` through
      `lru_cache`, so the documented demo login was rejected. The code and data
      were already correct; restarting the process fixed it. Worth knowing:
      **edits to anything under `data/` need a backend restart.**
- [x] "Today" was split in two. `anchor_date()` returned the latest merged
      date while the dashboard defaulted to the fixed `ANCHOR_DATE`, so the
      command centre and Ask AI disagreed about the business date whenever
      anything had been uploaded. `anchor_date()` is now pinned to
      `ANCHOR_DATE` (2026-09-14); uploads for later dates stay reachable from
      the selector but no longer move "today".
- [x] The hero revenue figure was computed inline in `analysis.overview` with a
      hand-written provenance dict, bypassing the metric registry and breaking
      rule I. The reporting window is now a `MetricContext` parameter and the
      hero reads `registry.compute("trailing_30_total_revenue", ...)` again.
- [x] An uploaded day replaced the whole seeded row, zeroing occupancy, ADR,
      RevPAR and room revenue for that date. An upload now overlays only the
      F&B and checklist fields it actually states; a date with no rooms record
      reports those metrics as absent (`--`) rather than as zero.
- [x] Provenance named `daily_property.json` for figures that came from an
      upload. Every metric now cites the file the rows were really read from,
      including `banquets.json + Data Studio` for a mixed window.
- [x] The top-bar business date was the hardcoded string `16 Sep 2026`. It now
      reads `/api/health`.

## Restaurant data and presentation pass

The product was branded as restaurant intelligence but the dataset underneath
it was a 180-room hotel. That is why the KPIs read as meaningless and the
headline was an abstract crore figure. Rebuilt end to end.

- [x] Re-seed as **Astra House Group**: four Bengaluru outlets, 250 seats, three
      dining rooms and one delivery-only kitchen. A weekday trades about
      ₹5.9L and a weekend about ₹9.3L.
- [x] Retire every hotel field -- rooms, occupancy, ADR, RevPAR, room revenue --
      and replace them with covers, average spend, dine-in and delivery splits,
      prime cost, sales per seat, table turns and comps.
- [x] Rebuild the 21 metrics around what a restaurant operator reads. **Prime
      cost** is now on the front row; it is the number a restaurant lives or
      dies by and neither food nor labour alone shows it.
- [x] Lead the dashboard with the day's own net sales (₹7,24,455), not a
      30-day aggregate in crores. The window total is context beneath it.
- [x] Plant a second story in the data: delivery drifts from 17.5% to 23.5% of
      sales across the window, a lower-margin channel quietly taking share.
      Asserted at generation time like the food-cost step.
- [x] Rewrite the operating standard's 34 tasks as restaurant work across
      Kitchen, Service & Floor, Bar & Beverage, Host & Reservations,
      Delivery & Packaging, and Facilities & Safety.
- [x] Rescale the 24 events to private-dining size, preserving every margin
      exactly by scaling revenue and all four cost lines by the same ratio.
      Segments renamed `corporate` / `wedding` / `celebration` / `group`.
- [x] Lower the complimentary-beverage threshold from 150 covers to 80 in both
      the policy document and the rule that reads it, so the flagged event
      still has a documented cause at restaurant scale.
- [x] Replace the requisition catalogue with what a restaurant group buys.
- [x] Convert the Ask AI "occupancy" intent to a **covers** intent, in English
      and Gujarati, with the weekend premium as its explanation.

### Presentation

- [x] One type scale in `tokens.css`, applied everywhere. The page title came
      down from 58px to 36px and the hero from 109px to 44px.
- [x] Replace the "DA" monogram, which read as DNA, with a drawn mark: an
      eight-pointed star set in a charger ring. Matching favicon.
- [x] Replace the two overlapping polylines with two bar charts that each make
      an argument: net sales stacked by channel, and food cost against target.
      Bars, not curves -- a trading day is discrete and a line between two of
      them implies values that were never traded.
- [x] **Tooltips on both charts**, by hover and by keyboard, giving the exact
      figures for the day under the cursor.
- [x] Chart palette validated with the dataviz skill's checker rather than by
      eye: lightness band, chroma floor, CVD separation and normal-vision
      floor all pass. The gold's sub-3:1 contrast is relieved by written
      totals in the legend.
- [x] Move the per-tile provenance to hover. Six tiles each printing three
      lines of source text had turned the most important row into small print.
- [x] Default the reporting window to 60 days, so the 16 August food-cost step
      falls inside the frame. At 30 days every bar landed on the same side of
      the target and the chart said nothing.

### Data Studio

- [x] Add an optional `delivery_sales` column to the daily sheet.
- [x] Fix a round-trip bug: a cost percentage typed as 34% came back as 26%,
      because it was applied to dine-in sales but reported against dine-in
      plus delivery. Pinned with a test.
- [x] After an upload, "See refreshed KPIs" links to the date just loaded.
- [x] Verified live: 12 rows across three sheets load, re-uploading the same
      file reports 12 unchanged, and restating one outlet-day versions it and
      moves the dashboard from ₹5,70,800 to ₹6,09,300.

## Configuration and documentation

- [x] Create a local `.env` containing blank key placeholders only.
- [x] Keep `.env.example` aligned with every supported key.
- [x] Rewrite the root README for DineAstra setup and demo flow.
- [x] Refresh `DEMO.md` for the new screen names and upload journey.
- [x] Keep runtime imports and traces ignored by Git.
- [x] Add this resumable checklist.
- [x] Add `CLAUDE_HANDOVER.md` with continuation instructions.
- [x] Resolve the constitution-versus-CSS disagreement: rule X amended to
      permit token-built depth, eyebrow capitals and the two brand gradients.
      The load-bearing half of the rule — no colour outside `tokens.css`, no
      backdrop blur, no emoji — is unchanged and still greps to zero.
- [x] Ignore `outputs/` and `tmp/`, and untrack the four generated files that
      were committed under them. The customer template is now generated by
      `scripts/build_sample_workbook.py` into `ui/frontend/public/samples/`,
      using openpyxl rather than a vendored Node package.

## Verification

- [x] Python tests pass: **54 passed** (was 26).
- [x] Frontend production build passes.
- [x] Frontend lint: five legacy React warnings remain, none in new code.
- [x] Restart the backend after the latest source changes.
- [x] Exercise login, dashboard, Data Studio upload, updated dashboard, and Ask AI through localhost.
- [x] Confirm `http://127.0.0.1:5173` and `http://127.0.0.1:8000/api/health` respond.
- [x] Inspect Git diff and ensure no runtime secrets or customer files are tracked.
- [x] Load the three-sheet template through the live API: 10 rows across daily,
      events and requisitions, 0 rejected.
- [x] Confirm uploaded events reach `/api/banquet/events` and uploaded
      requisitions reach `/api/operations/submissions`, with margin and line
      totals computed on load.
- [x] Confirm a mixed valid/invalid upload loads the good rows, lists the bad
      ones with reasons, and serves a correct CSV reject report.
- [x] Confirm the reset control refuses every phrase except `RESET`, and that
      a confirmed reset clears all three datasets and their reject reports.
- [x] Confirm the load-bearing figures in `HANDOFF.md` §5 still hold with the
      template loaded: corporate margin 61.2 across six events, checklist
      97.1%, food cost 34.8%, 21 metrics, anchor 2026-09-14.
- [x] Re-check 375px across every route with `scripts/responsive_audit.py`,
      which drives headless Chrome over CDP and reports any element escaping
      the viewport. All eight routes pass. The reject panel and reset card
      were rendered at 375px through a real upload and measured too.

## Current runtime notes

- Vite runs at `http://127.0.0.1:5173`; FastAPI at `http://127.0.0.1:8000`.
- Login is `owner@dineastra.demo` / `dineastra`.
- Restart the backend after editing anything under `data/` — the repository
  caches those files with `lru_cache` for the life of the process.
- On Windows, set `PYTHONIOENCODING=utf-8` before piping any script that
  prints `₹`, or the console mangles it into `â‚¹`.

## Not done, and deliberately so

- The Events and Requisitions sheets are ingested, versioned and merged, but
  no screen yet lets a customer *browse* uploaded events separately from
  seeded ones; they simply appear in the existing events and proof screens,
  tagged with a `Data Studio` source in their provenance.
- Of `HANDOFF.md` §7 item 6, only the 375px half is now re-checked, by
  `scripts/responsive_audit.py`. **Keyboard focus rings and
  `prefers-reduced-motion` have still not been re-verified since the rebrand.**
  The same CDP harness could check both; it has not been extended to do so.
- The Gemini key noted in `HANDOFF.md` §8 still wants rotating. Nothing was
  ever committed, but the key touched local disk.
