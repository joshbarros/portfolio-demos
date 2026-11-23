# Harborlift

**Application and Database Migration Lab with Verified Rollback**

Reproducible lab that migrates a small legacy application and its Postgres database from a source
stack to a target stack, verifies integrity, cuts over, and proves rollback.

## Environment (chosen and identified)

Isolated stacks on one host, using Docker Compose:

| Role | Container | Port |
|---|---|---|
| Source database | `harborlift-source-db-1` | 5441 |
| Target database | `harborlift-target-db-1` | 5442 |
| Legacy app | `harborlift/app.py` (Flask) | 8181, pointed at either DB |

Compose is the declarative infrastructure used by the lab (the Terraform-equivalent for this local
scope). No shared demo host is touched; teardown only removes this compose project.

## Write-freeze strategy (chosen)

A **write-freeze window** covers the consistent snapshot, the cutover and the rollback exercise. Both
databases are set to `default_transaction_read_only = on`; write attempts are rejected and recorded.
This avoids pretending that a copy plus a rollback is lossless.

- Recovery point: the snapshot taken inside the freeze window.
- Allowed loss in this lab: **zero writes accepted during the window**; writes that would have
  arrived are rejected, not silently dropped.
- Once the rollback is verified, the source is unfrozen and accepts writes again.

## Flow

1. Seed source with fictional customers, orders and a control row (checksum + row count).
2. Freeze source; attempt a write and record the rejection.
3. `pg_dump` a consistent backup; record size and time.
4. Restore into the target.
5. Apply a versioned migration (customer region, not null, index).
6. Validate: checksum, row count, nulls, index, and the app returning orders.
7. Freeze target; cut over the app to the target.
8. Attempt a write after cutover; record the rejection.
9. Roll back: stop the target app, unfreeze source, point the app back; validate checksum and behavior.
10. Record every step's duration and result; write `web/last_run.json` and `web/report.html`.

## Live run report

https://harborlift.5-222-1-215.sslip.io — static page with the last recorded run (date, environment, strategy). The demo cannot restore databases or run infrastructure.

## Run

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
docker compose up -d
python -m harborlift.lab
```

The public page (`web/report.html`) shows the **last recorded run** with date, environment and the
freeze strategy. It is static: visitors cannot run Terraform, restore databases or destroy anything.
The reproducible scripts are in the repository.

## Screenshots / video

- Source and target tables, integrity check and rollback result are captured from the run.
- Video: migration → validation → cutover → verified rollback.

## Limitations

- Local Docker Compose, not a cloud migration; concepts (snapshot consistency, freeze window,
  validation, rollback drill) are transferable, but this is not a Databricks/Snowflake/AWS migration.
- The app is minimal; it proves read/write behavior, not a full production workload.
- No zero-downtime claim: the freeze window is explicit and short.
- Backups live in `/tmp` inside the lab; no long-term retention.
