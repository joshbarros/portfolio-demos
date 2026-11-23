# Evidence

**Date:** 2026-11-23
**Public report:** https://harborlift.5-222-1-215.sslip.io
**Screenshot:** `portfolio/screenshots/01-run-report.png`

## Verified (21 steps, all ok)

| Step | Observed |
|---|---|
| Seed + control | 6 orders, checksum 2115ea8f… |
| Freeze source | write rejected: `cannot execute INSERT in a read-only transaction` |
| Backup | pg_dump 3752 bytes |
| Restore target | 3752 bytes restored |
| Migration | region column, backfill, not null, index |
| Validate | checksum equal, 6 rows, 0 null regions, index present |
| Cutover | app on target, GET /orders 200 |
| Write after cutover | rejected with 409 (read-only) |
| Rollback | target app stopped, source unfrozen, app on source 200 |
| Rollback validate | checksum equal, 6 rows |
| Write after rollback | accepted (201, ord_after_rollback) |

Timings are in the run report (backup ~150 ms, restore ~90 ms, validation ~45 ms).

## Environment and strategy

Local Docker Compose: source-db 5441, target-db 5442, app 8181. Write-freeze window covering
snapshot, cutover and rollback. Recovery point = snapshot. No zero-downtime or zero-loss claim.
