# Riverbend

**Incremental Data Pipeline with Data Quality Monitoring and a Reconciliable Dashboard**

Personal demo project. Imperfect source data goes through a raw layer, validation, quarantine and an
incremental upsert; a dashboard shows business indicators that reconcile with SQL.

## Incremental strategy

- **Raw layer is append-only.** Every file/API page is stored with its SHA-256 and ingested once.
  Re-running the same file is a no-op.
- **Stable key:** `order_id`. The analytics table is an upsert, not a truncate-and-reload.
- **Watermark:** the newest `updated_at` processed per source is recorded in `ops.watermarks`.
- **Late and out-of-order events:** a row is applied only when its `updated_at` is newer than the
  stored one, so an older correction never overwrites a newer state.
- **Corrections:** a previously quarantined row can arrive valid later and is then applied.
- **Quarantine:** every rejected row keeps the source row and a reason; nothing is silently dropped.
- **Run log:** each run records counts, status, error and timestamps in `ops.runs`.

## Current state

Core pipeline and tests are implemented:

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q
```

7 tests: initial load with quarantine, idempotent re-run, new records, correction of an existing row,
late older event ignored, API page upsert, reconciliation against a manual SQL sum.

## Live demo

https://riverbend.5-222-1-215.sslip.io — read-only Streamlit dashboard backed by the same DuckDB file
the scheduler writes.

- dbt models: `staging.stg_orders`, `marts.fct_daily_revenue`, `marts.dim_customers`.
- dbt build: 13/13 PASS (models and data tests).
- Scheduler: checks `data/incoming/*.csv` and the API page on an interval, then rebuilds the marts.
- The dashboard never triggers ingestion; only the scheduler writes.
- Simulated incoming files are dropped in data/incoming; the scheduler picks them up on the next tick.
