"""Deterministic data generator for the DineAstra demo.

Run from the repo root:

    python scripts/seed_data.py

Regenerates every file under data/ (except data/docs/, which is hand-written
and only copied/validated here, and data/runtime/, which holds live traces).
Running this script twice produces byte-identical output: all "randomness"
comes from a fixed-seed PRNG and every float is rounded before being
written, so there is nothing that can drift between runs.

ANCHOR_DATE is the simulated "today" for the whole demo (2026-09-14). It is
a fixed constant, not datetime.date.today() -- the demo must show the same
alert and the same contrast pair no matter what day it is actually run.
"""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"
DOCS_DIR = DATA_DIR / "docs"

ANCHOR_DATE = date(2026, 9, 14)
WINDOW_DAYS = 120
START_DATE = ANCHOR_DATE - timedelta(days=WINDOW_DAYS - 1)
FOOD_COST_STEP_DATE = date(2026, 8, 16)

# ---------------------------------------------------------------------------
# The property: a four-outlet restaurant group in Bengaluru.
#
# Three dine-in rooms and one delivery-only kitchen. Seat counts are what the
# per-seat and table-turn metrics divide by, so they are fixed facts about the
# estate, not generated.
# ---------------------------------------------------------------------------

OUTLETS = [
    {"name": "Astra House, Indiranagar", "seats": 110, "kind": "dine_in"},
    {"name": "Astra Terrace, Koramangala", "seats": 85, "kind": "dine_in"},
    {"name": "Astra Cafe, Whitefield", "seats": 55, "kind": "dine_in"},
    {"name": "Astra Kitchen, HSR", "seats": 0, "kind": "delivery"},
]
TOTAL_SEATS = sum(outlet["seats"] for outlet in OUTLETS)  # 250

# brand-standard.md section 4.2 sets 34 daily tasks across 6 departments, and
# section 5 measures compliance as the share signed off. Target 100%, owner
# reporting threshold 95%.
CHECKLIST_TASK_TOTAL = 34
SEED = 20260914  # fixed seed -> deterministic across runs

# Delivery's share of sales drifts up across the window. It is the second
# story the dashboard has to tell: the channel grows while it earns less per
# rupee than the dining room, so a rising mix quietly moves the blended margin.
DELIVERY_MIX_START_PCT = 17.5
DELIVERY_MIX_END_PCT = 23.5


def _round1(x: float) -> float:
    return round(x + 1e-9, 1)


def _round2(x: float) -> float:
    return round(x + 1e-9, 2)


# ---------------------------------------------------------------------------
# daily_property.json
#
# One row per trading day for the whole group. Restaurants are weekend-heavy,
# which is the opposite shape to a corporate hotel: Friday to Sunday carries
# roughly half again the covers of Monday to Thursday, and a slightly higher
# average spend with it. Every daily metric compares like-for-like day types
# for exactly that reason.
# ---------------------------------------------------------------------------


def build_daily_property() -> list[dict]:
    rng = random.Random(SEED)
    rows: list[dict] = []

    for i in range(WINDOW_DAYS):
        d = START_DATE + timedelta(days=i)
        weekday = d.weekday()  # Monday=0 ... Sunday=6
        is_weekend = weekday >= 4  # Fri, Sat, Sun

        # Dine-in covers and average spend, by day type.
        covers_base = 655.0 if is_weekend else 448.0
        covers = round(covers_base + rng.uniform(-28.0, 28.0))

        aov_base = 1305.0 if is_weekend else 1155.0
        average_order_value = _round2(aov_base + rng.uniform(-45.0, 45.0))
        dine_in_revenue = round(covers * average_order_value)

        # Delivery grows as a share of the business across the window.
        progress = i / (WINDOW_DAYS - 1)
        mix_target = DELIVERY_MIX_START_PCT + progress * (
            DELIVERY_MIX_END_PCT - DELIVERY_MIX_START_PCT
        )
        delivery_mix_pct = _round1(mix_target + rng.uniform(-0.8, 0.8))
        # Solve for the delivery figure that produces that share of the total,
        # before events are added: mix = delivery / (dine_in + delivery).
        delivery_revenue = round(
            dine_in_revenue * delivery_mix_pct / (100.0 - delivery_mix_pct)
        )

        # Private dining sits on top, and only on some days.
        events_revenue = (
            round(rng.uniform(45000, 185000))
            if rng.random() < (0.45 if is_weekend else 0.22)
            else 0
        )

        net_sales = dine_in_revenue + delivery_revenue + events_revenue

        # The documented vendor rate revision steps food cost on 16 August.
        food_cost_pct_base = 34.5 if d >= FOOD_COST_STEP_DATE else 31.0
        food_cost_pct = _round1(food_cost_pct_base + rng.uniform(-0.3, 0.3))
        food_cost_amount = round(net_sales * food_cost_pct / 100)

        # Labour is stickier than sales: a quiet Tuesday still needs a kitchen,
        # so the percentage runs higher on weekdays even though the rupee cost
        # is lower. This is the single most useful thing the dashboard shows a
        # restaurant operator, and it has to be visible in the data.
        labour_cost_pct = _round1(
            (23.8 if is_weekend else 27.9) + rng.uniform(-0.7, 0.7)
        )
        labour_cost_amount = round(net_sales * labour_cost_pct / 100)

        prime_cost_pct = _round1(food_cost_pct + labour_cost_pct)
        prime_cost_amount = food_cost_amount + labour_cost_amount

        # Rent, utilities, platform commission and the rest, as one line.
        overhead_pct = _round1(18.5 + rng.uniform(-0.5, 0.5))
        overhead_amount = round(net_sales * overhead_pct / 100)

        # Comps and voids: small, but the discipline signal operators watch.
        void_comp_pct = _round2(max(0.2, 0.75 + rng.uniform(-0.35, 0.45)))
        void_comp_amount = round(net_sales * void_comp_pct / 100)

        gop_amount = net_sales - prime_cost_amount - overhead_amount
        gop_pct = _round1(gop_amount / net_sales * 100)

        sales_per_seat = _round2(dine_in_revenue / TOTAL_SEATS)
        table_turns = _round2(covers / TOTAL_SEATS)

        # Sign-off runs high but rarely perfect; busier weekend days slip
        # slightly more often than quiet weekdays.
        misses = rng.choices(
            [0, 1, 2, 3], weights=[52, 30, 13, 5] if is_weekend else [64, 24, 9, 3]
        )[0]
        # The anchor day is pinned to one outstanding task. The demo narrates
        # "33 of 34 signed off, and here is the one that is not", which needs a
        # day that actually has exactly one gap.
        if d == ANCHOR_DATE:
            misses = 1
        tasks_signed_off = CHECKLIST_TASK_TOTAL - misses
        checklist_signoff_pct = _round1(
            tasks_signed_off / CHECKLIST_TASK_TOTAL * 100
        )

        rows.append(
            {
                "date": d.isoformat(),
                "day_of_week": d.strftime("%A"),
                "seats": TOTAL_SEATS,
                "covers": covers,
                "average_order_value": average_order_value,
                "dine_in_revenue": dine_in_revenue,
                "delivery_revenue": delivery_revenue,
                "events_revenue": events_revenue,
                "total_revenue": net_sales,
                "delivery_mix_pct": _round1(delivery_revenue / net_sales * 100),
                "sales_per_seat": sales_per_seat,
                "table_turns": table_turns,
                "food_cost_pct": food_cost_pct,
                "food_cost_amount": food_cost_amount,
                "labor_cost_pct": labour_cost_pct,
                "labor_cost_amount": labour_cost_amount,
                "prime_cost_pct": prime_cost_pct,
                "prime_cost_amount": prime_cost_amount,
                "overhead_amount": overhead_amount,
                "void_comp_pct": void_comp_pct,
                "void_comp_amount": void_comp_amount,
                "gop_amount": gop_amount,
                "gop_pct": gop_pct,
                "checklist_tasks_total": CHECKLIST_TASK_TOTAL,
                "checklist_tasks_signed_off": tasks_signed_off,
                "checklist_signoff_pct": checklist_signoff_pct,
            }
        )

    # The shape the demo narrates has to actually be in the data.
    weekend = [r for r in rows if r["day_of_week"] in ("Friday", "Saturday", "Sunday")]
    weekday = [r for r in rows if r["day_of_week"] not in ("Friday", "Saturday", "Sunday")]
    weekend_mean = sum(r["total_revenue"] for r in weekend) / len(weekend)
    weekday_mean = sum(r["total_revenue"] for r in weekday) / len(weekday)
    assert weekend_mean > weekday_mean * 1.3, (
        "the weekend premium the dashboard reports is not in the data"
    )
    assert rows[-1]["delivery_mix_pct"] > rows[0]["delivery_mix_pct"] + 3, (
        "delivery mix is meant to drift up across the window"
    )
    anchor = next(r for r in rows if r["date"] == ANCHOR_DATE.isoformat())
    assert anchor["checklist_tasks_signed_off"] == 33, "anchor-day sign-off drifted"
    assert anchor["checklist_signoff_pct"] == 97.1, "anchor-day sign-off percentage drifted"
    assert 400000 < anchor["total_revenue"] < 1200000, (
        f"anchor-day sales of {anchor['total_revenue']} is not a believable "
        "trading day for this estate"
    )

    return rows


# ---------------------------------------------------------------------------
# banquets.json
#
# Six "corporate" events average exactly 61.2% margin. BQ-2026-018 is one of
# them, deliberately the low outlier at 55.6%, caused by the complimentary
# beverage policy in data/docs/banquet-policy.md (covers > 150). Every
# event's cost lines sum exactly to revenue - net -- no rounding drift.
# ---------------------------------------------------------------------------


@dataclass
class Banquet:
    id: str
    name: str
    segment: str
    date: str
    covers: int
    venue: str
    revenue: int
    food_cost: int
    beverage_cost: int
    labor_cost: int
    other_cost: int
    net: int
    margin_pct: float

    @staticmethod
    def make(
        id_: str,
        name: str,
        segment: str,
        d: date,
        covers: int,
        venue: str,
        revenue: int,
        food_cost: int,
        beverage_cost: int,
        labor_cost: int,
        other_cost: int,
    ) -> "Banquet":
        total_cost = food_cost + beverage_cost + labor_cost + other_cost
        net = revenue - total_cost
        margin_pct = _round1(net / revenue * 100)
        return Banquet(
            id=id_,
            name=name,
            segment=segment,
            date=d.isoformat(),
            covers=covers,
            venue=venue,
            revenue=revenue,
            food_cost=food_cost,
            beverage_cost=beverage_cost,
            labor_cost=labor_cost,
            other_cost=other_cost,
            net=net,
            margin_pct=margin_pct,
        )


def build_banquets() -> list[dict]:
    events = [
        Banquet.make(
            "BQ-2026-001", "Kapoor-Mehta Wedding Sangeet", "wedding",
            date(2026, 5, 30), 109, "Astra House, Terrace Deck",
            288000, 84000, 24000, 38000, 16000,
        ),
        Banquet.make(
            "BQ-2026-002", "Rotary Club Annual Social", "celebration",
            date(2026, 6, 4), 59, "Astra Terrace, Sky Room",
            88000, 27200, 7200, 12800, 4800,
        ),
        Banquet.make(
            "BQ-2026-003", "PharmaCon Regional Meet", "group",
            date(2026, 6, 9), 76, "Astra House, Private Room",
            152000, 36800, 8800, 23200, 7200,
        ),
        Banquet.make(
            "BQ-2026-004", "Iyer-Nair Reception", "wedding",
            date(2026, 6, 14), 126, "Astra House, Terrace Deck",
            324000, 94000, 26400, 41600, 18000,
        ),
        Banquet.make(
            "BQ-2026-005", "Vantage Consulting Leadership Offsite", "corporate",
            date(2026, 6, 20), 38, "Astra House, Private Room",
            160000, 28000, 8000, 20000, 8000,
        ),
        Banquet.make(
            "BQ-2026-006", "Lions Club Charity Dinner", "celebration",
            date(2026, 6, 27), 67, "Astra Terrace, Sky Room",
            96000, 29600, 8000, 13600, 5200,
        ),
        Banquet.make(
            "BQ-2026-007", "Northbridge Insurance Agent Convention", "group",
            date(2026, 7, 3), 92, "Astra House, Private Room",
            184000, 44800, 11200, 26400, 8800,
        ),
        Banquet.make(
            "BQ-2026-008", "Desai-Shah Wedding Reception", "wedding",
            date(2026, 7, 9), 134, "Astra House, Terrace Deck",
            344000, 100000, 28000, 44000, 19200,
        ),
        Banquet.make(
            "BQ-2026-009", "Meridian Capital Quarterly Review", "corporate",
            date(2026, 7, 15), 55, "Astra House, Private Room",
            240000, 38000, 9600, 28000, 12000,
        ),
        Banquet.make(
            "BQ-2026-010", "Alumni Association Reunion", "celebration",
            date(2026, 7, 21), 80, "Astra Terrace, Sky Room",
            116000, 35200, 9600, 16000, 5600,
        ),
        Banquet.make(
            "BQ-2026-011", "Skyline Motors Dealer Conference", "group",
            date(2026, 7, 27), 88, "Astra House, Private Room",
            176000, 43200, 10400, 24800, 8000,
        ),
        Banquet.make(
            "BQ-2026-012", "Rao-Krishnan Wedding Sangeet", "corporate",
            date(2026, 8, 2), 40, "Astra House, Terrace Deck",
            140000, 22000, 6000, 16000, 6400,
        ),
        Banquet.make(
            "BQ-2026-013", "Malhotra-Bose Reception", "wedding",
            date(2026, 8, 8), 143, "Astra House, Terrace Deck",
            364000, 107200, 29600, 47200, 20000,
        ),
        Banquet.make(
            "BQ-2026-014", "Rotary Youth Awards Night", "celebration",
            date(2026, 8, 12), 63, "Astra Terrace, Sky Room",
            92000, 28000, 7600, 12800, 4800,
        ),
        Banquet.make(
            "BQ-2026-015", "Everest Freight Partner Summit", "group",
            date(2026, 8, 18), 84, "Astra House, Private Room",
            168000, 41600, 10000, 24000, 7600,
        ),
        Banquet.make(
            "BQ-2026-016", "Bhatia-Sen Wedding Reception", "wedding",
            date(2026, 8, 23), 118, "Astra House, Terrace Deck",
            304000, 89600, 24800, 40000, 16800,
        ),
        Banquet.make(
            "BQ-2026-017", "City Chamber of Commerce Gala", "celebration",
            date(2026, 8, 28), 74, "Astra Terrace, Sky Room",
            108000, 32800, 8800, 15200, 5600,
        ),
        # BQ-2026-018: the planted anomaly. 220 covers triggers the
        # complimentary beverage policy in banquet-policy.md, section 3.4 --
        # beverage cost carries 8% of revenue instead of the usual ~4-5%,
        # softening margin to 55.6% against a 61.2% corporate peer average.
        Banquet.make(
            "BQ-2026-018", "Solstice Analytics Annual Kickoff", "corporate",
            date(2026, 9, 2), 92, "Astra House, Private Room",
            200000, 36000, 16000, 24800, 12000,
        ),
        Banquet.make(
            "BQ-2026-019", "Harbourline Shipping Partner Night", "group",
            date(2026, 9, 5), 82, "Astra House, Private Room",
            164000, 40000, 9600, 23200, 7200,
        ),
        Banquet.make(
            "BQ-2026-020", "Verma-Chawla Wedding Reception", "wedding",
            date(2026, 9, 8), 130, "Astra House, Terrace Deck",
            332000, 97600, 27200, 42400, 18400,
        ),
        Banquet.make(
            "BQ-2026-021", "Ashford Legal Partners Retreat", "corporate",
            date(2026, 9, 10), 42, "Astra House, Private Room",
            180000, 32000, 7200, 22000, 8100,
        ),
        Banquet.make(
            "BQ-2026-022", "Diwali Preview Trade Social", "celebration",
            date(2026, 9, 12), 69, "Astra Terrace, Sky Room",
            102000, 31200, 8400, 14400, 5200,
        ),
        Banquet.make(
            "BQ-2026-023", "Coastline Retail Buyers Meet", "group",
            date(2026, 9, 13), 86, "Astra House, Private Room",
            172000, 42400, 10000, 24000, 7600,
        ),
        Banquet.make(
            "BQ-2026-024", "Blueprint Systems Founders Day", "corporate",
            date(2026, 9, 14), 46, "Astra House, Private Room",
            192000, 34000, 8000, 24000, 5808,
        ),
    ]

    corporate = [e for e in events if e.segment == "corporate"]
    assert len(corporate) == 6, f"expected 6 corporate events, got {len(corporate)}"
    avg_margin = _round1(sum(e.margin_pct for e in corporate) / len(corporate))
    assert avg_margin == 61.2, f"corporate average margin drifted to {avg_margin}"

    by_id = {e.id: e for e in events}
    assert by_id["BQ-2026-018"].margin_pct == 55.6, (
        f"BQ-2026-018 margin drifted to {by_id['BQ-2026-018'].margin_pct}"
    )
    for e in events:
        total_cost = e.food_cost + e.beverage_cost + e.labor_cost + e.other_cost
        assert e.revenue - total_cost == e.net, f"{e.id} waterfall does not sum to net"

    return [asdict(e) for e in events]


# ---------------------------------------------------------------------------
# submissions.json
#
# Ten days of purchase requisitions (2026-09-05 .. 2026-09-14), IDs assigned
# sequentially so the contrast pair lands exactly on SUB-004182/SUB-004183,
# both dated 2026-09-14: the same item, same day, wildly different unit
# cost. The pair is discovered by operations.py grouping same-item
# same-date rows by cost variance, not hardcoded into the route.
# ---------------------------------------------------------------------------

# What a four-outlet restaurant group actually buys in a week. The
# departments match the six in brand-standard.md 4.2, so a requisition can be
# traced to the team that raised it.
ITEM_CATALOG = [
    ("Basmati Rice 1kg", "Kitchen", "Anand Grain Traders", 58, 40),
    ("Fresh Paneer 1kg", "Kitchen", "Himalayan Dairy Co", 320, 18),
    ("Chicken Breast 1kg", "Kitchen", "Coastal Poultry Supply", 240, 35),
    ("Cold-Pressed Cooking Oil 5L", "Kitchen", "Sunfield Oils", 720, 12),
    ("LPG Cylinder 19kg", "Kitchen", "Bharat Gas Distributors", 1850, 4),
    ("Single-Origin Coffee Beans 1kg", "Bar & Beverage", "Kaapi Roasters Bengaluru", 1250, 8),
    ("Craft Tonic Case (24x200ml)", "Bar & Beverage", "Highland Mixers", 960, 6),
    ("Delivery Packaging - Meal Box (100)", "Delivery & Packaging", "EcoPack Solutions", 480, 40),
    ("Table Linen (set of 10)", "Service & Floor", "Weavers Guild Textiles", 1450, 6),
    ("Dishwash Concentrate 5L", "Facilities & Safety", "Clearline Hygiene", 640, 10),
]

CONTRAST_ITEM = "Basmati Rice 1kg"

SUBMISSIONS_START = date(2026, 9, 5)
SUBMISSIONS_DAYS = 10
SUBMISSIONS_PER_DAY = 20
# Requisition numbering continues from the property's opening ledger. The
# offset is chosen so the 2026-09-14 rows land on SUB-004181 onward, which
# puts the planted contrast pair on SUB-004182 / SUB-004183.
SUBMISSIONS_START_ID = 4001


def build_submissions() -> list[dict]:
    rng = random.Random(SEED + 1)
    rows: list[dict] = []
    counter = SUBMISSIONS_START_ID

    for day_index in range(SUBMISSIONS_DAYS):
        d = SUBMISSIONS_START + timedelta(days=day_index)
        is_anchor_day = d == ANCHOR_DATE

        # On the anchor day the filler rows skip the contrast-pair item, so
        # that day carries exactly two rows for it: the planted pair. Any
        # third row would make the "cheapest same-item line" ambiguous and
        # the detected pair would no longer be the one the demo narrates.
        catalog = (
            [row for row in ITEM_CATALOG if row[0] != CONTRAST_ITEM]
            if is_anchor_day
            else ITEM_CATALOG
        )

        day_rows = []
        for slot in range(SUBMISSIONS_PER_DAY):
            item, dept, vendor, base_cost, base_qty = catalog[slot % len(catalog)]
            qty = base_qty + rng.randint(-3, 3)
            qty = max(1, qty)
            unit_cost = round(base_cost * (1 + rng.uniform(-0.04, 0.04)))
            day_rows.append(
                {
                    "item": item,
                    "department": dept,
                    "vendor": vendor,
                    "unit_cost": unit_cost,
                    "quantity": qty,
                }
            )

        if is_anchor_day:
            # Planted contrast pair: identical item, same date, same
            # department catalogue entry, unit cost nearly 70% apart.
            # Placed at slots 1 and 2 so the IDs come out 004182 / 004183.
            day_rows[1] = {
                "item": "Basmati Rice 1kg",
                "department": "Kitchen",
                "vendor": "Anand Grain Traders",
                "unit_cost": 58,
                "quantity": 40,
            }
            day_rows[2] = {
                # Same item, same day, a different outlet's kitchen buying it
                # from a different vendor at nearly seventy per cent more.
                "item": "Basmati Rice 1kg",
                "department": "Delivery & Packaging",
                "vendor": "Sundar Wholesale Provisions",
                "unit_cost": 97,
                "quantity": 40,
            }

        for row in day_rows:
            sub_id = f"SUB-{counter:06d}"
            rows.append(
                {
                    "id": sub_id,
                    "date": d.isoformat(),
                    **row,
                    "total_cost": row["unit_cost"] * row["quantity"],
                }
            )
            counter += 1

    by_id = {r["id"]: r for r in rows}
    assert "SUB-004182" in by_id and "SUB-004183" in by_id, (
        "contrast pair IDs drifted -- adjust SUBMISSIONS_* constants"
    )
    assert by_id["SUB-004182"]["item"] == by_id["SUB-004183"]["item"] == CONTRAST_ITEM
    assert by_id["SUB-004182"]["date"] == ANCHOR_DATE.isoformat()

    # The pair must be the only rows for that item on that day, so the
    # variance rule in expense-policy.md 4.1 lands on exactly these two.
    anchor_item_rows = [
        r
        for r in rows
        if r["date"] == ANCHOR_DATE.isoformat() and r["item"] == CONTRAST_ITEM
    ]
    assert {r["id"] for r in anchor_item_rows} == {"SUB-004182", "SUB-004183"}, (
        f"expected exactly the planted pair for {CONTRAST_ITEM}, got "
        f"{[r['id'] for r in anchor_item_rows]}"
    )

    return rows


# ---------------------------------------------------------------------------
# connections.json -- the Connections screen. Every integration is
# deliberately "not_connected": this is a mock-data demo end to end.
# ---------------------------------------------------------------------------


def build_connections() -> list[dict]:
    return [
        {
            "id": "pms",
            "name": "Property Management System",
            "vendor": "IDS Next / generic PMS",
            "status": "not_connected",
            "description": "Room inventory, rates and folio data.",
        },
        {
            "id": "pos",
            "name": "Point of Sale",
            "vendor": "Micros / generic POS",
            "status": "not_connected",
            "description": "F&B outlet sales and covers.",
        },
        {
            "id": "accounting",
            "name": "Accounting Ledger",
            "vendor": "Tally / generic ERP",
            "status": "not_connected",
            "description": "Purchase requisitions and cost ledgers.",
        },
        {
            "id": "whatsapp",
            "name": "WhatsApp Business",
            "vendor": "Meta Cloud API",
            "status": "not_connected",
            "description": "Send the GM digest directly to WhatsApp.",
        },
        {
            "id": "channel_manager",
            "name": "Channel Manager",
            "vendor": "generic OTA channel manager",
            "status": "not_connected",
            "description": "OTA rate and availability sync.",
        },
    ]


# ---------------------------------------------------------------------------
# users.json -- demo login. Password stored as a salted hash so the file
# does not read as a plaintext credential dump, even though this is a demo.
# ---------------------------------------------------------------------------

import hashlib

DEMO_SALT = "dineastra-demo-2026"


def _hash_password(password: str) -> str:
    return hashlib.sha256(f"{DEMO_SALT}:{password}".encode("utf-8")).hexdigest()


def build_users() -> list[dict]:
    return [
        {
            "email": "owner@dineastra.demo",
            "name": "Rohan Ahuja",
            "role": "General Manager",
            "password_hash": _hash_password("dineastra"),
        }
    ]


# ---------------------------------------------------------------------------
# documents_meta.json -- indexes the four hand-written docs in data/docs/.
# ---------------------------------------------------------------------------


def build_documents_meta() -> list[dict]:
    return [
        {
            "id": "brand-standard",
            "title": "DineAstra Operating Standard",
            "filename": "brand-standard.md",
            "department": "All departments",
            "last_verified": "2026-09-11",
        },
        {
            "id": "banquet-policy",
            "title": "Banquet & Events Costing Policy",
            "filename": "banquet-policy.md",
            "department": "Banquets & Events",
            "last_verified": "2026-08-01",
        },
        {
            "id": "fnb-cost-policy",
            "title": "F&B Procurement & Cost Policy",
            "filename": "fnb-cost-policy.md",
            "department": "Kitchen & Stewarding",
            "last_verified": "2026-08-16",
        },
        {
            "id": "expense-policy",
            "title": "Purchase Requisition & Expense Policy",
            "filename": "expense-policy.md",
            "department": "Finance",
            "last_verified": "2026-07-20",
        },
    ]


# ---------------------------------------------------------------------------
# write helpers
# ---------------------------------------------------------------------------


def write_json(path: Path, payload) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    (DATA_DIR / "runtime").mkdir(parents=True, exist_ok=True)
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    write_json(DATA_DIR / "daily_property.json", build_daily_property())
    write_json(DATA_DIR / "banquets.json", build_banquets())
    write_json(DATA_DIR / "submissions.json", build_submissions())
    write_json(DATA_DIR / "connections.json", build_connections())
    write_json(DATA_DIR / "users.json", build_users())
    write_json(DATA_DIR / "documents_meta.json", build_documents_meta())

    print("Seeded:")
    for name in (
        "daily_property.json",
        "banquets.json",
        "submissions.json",
        "connections.json",
        "users.json",
        "documents_meta.json",
    ):
        print(f"  data/{name}")
    print("Hand-written documents expected in data/docs/ (not generated here):")
    for meta in build_documents_meta():
        exists = (DOCS_DIR / meta["filename"]).exists()
        marker = "ok" if exists else "MISSING"
        print(f"  data/docs/{meta['filename']} [{marker}]")


if __name__ == "__main__":
    main()
