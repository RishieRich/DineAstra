# Demo script

Six steps, about four minutes. Runs on a fresh clone with no `.env` and no
API keys. Everything below is real: the figures are computed from
`data/`, and the only thing that changes with a key is who writes the prose.

## Before you start

Two terminals, both at the repository root.

```bash
# terminal 1
python -m venv .venv && .venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python -m uvicorn ui.backend.main:app --port 8000
```

```bash
# terminal 2
cd ui/frontend && npm install && npm run dev
```

Open http://localhost:5173. The backend log will say
`Answering through mock (sample-data)` — that is the intended state with no
keys.

---

## 1. Sign in

Enter `owner@darpan.demo` and `darpan`, click **Sign in**.

Say: the chip in the masthead reads **Sample data**, and it is on every
screen. Nothing here is connected to a property system, and the app never
pretends otherwise.

## 2. The Overview, and the one thing that needs attention

The hero figure counts up once to **₹4.47Cr**, trailing thirty days, with the
exact rupee figure under it and its source under that.

Point at the burgundy block below it: food cost has held at **34.6%** for
seven days, **+3.6 pts** above the standing target, worth about **₹12,339 a
day**. The property's own F&B policy sets that threshold, and the block says
which file and which window the figure came from.

Then note the metric tiles: each one compares like with like — a Monday
against other Mondays — because this property runs Monday-to-Thursday heavy
and a blended average would report the shape of the week as a movement.

## 3. Ask it why — click the alert

Click the alert block. It carries its own question into **Ask** and asks it:

> Why has food cost risen since the middle of August?

The answer streams word by word. Under it: the figures behind the answer, the
policy clause it cites with its last-verified date, the source files, and
**Number check: pass**.

Say: the numbers were computed first and the prose was written around them.
With a key, the model writes these sentences; the figures do not change,
because a model is never asked for one. If it writes a figure that was not
computed, the guard throws that answer away and serves the checked one.

## 4. Banquets — find the event that lost money

Go to **Banquets**. One event is flagged below its segment floor:
**BQ-2026-018, Solstice Analytics Annual Kickoff**. Click it.

The waterfall shows where ₹5,00,000 went, and the segments sum exactly to the
₹2,78,000 net. Against its peers it sits **-5.6 pts** behind a corporate
average of **61.2%**.

The cause is on the right, and it is not a guess: 220 covers crossed the
150-cover threshold in the banquet policy, so two hours of complimentary
house-pour service was charged to the event, putting beverage cost at 8.0% of
revenue against a segment norm of four to five. The clause is quoted underneath.

## 5. Proof — two rates for the same sack of rice

Go to **Proof**. Two requisitions were raised on the same day for Basmati
Rice: **SUB-004182** at ₹58 a unit from the contracted vendor, and
**SUB-004183** at ₹97 from another. A 67.2% spread, ₹1,560 on the dearer line.

Say: nothing here is hardcoded. The API compares same-item requisitions on
the same day and applies the 40% variance rule from the property's expense
policy. Both lines are held, not just the expensive one — the policy says the
cheaper line sometimes carries a substitution, and the screen quotes it.

## 6. The Property Brain — the documents answer back

Go to **Brain**. Click **Generate checklist** on the Darpan Brand Standard.

After about a second it returns **34 tasks across 6 departments**, each with
the line of the document it came from — a draft to review, not a black box.
Hand-count the document if you like; it matches.

Now click the chip *What does the brand standard require every department to
do daily?* The answer cites section 4.2, gives the clause verbatim, adds that
**33 of 34** tasks were signed off today (**97.1%**), and states the document
was last verified on **11 September 2026**.

Click the citation. The document opens at that section, in context, with the
quoted lines marked in gold.

Finish on **Connections**: every card reads **Not connected**. Everything
just demonstrated ran on generated data, end to end.

---

## Optional: run it with a key

Stop the backend, set `GEMINI_API_KEY` (and optionally `GEMINI_MODEL`), start
it again. The log will say `Answering through gemini`. Ask the same question
from step 3: the prose is now the model's and the figures are identical.

Set a deliberately wrong `GEMINI_MODEL` and restart: the log lists the model
ids the key can actually reach, falls through to mock, and every screen still
works.
