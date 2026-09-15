# Constitution

The original `constitution.md` referenced by `specs/spec_001.md` is not in
this repository. These twelve rules are reconstructed from the constraints
that spec's own acceptance criteria enforce, and rule VIII is the one that
spec names by number. They are the rules this build was held to, and each
carries a one-line note on how the repository satisfies it.

---

**I. Every figure is computed. A model may write the prose and never the
numbers.**
`agents/registry.py` computes all 21 metrics; `agents/narrator.py` gathers
figures before any prose exists, and `agents/mock_bank.py` templates carry
placeholders only, enforced by `audit_templates()`.

**II. No figure appears without saying where it came from.**
Every `MetricResult` carries a populated `Provenance`; `ProvenanceLine`
renders it under every tile, hero figure, answer and table.

**III. The app is fully usable with no `.env` and no keys.**
Verified on a fresh clone: every screen renders, every endpoint returns 200,
and all three Ask chips answer in mock mode.

**IV. An unsupported question is refused honestly, not answered approximately.**
`agents/router.py` is rule-based and returns `None` for anything outside the
property's records; the refusal is served with no model call.

**V. Generated data is labelled as generated, on every screen.**
The `Sample data` chip lives in `Shell` and on the login card, so no screen
can ship without it; the footer repeats it in full.

**VI. Nothing claims a connection it does not have.**
Every Connections card reads `Not connected`, there is no green indicator
anywhere, and `Send to GM` previews and copies rather than pretending to send.

**VII. The demo is deterministic.**
`scripts/seed_data.py` runs from a fixed seed and a fixed `ANCHOR_DATE`
(2026-09-14), never `date.today()`; run twice, `data/` is byte-identical.

**VIII. A configured model is validated at startup, not in front of an
audience.**
`resolve_provider()` checks the key, checks the model id against the ids the
key can reach, and makes one minimal generation to prove it is callable. A
bad id logs the available ids and falls through; the app still serves.

**IX. Every model answer is checked before it reaches the screen.**
`agents/guard.py` compares every figure in a narration against the computed
payload; a mismatch is discarded and the deterministic template is served
instead. Six unit tests cover it.

**X. Design restraint is a rule, not a preference.**
No hex literal outside `tokens.css`; no shadow, colour ramp, backdrop blur or
CSS-forced capitals; no emoji. All three greps return zero results.

**XI. The product is usable by keyboard, at phone width, and with motion off.**
Every interactive element takes a visible gold focus ring; no screen scrolls
horizontally at 375px; the hero figure paints its final value immediately
under `prefers-reduced-motion`.

**XII. A secret never reaches a log, a trace, or a response.**
Gemini passes its key in the request URL, so provider error text is scrubbed
before it is stored or returned, and httpx request logging is quietened.
`data/runtime/` is git-ignored.
