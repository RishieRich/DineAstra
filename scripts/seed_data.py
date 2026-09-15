"""Deterministic data generator for the Darpan demo.

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

ROOMS_AVAILABLE = 180
# brand-standard.md section 4.2 sets 34 daily tasks across 6 departments, and
# section 5 measures compliance as the share signed off. Target 100%, owner
# reporting threshold 95%.
CHECKLIST_TASK_TOTAL = 34
SEED = 20260914  # fixed seed -> deterministic across runs


def _round1(x: float) -> float:
    return round(x + 1e-9, 1)


def _round2(x: float) -> float:
    return round(x + 1e-9, 2)


# ---------------------------------------------------------------------------
# daily_property.json
# ---------------------------------------------------------------------------


def build_daily_property() -> list[dict]:
    rng = random.Random(SEED)
    rows: list[dict] = []

    for i in range(WINDOW_DAYS):
        d = START_DATE + timedelta(days=i)
        weekday = d.weekday()  # Monday=0 ... Sunday=6
        is_weekday_heavy = weekday <= 3  # Mon-Thu, corporate-driven property

        occ_base = 78.0 if is_weekday_heavy else 61.0
        occ_noise = rng.uniform(-3.0, 3.0)
        occupancy_pct = _round1(min(96.0, max(48.0, occ_base + occ_noise)))

        adr_base = 9600.0 if is_weekday_heavy else 8250.0
        adr_noise = rng.uniform(-180.0, 180.0)
        adr = round(adr_base + adr_noise)

        rooms_sold = round(ROOMS_AVAILABLE * occupancy_pct / 100)
        room_revenue = rooms_sold * adr
        revpar = _round2(adr * occupancy_pct / 100)

        fnb_base = 340000.0 if is_weekday_heavy else 265000.0
        fnb_revenue = round(fnb_base + rng.uniform(-15000.0, 15000.0))

        other_revenue = round(28000 + rng.uniform(-4000, 4000))

        food_cost_pct_base = 34.5 if d >= FOOD_COST_STEP_DATE else 31.0
        food_cost_pct = _round1(food_cost_pct_base + rng.uniform(-0.3, 0.3))
        food_cost_amount = round(fnb_revenue * food_cost_pct / 100)

        labor_cost_pct = _round1(27.5 + rng.uniform(-0.6, 0.6))
        labor_cost_amount = round(
            (room_revenue + fnb_revenue) * labor_cost_pct / 100
        )

        other_cost_amount = round(other_revenue * 0.55)

        total_revenue = room_revenue + fnb_revenue + other_revenue
        total_cost = food_cost_amount + labor_cost_amount + other_cost_amount
        gop_amount = total_revenue - total_cost
        gop_pct = _round1(gop_amount / total_revenue * 100)

        # Sign-off runs high but rarely perfect; busier weekdays slip slightly
        # more often than quiet weekend days.
        misses = rng.choices(
            [0, 1, 2, 3], weights=[52, 30, 13, 5] if is_weekday_heavy else [64, 24, 9, 3]
        )[0]
        tasks_signed_off = CHECKLIST_TASK_TOTAL - misses
        checklist_signoff_pct = _round1(
            tasks_signed_off / CHECKLIST_TASK_TOTAL * 100
        )

        rows.append(
            {
                "date": d.isoformat(),
                "day_of_week": d.strftime("%A"),
                "rooms_available": ROOMS_AVAILABLE,
                "rooms_sold": rooms_sold,
                "occupancy_pct": occupancy_pct,
                "adr": adr,
                "revpar": revpar,
                "room_revenue": room_revenue,
                "fnb_revenue": fnb_revenue,
                "other_revenue": other_revenue,
                "total_revenue": total_revenue,
                "food_cost_pct": food_cost_pct,
                "food_cost_amount": food_cost_amount,
                "labor_cost_pct": labor_cost_pct,
                "labor_cost_amount": labor_cost_amount,
                "other_cost_amount": other_cost_amount,
                "gop_amount": gop_amount,
                "gop_pct": gop_pct,
                "checklist_tasks_total": CHECKLIST_TASK_TOTAL,
                "checklist_tasks_signed_off": tasks_signed_off,
                "checklist_signoff_pct": checklist_signoff_pct,
            }
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
            date(2026, 5, 30), 260, "Grand Lawn",
            720000, 210000, 60000, 95000, 40000,
        ),
        Banquet.make(
            "BQ-2026-002", "Rotary Club Annual Social", "social",
            date(2026, 6, 4), 140, "Terrace Hall",
            220000, 68000, 18000, 32000, 12000,
        ),
        Banquet.make(
            "BQ-2026-003", "PharmaCon Regional Meet", "mice",
            date(2026, 6, 9), 180, "Conference Wing",
            380000, 92000, 22000, 58000, 18000,
        ),
        Banquet.make(
            "BQ-2026-004", "Iyer-Nair Reception", "wedding",
            date(2026, 6, 14), 300, "Grand Lawn",
            810000, 235000, 66000, 104000, 45000,
        ),
        Banquet.make(
            "BQ-2026-005", "Vantage Consulting Leadership Offsite", "corporate",
            date(2026, 6, 20), 90, "Conference Wing",
            400000, 70000, 20000, 50000, 20000,
        ),
        Banquet.make(
            "BQ-2026-006", "Lions Club Charity Dinner", "social",
            date(2026, 6, 27), 160, "Terrace Hall",
            240000, 74000, 20000, 34000, 13000,
        ),
        Banquet.make(
            "BQ-2026-007", "Northbridge Insurance Agent Convention", "mice",
            date(2026, 7, 3), 220, "Conference Wing",
            460000, 112000, 28000, 66000, 22000,
        ),
        Banquet.make(
            "BQ-2026-008", "Desai-Shah Wedding Reception", "wedding",
            date(2026, 7, 9), 320, "Grand Lawn",
            860000, 250000, 70000, 110000, 48000,
        ),
        Banquet.make(
            "BQ-2026-009", "Meridian Capital Quarterly Review", "corporate",
            date(2026, 7, 15), 130, "Conference Wing",
            600000, 95000, 24000, 70000, 30000,
        ),
        Banquet.make(
            "BQ-2026-010", "Alumni Association Reunion", "social",
            date(2026, 7, 21), 190, "Terrace Hall",
            290000, 88000, 24000, 40000, 14000,
        ),
        Banquet.make(
            "BQ-2026-011", "Skyline Motors Dealer Conference", "mice",
            date(2026, 7, 27), 210, "Conference Wing",
            440000, 108000, 26000, 62000, 20000,
        ),
        Banquet.make(
            "BQ-2026-012", "Rao-Krishnan Wedding Sangeet", "corporate",
            date(2026, 8, 2), 95, "Grand Lawn",
            350000, 55000, 15000, 40000, 16000,
        ),
        Banquet.make(
            "BQ-2026-013", "Malhotra-Bose Reception", "wedding",
            date(2026, 8, 8), 340, "Grand Lawn",
            910000, 268000, 74000, 118000, 50000,
        ),
        Banquet.make(
            "BQ-2026-014", "Rotary Youth Awards Night", "social",
            date(2026, 8, 12), 150, "Terrace Hall",
            230000, 70000, 19000, 32000, 12000,
        ),
        Banquet.make(
            "BQ-2026-015", "Everest Freight Partner Summit", "mice",
            date(2026, 8, 18), 200, "Conference Wing",
            420000, 104000, 25000, 60000, 19000,
        ),
        Banquet.make(
            "BQ-2026-016", "Bhatia-Sen Wedding Reception", "wedding",
            date(2026, 8, 23), 280, "Grand Lawn",
            760000, 224000, 62000, 100000, 42000,
        ),
        Banquet.make(
            "BQ-2026-017", "City Chamber of Commerce Gala", "social",
            date(2026, 8, 28), 175, "Terrace Hall",
            270000, 82000, 22000, 38000, 14000,
        ),
        # BQ-2026-018: the planted anomaly. 220 covers triggers the
        # complimentary beverage policy in banquet-policy.md, section 3.4 --
        # beverage cost carries 8% of revenue instead of the usual ~4-5%,
        # softening margin to 55.6% against a 61.2% corporate peer average.
        Banquet.make(
            "BQ-2026-018", "Solstice Analytics Annual Kickoff", "corporate",
            date(2026, 9, 2), 220, "Conference Wing",
            500000, 90000, 40000, 62000, 30000,
        ),
        Banquet.make(
            "BQ-2026-019", "Harbourline Shipping Partner Night", "mice",
            date(2026, 9, 5), 195, "Conference Wing",
            410000, 100000, 24000, 58000, 18000,
        ),
        Banquet.make(
            "BQ-2026-020", "Verma-Chawla Wedding Reception", "wedding",
            date(2026, 9, 8), 310, "Grand Lawn",
            830000, 244000, 68000, 106000, 46000,
        ),
        Banquet.make(
            "BQ-2026-021", "Ashford Legal Partners Retreat", "corporate",
            date(2026, 9, 10), 100, "Conference Wing",
            450000, 80000, 18000, 55000, 20250,
        ),
        Banquet.make(
            "BQ-2026-022", "Diwali Preview Trade Social", "social",
            date(2026, 9, 12), 165, "Terrace Hall",
            255000, 78000, 21000, 36000, 13000,
        ),
        Banquet.make(
            "BQ-2026-023", "Coastline Retail Buyers Meet", "mice",
            date(2026, 9, 13), 205, "Conference Wing",
            430000, 106000, 25000, 60000, 19000,
        ),
        Banquet.make(
            "BQ-2026-024", "Blueprint Systems Founders Day", "corporate",
            date(2026, 9, 14), 110, "Conference Wing",
            480000, 85000, 20000, 60000, 14520,
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

ITEM_CATALOG = [
    ("Basmati Rice 1kg", "Kitchen & Stewarding", "Anand Grain Traders", 58, 40),
    ("Fresh Paneer 1kg", "Kitchen & Stewarding", "Himalayan Dairy Co", 320, 18),
    ("Chicken Breast 1kg", "Kitchen & Stewarding", "Coastal Poultry Supply", 240, 35),
    ("Table Linen (set of 10)", "Banquets & Events", "Weavers Guild Textiles", 1450, 6),
    ("LPG Cylinder 19kg", "Kitchen & Stewarding", "Bharat Gas Distributors", 1850, 4),
    ("Housekeeping Amenity Kit", "Housekeeping", "Comfort Line Supplies", 95, 120),
    ("Printer Toner Cartridge", "Front Office", "OfficeMax Traders", 2400, 3),
    ("Fresh Cut Flowers (bunch)", "Banquets & Events", "Bloom & Petal Florists", 380, 25),
    ("Mineral Water Case (24x1L)", "F&B Service", "Himalayan Springs Ltd", 340, 30),
    ("Bath Towel (set of 5)", "Housekeeping", "Comfort Line Supplies", 1650, 10),
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
                "department": "Kitchen & Stewarding",
                "vendor": "Anand Grain Traders",
                "unit_cost": 58,
                "quantity": 40,
            }
            day_rows[2] = {
                "item": "Basmati Rice 1kg",
                "department": "Banquets & Events",
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

DEMO_SALT = "darpan-demo-2026"


def _hash_password(password: str) -> str:
    return hashlib.sha256(f"{DEMO_SALT}:{password}".encode("utf-8")).hexdigest()


def build_users() -> list[dict]:
    return [
        {
            "email": "owner@darpan.demo",
            "name": "Rohan Ahuja",
            "role": "General Manager",
            "password_hash": _hash_password("darpan"),
        }
    ]


# ---------------------------------------------------------------------------
# documents_meta.json -- indexes the four hand-written docs in data/docs/.
# ---------------------------------------------------------------------------


def build_documents_meta() -> list[dict]:
    return [
        {
            "id": "brand-standard",
            "title": "Darpan Brand Standard",
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
