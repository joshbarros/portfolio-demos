"""Command line for the Riverbend demo."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .pipeline import DATA, Pipeline

DB = DATA / "riverbend.duckdb"


def seed(db: Path = DB) -> dict:
    if db.exists():
        db.unlink()
    pipe = Pipeline(db)
    results = [pipe.run_csv(DATA / "orders_v1.csv"), pipe.run_csv(DATA / "orders_v2.csv"), pipe.run_api(DATA / "api_page_1.json")]
    return {
        "runs": [
            {
                "source": r.source,
                "seen": r.rows_seen,
                "valid": r.rows_valid,
                "quarantined": r.rows_quarantined,
                "upserted": r.rows_upserted,
                "skipped": r.skipped,
            }
            for r in results
        ],
        "metrics": pipe.metrics(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["seed", "metrics"])
    args = parser.parse_args()
    if args.command == "seed":
        print(json.dumps(seed(), indent=2))
    else:
        print(json.dumps(Pipeline(DB).metrics(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
