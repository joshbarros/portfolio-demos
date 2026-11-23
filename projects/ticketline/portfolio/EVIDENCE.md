# Evidence

**Date:** 2026-11-23
**Public URL:** https://ticketline.5-222-1-215.sslip.io
**Demo PDF:** `portfolio/invoice-demo.pdf` (rendered page in `screenshots/04-invoice-pdf-1.png`)

## Verified

| Scenario | Observed |
|---|---|
| Full flow | Create → submit → approve → issue; history has 4 entries |
| Real PDF | `%PDF` header, text extraction shows invoice number, client, ticket, items and total |
| Duplicate issuance | Second request rejected with 409 |
| Technician approving | Denied (403) |
| Invalid transition | Approving a draft rejected (409) |
| Cross-organization | Invoice not found (404) |
| Concurrent issuance | One success, one conflict; one invoice, one number |
| Money | Integer cents; total $370.00 matches 2 × $185.00 |

Tests: 4 unit + 6 integration (Postgres), all passing.
