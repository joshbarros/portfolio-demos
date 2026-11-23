# Ticketline

**Field Service Workflow: Job Tickets, Approvals and PDF Invoices**

Personal demo project. A technician records a job with line items, a reviewer approves it, and the
application issues a demo invoice as a real PDF. Fictional company (Demo Electric Co.) and fictional
data.

## Domain

- Organizations, users (technician / reviewer), clients and services.
- Tickets with items, quantities and integer-cent prices.
- Explicit state machine: draft → submitted → approved → invoiced; submitted → rejected → draft.
- Approval history in an append-only audit table.
- Invoice numbering per organization, transactional, without duplicates.
- Invoice snapshot: client and items are copied at issuance, so later edits do not rewrite a document.
- Authorized PDF download scoped by organization.

## Integrity

- Money is integer cents everywhere; totals are computed from items.
- Invalid transitions, duplicate issuance, cross-organization access and concurrent issuance are
  covered by tests.

## Tests

```bash
npm install
npm test                                        # unit tests
TEST_DATABASE_URL=postgres://... npm test       # + integration (Postgres)
```

10 tests: money, state machine, roles, full flow with PDF, duplicate issuance, technician cannot
approve, invalid transition, cross-org denial, concurrent issuance (one invoice, one number).

## Status

Backend complete. UI, Docker Compose, deployment and media are the next step.
