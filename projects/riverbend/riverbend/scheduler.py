"""Lightweight scheduler: picks up new files, runs the API page, then rebuilds dbt marts.

This is a real recurring execution (interval from SCHEDULE_SECONDS). It is not a
full orchestrator; the point is that ingestion and transformations run on a
schedule and every run is logged.
"""
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path

from .pipeline import DATA, Pipeline

DB = DATA / "riverbend.duckdb"
INCOMING = DATA / "incoming"
DBT = Path(__file__).resolve().parents[1] / "dbt"
INTERVAL = int(os.getenv("SCHEDULE_SECONDS", "120"))


def tick() -> None:
    INCOMING.mkdir(exist_ok=True)
    # Open, write and close: DuckDB allows readers between ticks, so the
    # dashboard can query the same file without lock conflicts.
    pipe = Pipeline(DB)
    try:
        for path in sorted(INCOMING.glob("*.csv")):
            result = pipe.run_csv(path)
            print({"event": "ingest", "file": path.name, "status": result.status, "upserted": result.rows_upserted}, flush=True)
        api = DATA / "api_page_1.json"
        if api.exists():
            result = pipe.run_api(api)
            if not result.skipped:
                print({"event": "api", "upserted": result.rows_upserted}, flush=True)
        metrics = pipe.metrics()
    finally:
        pipe.close()
    subprocess.run(["dbt", "build", "--profiles-dir", "."], cwd=DBT, check=False, capture_output=True)
    print({"event": "tick", "metrics": metrics}, flush=True)


def main() -> None:
    print({"event": "scheduler_started", "interval_seconds": INTERVAL}, flush=True)
    while True:
        try:
            tick()
        except Exception as error:  # noqa: BLE001
            print({"event": "tick_failed", "error": str(error)}, flush=True)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
