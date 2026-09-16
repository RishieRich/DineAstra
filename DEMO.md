# DineAstra customer demo

This is a six-to-eight minute walkthrough of the working localhost prototype. Start the backend and frontend using the commands in `README.md`, then open `http://127.0.0.1:5173`.

## 1. Premium sample workspace

On the login screen, point out the cascading product capabilities and the distinction between a secure customer workspace and the sample-data environment. Choose **Explore with sample data**, or use `owner@dineastra.demo` / `dineastra`.

## 2. Command centre

The headline is the day's own net sales — what the four outlets actually took on 14 September — not a period total. The window figure sits under it as context.

Six tiles carry the day: net sales, covers, average spend, food cost, **prime cost** and operating margin. Prime cost is the one to dwell on: food plus labour is the number a restaurant lives or dies by, and either half can look fine while the pair does not. The strip beneath adds delivery share, table turns, sales per seat, labour cost, standards sign-off and events held.

Every tile shows where its figure came from on hover, rather than printing six source lines permanently.

**The two charts are the argument.** Hover anywhere on either.

- *Net sales by channel* stacks dining room, delivery and private events for each trading day. The weekend rhythm is obvious, and so is the gold band growing: delivery has gone from about 17% of sales to about 24% across the window, and it earns less per rupee than the dining room does.
- *Food cost vs target* colours each day against the 31% standing target. The window opens green and turns red partway through — that is 16 August, the day the documented vendor rate revision landed. The chart shows the step; the next screen explains it.

The window selector defaults to 60 days precisely so that step is inside the frame.

## 3. Incremental workbook load

Open **Data Studio** and download the Excel template. It carries three sheets — **Daily Operations**, **Events** and **Requisitions** — with worked examples and customer-facing guidance on each.

Upload it once. The result reports what came in per sheet, then created, versioned, unchanged and processed rows. Upload the same file again to show that unchanged records are not duplicated.

Change `net_sales` for one existing outlet-date in the workbook and upload it again. DineAstra retains the old version, activates the new version, increments **Historical versions**, and records the batch in **Version history**.

Return to **Command centre**, select the updated date, and show the KPI and chart refresh. The quick-entry form demonstrates the same flow without a file.

### Worth showing: what happens to a bad row

Break one row in the workbook — set `food_cost_pct` to `180`, or type a word into `net_sales` — and upload it. The good rows still load; the broken ones come back in a panel naming each row and why it was held back, with a CSV report to download that keeps every original value beside the reason. This is the point to make that a single bad cell does not reject a month of trade.

### Worth showing: starting over

The **Start again** card at the foot of Data Studio discards every uploaded record and returns the workspace to seeded sample data. It requires typing `RESET` and cannot be undone, so it is safe to show and safe to leave alone.

### A note on dates

Uploaded rows for dates after the seeded window are merged and reachable from the date selector, but they do not move the demo's "today", which stays **14 September 2026**. The template's rows are dated 15 and 16 September deliberately, so loading it demonstrates the intake without restating any figure in the scripted walkthrough — and the "See refreshed KPIs" link after an upload takes you straight to the day you just loaded.

## 4. Ask DineAstra

Open **Ask DineAstra** and select a suggested question such as:

> Why has food cost risen since the middle of August?

The response includes computed evidence, citations, provenance, and a visible number-check result. With an optional AI key, a model writes the prose; the metric calculations and guard remain application-controlled.

## 5. Operational drill-downs

Open **Events & banquets** and inspect the flagged event and its margin waterfall — BQ-2026-018, a corporate dinner at 55.6% against a 60% segment floor. Then open **Daily proof** for the same-item purchase variance: two requisitions for Basmati Rice on the same day, ₹58 and ₹97, from two different kitchens. These are working seeded-data workflows, not static screenshots.

## 6. Operating brain

Open **Operating brain**, generate a checklist from a sample policy, ask a suggested document question, and open the cited source passage. This demonstrates document-grounded operational retrieval.

## 7. Honest roadmap

Finish on **Connections** and the roadmap strips. Direct POS sync, loyalty, scheduled imports, maintenance SLA, and menu engineering are intentionally labelled as future capabilities. The current prototype does not claim those integrations are connected.

## Optional real model

Add a Gemini or Groq key to the local `.env`, change `DARPAN_PROVIDER` to the chosen provider (or remove the override), and restart the backend. If provider validation fails, DineAstra falls back to its deterministic guarded answer bank while the rest of the product stays available.
