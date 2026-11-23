"""Riverbend — incremental data pipeline with validation, quarantine and reconciliation.

Design notes
------------
- Raw layer is append-only: every accepted file/API page is stored with its hash,
  so a re-run of the same file is a no-op.
- Validation is explicit and each rejected row is quarantined with a reason.
- The analytics table is an upsert keyed by order_id. A row is applied only when
  its updated_at is newer than the stored one, which also handles late-arriving
  corrections (out-of-order updates).
- A watermark records the newest updated_at processed per source.
- Every run is logged with counts, status and error.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import duckdb

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

ALLOWED_CURRENCIES = {"USD", "BRL"}
ALLOWED_STATUSES = {"paid", "refunded", "cancelled"}
REQUIRED = ("order_id", "customer_id", "order_ts", "amount_cents", "currency", "status", "updated_at")


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass
class RunResult:
    run_id: str
    source: str
    rows_seen: int = 0
    rows_valid: int = 0
    rows_quarantined: int = 0
    rows_upserted: int = 0
    skipped: bool = False
    status: str = "succeeded"
    error: str | None = None
    quarantine: list[dict] = field(default_factory=list)


class Pipeline:
    def __init__(self, db_path: str | Path = ":memory:") -> None:
        self.conn = duckdb.connect(str(db_path))
        self._init_schema()

    def _init_schema(self) -> None:
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS raw")
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS staging")
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS analytics")
        self.conn.execute("CREATE SCHEMA IF NOT EXISTS ops")
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS raw.ingested_files (
                source TEXT, file_hash TEXT, path TEXT, ingested_at TEXT,
                PRIMARY KEY (source, file_hash)
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS raw.orders_raw (
                source TEXT, file_hash TEXT, ingested_at TEXT,
                order_id TEXT, customer_id TEXT, order_ts TEXT, amount_cents TEXT,
                currency TEXT, status TEXT, updated_at TEXT, payload TEXT
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS raw.quarantine (
                run_id TEXT, source TEXT, order_id TEXT, reason TEXT, payload TEXT, quarantined_at TEXT
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS analytics.orders (
                order_id TEXT PRIMARY KEY, customer_id TEXT, order_ts TIMESTAMP,
                amount_cents INTEGER, currency TEXT, status TEXT, updated_at TIMESTAMP,
                first_seen_at TEXT, updated_in_run TEXT
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS ops.runs (
                run_id TEXT PRIMARY KEY, source TEXT, started_at TEXT, finished_at TEXT,
                status TEXT, rows_seen INTEGER, rows_valid INTEGER, rows_quarantined INTEGER,
                rows_upserted INTEGER, error TEXT
            )"""
        )
        self.conn.execute(
            """CREATE TABLE IF NOT EXISTS ops.watermarks (
                source TEXT PRIMARY KEY, last_updated_at TEXT, updated_at TEXT
            )"""
        )

    # ------------------------------------------------------------------ validation
    def validate(self, row: dict) -> tuple[bool, str]:
        for key in REQUIRED:
            if row.get(key) in (None, ""):
                return False, f"missing {key}"
        try:
            amount = int(row["amount_cents"])
        except (TypeError, ValueError):
            return False, "amount_cents is not an integer"
        if amount <= 0:
            return False, "amount_cents must be positive"
        if row["currency"] not in ALLOWED_CURRENCIES:
            return False, f"unsupported currency {row['currency']}"
        if row["status"] not in ALLOWED_STATUSES:
            return False, f"unknown status {row['status']}"
        for field_name in ("order_ts", "updated_at"):
            try:
                datetime.fromisoformat(str(row[field_name]).replace("Z", "+00:00"))
            except ValueError:
                return False, f"invalid timestamp in {field_name}"
        return True, ""

    # ------------------------------------------------------------------ ingestion
    def _ingest_rows(self, source: str, digest: str, rows: Iterable[dict], run: RunResult, already: bool) -> None:
        if already:
            run.skipped = True
            return
        self.conn.execute(
            "INSERT INTO raw.ingested_files VALUES (?, ?, ?, ?)",
            [source, digest, source, utcnow()],
        )
        for row in rows:
            run.rows_seen += 1
            payload = json.dumps(row, ensure_ascii=False)
            self.conn.execute(
                "INSERT INTO raw.orders_raw VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    source,
                    digest,
                    utcnow(),
                    row.get("order_id"),
                    row.get("customer_id"),
                    row.get("order_ts"),
                    str(row.get("amount_cents")) if row.get("amount_cents") is not None else None,
                    row.get("currency"),
                    row.get("status"),
                    row.get("updated_at"),
                    payload,
                ],
            )
            valid, reason = self.validate(row)
            if not valid:
                run.rows_quarantined += 1
                run.quarantine.append({"order_id": row.get("order_id"), "reason": reason})
                self.conn.execute(
                    "INSERT INTO raw.quarantine VALUES (?, ?, ?, ?, ?, ?)",
                    [run.run_id, source, row.get("order_id"), reason, payload, utcnow()],
                )
                continue
            run.rows_valid += 1
            self._upsert(source, row, run)

    def _upsert(self, source: str, row: dict, run: RunResult) -> None:
        updated = datetime.fromisoformat(str(row["updated_at"]).replace("Z", "+00:00")).replace(tzinfo=None)
        order_ts = datetime.fromisoformat(str(row["order_ts"]).replace("Z", "+00:00")).replace(tzinfo=None)
        existing = self.conn.execute(
            "SELECT updated_at FROM analytics.orders WHERE order_id = ?", [row["order_id"]]
        ).fetchone()
        # Late or out-of-order updates are ignored unless they are actually newer.
        if existing and existing[0] is not None and updated <= existing[0]:
            return
        self.conn.execute(
            """INSERT INTO analytics.orders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT (order_id) DO UPDATE SET
                 customer_id = excluded.customer_id, order_ts = excluded.order_ts,
                 amount_cents = excluded.amount_cents, currency = excluded.currency,
                 status = excluded.status, updated_at = excluded.updated_at,
                 updated_in_run = excluded.updated_in_run""",
            [
                row["order_id"],
                row["customer_id"],
                order_ts,
                int(row["amount_cents"]),
                row["currency"],
                row["status"],
                updated,
                utcnow(),
                run.run_id,
            ],
        )
        run.rows_upserted += 1
        self.conn.execute(
            """INSERT INTO ops.watermarks VALUES (?, ?, ?)
               ON CONFLICT (source) DO UPDATE SET
                 last_updated_at = GREATEST(ops.watermarks.last_updated_at, excluded.last_updated_at),
                 updated_at = excluded.updated_at""",
            [source, str(updated), utcnow()],
        )

    # ------------------------------------------------------------------ sources
    def run_csv(self, path: Path | str, source: str | None = None) -> RunResult:
        path = Path(path)
        name = source or f"csv:{path.name}"
        run = RunResult(run_id=f"run_{utcnow()}_{uuid.uuid4().hex[:6]}_{name}", source=name)
        self.conn.execute(
            "INSERT INTO ops.runs VALUES (?, ?, ?, NULL, 'running', 0, 0, 0, 0, NULL)",
            [run.run_id, name, utcnow()],
        )
        try:
            digest = file_hash(path)
            already = self.conn.execute(
                "SELECT 1 FROM raw.ingested_files WHERE source = ? AND file_hash = ?", [name, digest]
            ).fetchone() is not None
            rows = []
            if not already:
                import csv

                with path.open(newline="", encoding="utf-8") as handle:
                    rows = list(csv.DictReader(handle))
            self._ingest_rows(name, digest, rows, run, already)
        except Exception as error:  # noqa: BLE001
            run.status = "failed"
            run.error = str(error)
        self._finish(run)
        return run

    def run_api(self, path: Path | str, source: str = "api:orders") -> RunResult:
        path = Path(path)
        run = RunResult(run_id=f"run_{utcnow()}_{uuid.uuid4().hex[:6]}_{source}", source=source)
        self.conn.execute(
            "INSERT INTO ops.runs VALUES (?, ?, ?, NULL, 'running', 0, 0, 0, 0, NULL)",
            [run.run_id, source, utcnow()],
        )
        try:
            digest = file_hash(path)
            already = self.conn.execute(
                "SELECT 1 FROM raw.ingested_files WHERE source = ? AND file_hash = ?", [source, digest]
            ).fetchone() is not None
            rows = [] if already else (json.loads(path.read_text(encoding="utf-8")).get("data") or [])
            self._ingest_rows(source, digest, rows, run, already)
        except Exception as error:  # noqa: BLE001
            run.status = "failed"
            run.error = str(error)
        self._finish(run)
        return run

    def _finish(self, run: RunResult) -> None:
        self.conn.execute(
            """UPDATE ops.runs SET finished_at = ?, status = ?, rows_seen = ?, rows_valid = ?,
               rows_quarantined = ?, rows_upserted = ?, error = ? WHERE run_id = ?""",
            [
                utcnow(),
                run.status,
                run.rows_seen,
                run.rows_valid,
                run.rows_quarantined,
                run.rows_upserted,
                run.error,
                run.run_id,
            ],
        )

    # ------------------------------------------------------------------ reporting
    def metrics(self) -> dict:
        row = self.conn.execute(
            """SELECT
                 COUNT(*)::INT AS orders,
                 COALESCE(SUM(amount_cents) FILTER (WHERE status = 'paid'), 0)::BIGINT AS paid_revenue_cents,
                 COALESCE(ROUND(AVG(amount_cents) FILTER (WHERE status = 'paid')), 0)::BIGINT AS avg_paid_order_cents,
                 COUNT(*) FILTER (WHERE status = 'cancelled')::INT AS cancelled_orders,
                 COUNT(*) FILTER (WHERE status = 'refunded')::INT AS refunded_orders
               FROM analytics.orders"""
        ).fetchone()
        quarantined = self.conn.execute("SELECT COUNT(*)::INT FROM raw.quarantine").fetchone()[0]
        watermark = self.conn.execute(
            "SELECT MAX(last_updated_at) FROM ops.watermarks"
        ).fetchone()[0]
        orders, revenue, avg, cancelled, refunded = row
        return {
            "orders": orders,
            "paid_revenue_cents": int(revenue),
            "avg_paid_order_cents": int(avg),
            "cancellation_rate": round(cancelled / orders, 4) if orders else 0.0,
            "refunded_orders": refunded,
            "quarantined_rows": int(quarantined),
            "watermark": watermark,
        }

    def reconcile(self) -> dict:
        """Numbers the dashboard shows, recomputed from the persisted rows."""
        total = self.conn.execute("SELECT COALESCE(SUM(amount_cents),0)::BIGINT FROM analytics.orders WHERE status='paid'").fetchone()[0]
        by_currency = self.conn.execute(
            "SELECT currency, COUNT(*)::INT, SUM(amount_cents)::BIGINT FROM analytics.orders GROUP BY currency ORDER BY currency"
        ).fetchall()
        return {"paid_revenue_cents": int(total), "by_currency": by_currency}
