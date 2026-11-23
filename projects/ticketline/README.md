# Ticketline

**Field Service Workflow: Job Tickets, Approvals and PDF Invoices**

A personal demo project. A technician records a job with line items, a reviewer approves it, and the
application issues a demo invoice as a real PDF. Fictional company (Demo Electric Co.), fictional data.

- Live demo: https://ticketline.5-222-1-215.sslip.io
- Roles in the demo: **Tina Technician** (creates and submits) and **Ravi Reviewer** (approves, issues).

## Flow

1. Technician creates a draft with client, notes and line items.
2. Technician submits it for review.
3. Reviewer approves or rejects; the decision is written to the history.
4. Reviewer issues the invoice: a per-organization sequential number, a frozen snapshot and a PDF.
5. The PDF is downloadable only inside the organization.

## Integrity

- Money is integer cents; totals are computed from items.
- Explicit state machine: draft → submitted → approved → invoiced; submitted → rejected → draft.
- Invoice numbering in a transaction (`invoice_counters`), with a unique constraint per organization.
- Invoice snapshot copies client and items, so later edits do not rewrite an issued document.
- Org-scoped access: another organization's invoice is simply not found.

## Tests

```bash
npm install
npm test                                     # unit
TEST_DATABASE_URL=postgres://... npm test    # + integration
```

10 tests: money, state machine, roles, full flow with real PDF, duplicate issuance, technician cannot
approve, invalid transition, cross-org denial, concurrent issuance producing one invoice and one number.

## Run

```bash
cp .env.example .env
docker compose up -d --build
open http://127.0.0.1:8096
```

## Stack

React + TypeScript (Vite), Node.js 22 + Fastify, Postgres 16, PDFKit, Docker Compose, Caddy TLS.

## Media

- Screenshots: `portfolio/screenshots/` (submitted, approved, invoiced, PDF page).
- Video: `portfolio/video/ticketline-demo.mp4` (54 s, captions).
- Demo PDF: `portfolio/invoice-demo.pdf`.

## Limitations

See `docs/limitations.md`. The PDF is a demo document, not a fiscal invoice.
