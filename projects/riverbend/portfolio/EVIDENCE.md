# Evidence

**Date:** 2026-11-23
**Public dashboard:** https://riverbend.5-222-1-215.sslip.io
**Screenshots:** `portfolio/screenshots/01-dashboard.png`, `02-public-dashboard.png`
**Video:** `portfolio/video/riverbend-demo.mp4` (42.8 s: load → defect → quarantine → correction → indicators)

## Verified

| Scenario | Observed |
|---|---|
| Initial load | 8 rows seen, 4 valid, 4 quarantined |
| Quarantine reasons | missing amount_cents, amount_cents must be positive, unknown status unknown, unsupported currency EUR |
| Re-run same file | skipped by file hash, no duplication |
| New records + correction | 3 valid, 3 upserted; ord_1004 corrected to 9900 |
| Late older event | ignored (amount stays 12500) |
| API page | 2 rows: one new, one correction from quarantine |
| dbt build | 13/13 PASS (models + tests including a business rule) |
| Reconciliation | dashboard revenue equals `sum(amount_cents)` for paid orders |
| Scheduled execution | scheduler runs on an interval and logs each tick |

Metrics at capture: 9 orders, $877.00 paid revenue, $125.29 average, 11.1% cancellation, 4 quarantined.

Tests: 7 pipeline tests + dbt data tests, all passing.
