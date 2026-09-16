# Rishi — what's done, and what's blocked on you

Last updated: 16 September 2026.

The demo is **live**. Nothing below is blocking the demo working; the items in
§1 are things only you can do, in priority order.

**Live URL:** https://dineastra.vercel.app
**Sign in:** `owner@dineastra.demo` / `dineastra` — or click **Explore with sample data**

---

## 1. Blocked on you

### 1.1 Rotate the Neon password — do this first

You pasted the Neon connection string into a chat message. Treat that
credential as **exposed**:

- it is in the chat transcript,
- the GitHub repo is **public** (`github.com/RishieRich/DineAstra`),
- the same database is used by **another live project of yours** (`arq-yantraiq`
  — I found 30 tables in `public` and a `yantraiq` schema already there).

That last point is the serious one. The credential is not just DineAstra's,
it is the whole database's, including the other project's tables.

**What to do:**

1. Neon console → your project → Roles → `neondb_owner` → **Reset password**.
2. Update the new connection string in Vercel for **both** projects:
   ```
   vercel env rm DATABASE_URL production
   vercel env add DATABASE_URL production      # paste the new string
   ```
   Repeat for `preview` and `development`, then redeploy.
3. Update your local `.env` (that file is gitignored — it is not in the repo).

I never committed the string. It is only in `.env` locally and in Vercel's
encrypted env store.

### 1.2 Decide whether this should be its own database

Right now DineAstra writes into the same Neon database as `arq-yantraiq`. I
isolated it into its own schema (`dineastra`) and touched nothing in `public`,
so there is no collision today — but two projects sharing one credential means
a leak in either one exposes both.

**Recommended:** create a separate Neon project for DineAstra and point
`DATABASE_URL` at it. Ten minutes, and the blast radius stops being shared.

If you'd rather keep one database, nothing needs doing — it works as is.

### 1.3 Decide who can reach the demo

The URL is **public right now**. I turned off Vercel's deployment protection
because otherwise every customer hits a Vercel login wall.

Anyone with the link can sign in with the demo credentials above. That is
almost certainly what you want for a shareable demo, but be aware it is not
private. If you'd rather gate it:

- **Password-protect the deployment** — Vercel → Project → Settings →
  Deployment Protection → Password Protection (Pro plan feature), or
- tell me and I'll add a per-customer access code to the login screen.

### 1.4 A custom domain, if you want one

`dineastra.vercel.app` works fine. If you want `demo.arqone.ai` or similar:

1. Vercel → Project → Settings → Domains → add it,
2. add the CNAME Vercel gives you at your DNS provider.

Tell me the domain and I'll do the Vercel side.

### 1.5 Optional: a real AI key

The demo runs in `mock` mode — every figure is computed by the app, and the
prose comes from a checked answer bank. It is honest and it never fails.

With a Gemini or Groq key, a model writes the prose instead; the figures and
the number-guard are unchanged. If you want that, give me a key and I'll set
`GEMINI_API_KEY` and flip `DARPAN_PROVIDER`. **Not needed for the demo.**

---

## 2. What I built for this deployment

### 2.1 Each visitor gets their own sandbox

This is the change that makes the link shareable.

A shared demo URL is opened by people who don't know each other. Without
isolation, one customer clicking "clear all data" would empty the screen
another customer was presenting from.

So: the browser generates a **workspace id** on first visit, keeps it in
`localStorage`, and sends it on every call. Everything a visitor loads,
uploads or clears is scoped to it. The seeded sample dataset (120 days of
trading) is read-only and shared by everyone.

Verified live: two workspaces hitting the same date see completely different
data, and clearing one leaves the other untouched.

### 2.2 Two buttons, as you asked

Both on **Data Studio**:

- **Load sample data** — loads two trading days, three events and three
  requisitions with no file. It goes through the *same importer* an upload
  does, so it demonstrates the real thing rather than a shortcut.
- **Clear all data** — appears once anything is loaded. One click, one
  confirm, gone. The wording says explicitly that it only affects that
  visitor's own data.

The button's rows and the downloadable workbook are generated from **one
definition** (`ui/backend/sample_rows.py`). That matters: load the sample,
then upload the downloaded template, and it reports *12 unchanged* rather
than pretending rows were edited. There's a test pinning that.

### 2.3 Storage moved to Postgres

Vercel's filesystem is read-only and thrown away between requests, so the
uploaded-data history could not stay in a JSON file.

- `DATABASE_URL` set → Postgres. This is what runs on Vercel.
- No `DATABASE_URL` → a local JSON file, so a fresh clone still runs and the
  test suite needs no server.

Tables created (in the `dineastra` schema, nothing in `public`):

| Table | Holds |
| --- | --- |
| `dineastra.import_versions` | the type-2 history — every version of every uploaded row |
| `dineastra.reject_reports` | the CSV report of rows that failed validation |

To inspect or wipe everything DineAstra has stored:

```sql
select workspace_id, count(*) from dineastra.import_versions group by 1;
drop schema dineastra cascade;   -- removes only DineAstra's data
```

### 2.4 Verified live, end to end

Against the deployed URL and the real Neon database:

| Step | Result |
| --- | --- |
| Sign in | works |
| Storage backend | reports `postgres` |
| Load sample data | 12 rows across three sheets |
| Upload the downloadable template on top | 12 unchanged — correctly idempotent |
| Upload a corrected row | 1 new, 1 versioned, old version retained |
| Dashboard on the uploaded date | ₹6,09,300, updated from the correction |
| Clear all data | 13 records and 14 versions discarded, back to baseline |
| Workspace isolation | a second workspace saw none of it |

---

## 3. How to run the demo for a customer

1. Open **https://dineastra.vercel.app** and click *Explore with sample data*.
2. **Command centre** — the headline is the day's own net sales, not a period
   total. Six tiles led by **prime cost** (food + labour), which is the number
   a restaurant lives or dies by. Hover any bar on either chart for exact
   figures. The food-cost chart turns red partway along — that's 16 August,
   the documented vendor rate revision.
3. **Data Studio** → *Load sample data*. Then *See refreshed KPIs* takes you
   straight to the date you just loaded.
4. Download the Excel template, change a number, upload it. It reports what
   was created, versioned and unchanged. Break a cell first and it loads the
   good rows and hands back a CSV of the bad ones with reasons.
5. **Ask DineAstra** — three questions answered from computed figures with the
   policy clause that explains them.
6. **Clear all data** when you're done, so the next person starts clean.

---

## 4. Known limits — say the word and I'll fix any of these

- **Cold starts.** The first request after a quiet spell takes a few seconds
  while the Python function wakes and opens a database connection. Subsequent
  requests are fast. Loading the page once before a customer call avoids it.
- **One login for everyone.** Every visitor signs in as the same demo user;
  isolation comes from the workspace id, not the account. Fine for a demo,
  wrong for real multi-tenant use.
- **Workspace lives in `localStorage`.** A customer who clears site data, or
  opens the link in a private window, gets a fresh empty workspace. Their
  previous uploads are still in the database but no longer reachable. I can
  add a "restore my workspace" code if that matters.
- **No cleanup of old workspaces.** Every visitor's uploads accumulate in
  Neon. Volume is tiny, but if you demo a lot I should add a job that clears
  workspaces untouched for 30 days.
- **`DARPAN_*` env names.** Internal names still say Darpan, from before the
  rebrand. Cosmetic; renaming means a coordinated env change.
- **Deployment is manual.** I deploy with `vercel deploy --prod`. If you want
  push-to-deploy from GitHub: `vercel git connect`.

---

## 5. Quick reference

```bash
# run locally (two terminals, from the repo root)
.venv/Scripts/python -m uvicorn ui.backend.main:app --port 8000
cd ui/frontend && npm run dev

# tests, build, lint
.venv/Scripts/python -m pytest tests -q          # 56 passing
cd ui/frontend && npm run build && npm run lint

# regenerate the customer template after changing importer columns
.venv/Scripts/python scripts/build_sample_workbook.py

# check no screen scrolls sideways at 375px (servers must be running)
.venv/Scripts/python scripts/responsive_audit.py

# deploy
vercel deploy --prod
```

| Thing | Value |
| --- | --- |
| Live URL | https://dineastra.vercel.app |
| Sign in | `owner@dineastra.demo` / `dineastra` |
| Vercel project | `dineastra` (team `rishikeshrpote-7458s-projects`) |
| Repo | https://github.com/RishieRich/DineAstra |
| Database | Neon, `dineastra` schema |
| Env vars set | `DATABASE_URL`, `DARPAN_SECRET`, `DARPAN_PROVIDER` — all three environments |
