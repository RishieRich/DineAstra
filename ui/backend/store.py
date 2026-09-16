"""Where uploaded records live.

Two implementations behind one small interface:

* **Postgres** when ``DATABASE_URL`` is set. This is what runs on Vercel,
  where the filesystem is read-only and thrown away between invocations.
* **A JSON file** otherwise, so a clone with no database still runs and the
  test suite needs no server.

The interface is deliberately read-all / replace-all rather than a set of
fine-grained SQL operations. The demo's import history is tens of rows, not
millions; doing it this way keeps one code path through ``ingest`` for both
backends, makes every write a single transaction, and leaves nothing to drift
between the two. If this ever holds real volume, that is the first thing to
change.

**Workspaces.** A published demo link is opened by people who do not know each
other. Every record is therefore scoped to a workspace id that the browser
generates and keeps; one visitor loading sample data, uploading a file, or
clearing everything cannot touch another's. The seeded sample dataset under
``data/`` is read-only and shared by everyone.
"""

from __future__ import annotations

import json
import os
import re
import threading
from contextvars import ContextVar
from pathlib import Path
from typing import Protocol

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_WORKSPACE = "demo"

# Everything this app creates lives in its own schema. The Neon database it
# was pointed at already hosts an unrelated application in `public`, and a
# demo has no business creating tables next to someone else's.
SCHEMA = "dineastra"


class Store(Protocol):
    def read_all(self, workspace: str) -> list[dict]: ...
    def replace_all(self, workspace: str, rows: list[dict]) -> None: ...
    def clear(self, workspace: str) -> int: ...
    def put_report(self, workspace: str, batch_id: str, csv: str) -> None: ...
    def get_report(self, workspace: str, batch_id: str) -> str | None: ...


# ---------------------------------------------------------------------------
# file-backed: local development and the test suite
# ---------------------------------------------------------------------------


class FileStore:
    """One JSON file per workspace, plus reject reports beside them."""

    def __init__(self, directory: Path):
        self.directory = directory
        self._lock = threading.Lock()

    def _history_path(self, workspace: str) -> Path:
        if workspace == DEFAULT_WORKSPACE:
            # The original single-workspace filename, so an existing local
            # history is not orphaned by the introduction of workspaces.
            return self.directory / "import_history.json"
        safe = "".join(c for c in workspace if c.isalnum() or c in "-_")[:64]
        return self.directory / f"import_history.{safe}.json"

    def _report_path(self, workspace: str, batch_id: str) -> Path:
        safe_ws = "".join(c for c in workspace if c.isalnum() or c in "-_")[:64]
        return self.directory / "reject_reports" / safe_ws / f"{batch_id}.csv"

    def read_all(self, workspace: str) -> list[dict]:
        path = self._history_path(workspace)
        if not path.exists():
            return []
        return json.loads(path.read_text(encoding="utf-8"))

    def replace_all(self, workspace: str, rows: list[dict]) -> None:
        path = self._history_path(workspace)
        with self._lock:
            path.parent.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".tmp")
            temporary.write_text(
                json.dumps(rows, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            temporary.replace(path)

    def clear(self, workspace: str) -> int:
        removed = len(self.read_all(workspace))
        with self._lock:
            self._history_path(workspace).unlink(missing_ok=True)
            reports = self._report_path(workspace, "x").parent
            if reports.exists():
                for report in reports.glob("*.csv"):
                    report.unlink(missing_ok=True)
        return removed

    def put_report(self, workspace: str, batch_id: str, csv: str) -> None:
        path = self._report_path(workspace, batch_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(csv, encoding="utf-8")

    def get_report(self, workspace: str, batch_id: str) -> str | None:
        path = self._report_path(workspace, batch_id)
        return path.read_text(encoding="utf-8") if path.exists() else None


# ---------------------------------------------------------------------------
# Postgres-backed: Vercel
# ---------------------------------------------------------------------------

SCHEMA_SQL = f"""
create schema if not exists {SCHEMA};

create table if not exists {SCHEMA}.import_versions (
    id            bigserial primary key,
    workspace_id  text        not null,
    version_id    text        not null,
    position      integer     not null,
    row           jsonb       not null,
    created_at    timestamptz not null default now(),
    unique (workspace_id, version_id)
);

create index if not exists import_versions_workspace_position
    on {SCHEMA}.import_versions (workspace_id, position);

create table if not exists {SCHEMA}.reject_reports (
    workspace_id  text        not null,
    batch_id      text        not null,
    csv           text        not null,
    created_at    timestamptz not null default now(),
    primary key (workspace_id, batch_id)
);
"""


class PostgresStore:
    """The same history, stored as ordered JSONB rows.

    The row order matters -- the type-2 history is read back as a list and the
    closing of a previous version depends on it -- so `position` is stored
    explicitly rather than trusted to come back in insertion order.
    """

    def __init__(self, dsn: str):
        self.dsn = dsn
        self._ready = False
        self._lock = threading.Lock()

    def _connect(self):
        import psycopg

        return psycopg.connect(self.dsn, connect_timeout=15)

    def _ensure_schema(self) -> None:
        if self._ready:
            return
        with self._lock:
            if self._ready:
                return
            with self._connect() as conn, conn.cursor() as cur:
                cur.execute(SCHEMA_SQL)
                conn.commit()
            self._ready = True

    def read_all(self, workspace: str) -> list[dict]:
        self._ensure_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"select row from {SCHEMA}.import_versions "
                "where workspace_id = %s order by position",
                (workspace,),
            )
            return [record[0] for record in cur.fetchall()]

    def replace_all(self, workspace: str, rows: list[dict]) -> None:
        self._ensure_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"delete from {SCHEMA}.import_versions where workspace_id = %s",
                (workspace,),
            )
            if rows:
                cur.executemany(
                    f"insert into {SCHEMA}.import_versions "
                    "(workspace_id, version_id, position, row) values (%s, %s, %s, %s)",
                    [
                        (workspace, row["version_id"], index, json.dumps(row))
                        for index, row in enumerate(rows)
                    ],
                )
            conn.commit()

    def clear(self, workspace: str) -> int:
        self._ensure_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"delete from {SCHEMA}.import_versions where workspace_id = %s",
                (workspace,),
            )
            removed = cur.rowcount or 0
            cur.execute(
                f"delete from {SCHEMA}.reject_reports where workspace_id = %s",
                (workspace,),
            )
            conn.commit()
            return removed

    def put_report(self, workspace: str, batch_id: str, csv: str) -> None:
        self._ensure_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"insert into {SCHEMA}.reject_reports (workspace_id, batch_id, csv) "
                "values (%s, %s, %s) on conflict (workspace_id, batch_id) "
                "do update set csv = excluded.csv",
                (workspace, batch_id, csv),
            )
            conn.commit()

    def get_report(self, workspace: str, batch_id: str) -> str | None:
        self._ensure_schema()
        with self._connect() as conn, conn.cursor() as cur:
            cur.execute(
                f"select csv from {SCHEMA}.reject_reports "
                "where workspace_id = %s and batch_id = %s",
                (workspace, batch_id),
            )
            found = cur.fetchone()
            return found[0] if found else None


# ---------------------------------------------------------------------------
# selection
# ---------------------------------------------------------------------------

_store: Store | None = None


def get_store() -> Store:
    """The store this process uses, chosen once from the environment."""
    global _store
    if _store is None:
        dsn = os.getenv("DATABASE_URL", "").strip()
        _store = (
            PostgresStore(dsn)
            if dsn
            else FileStore(REPO_ROOT / "data" / "runtime")
        )
    return _store


def set_store(store: Store | None) -> None:
    """Point the process at a different store. Used by the tests."""
    global _store
    _store = store


def backend_name() -> str:
    store = get_store()
    return "postgres" if isinstance(store, PostgresStore) else "file"


# ---------------------------------------------------------------------------
# the workspace of the request being served
# ---------------------------------------------------------------------------

_workspace: ContextVar[str] = ContextVar("dineastra_workspace", default=DEFAULT_WORKSPACE)

# Browsers send this; anything else is refused rather than sanitised, because a
# workspace id is an isolation boundary and a half-accepted one is worse than
# no isolation at all.
_WORKSPACE_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def valid_workspace(value: str | None) -> str | None:
    """The workspace id, if it is one we will accept."""
    if not value:
        return None
    return value if _WORKSPACE_PATTERN.fullmatch(value) else None


def current_workspace() -> str:
    return _workspace.get()


def set_workspace(workspace: str):
    """Bind the workspace for this request. Returns a token to reset with."""
    return _workspace.set(workspace or DEFAULT_WORKSPACE)


def reset_workspace(token) -> None:
    _workspace.reset(token)
