# Evidence

**Date:** 2026-11-23
**Environment:** local Docker Compose (WordPress 6.7, WooCommerce 9.5.1, MySQL 8, fictional API)
**Demo:** http://127.0.0.1:8080/wp-admin (admin/demo) — local only, not publicly exposed
**Screenshots:** `portfolio/screenshots/01-admin-sync-log.png`, `02-products.png`
**Video:** `portfolio/video/woobridge-demo.mp4` (31 s)

## Checks (11/11 passing)

| Check | Result |
|---|---|
| Plugin active | PASS |
| First import | 3 products created (2 pages of 2/1) |
| Re-run | created 0, updated 3; product count unchanged |
| Price update from source | 49.90 → 59.90 |
| Invalid payload | error reported, run continues |
| Temporary API failure | 503 reported |
| Recovery after failure | ok, no duplication |
| Concurrent sync | blocked by lock |
| Pagination | second page reached (ext_1003) |
| Unsigned webhook | 401 |
| Webhook signature | HMAC verified in code |

## Video

Adjusts the source price, runs the sync, shows the notice and log (`created: 0, updated: 3, errors: 0`)
and then the WooCommerce product with the updated price.
