# Portfolio Demos

**Index:** https://joshbarros.github.io/ — the seven systems, the hard part of each one and its limits.

Personal demo projects for Josh Barros (Josué André da Silva Barros). Each project is a
self-contained, runnable demonstration. None is a client engagement or a production service.

Every project uses fictional companies, documents and data. No real customer, revenue, user count,
SLA or certification is claimed anywhere.

## Projects

| Project | Problem demonstrated | Stack | Demo | Status |
|---|---|---|---|---|
| **Northstar Agent** — AI Support Agent with RAG, Citations and Auditable Actions | Support answers that cannot be traced or trusted; assistants that invent policy details | Python, FastAPI, React, TypeScript, Postgres + pgvector, Docker | https://northstar.5-222-1-215.sslip.io | PUBLIC_VERIFIED · PACKAGED |
| **Hookline** — Reliable Webhook and API Automation with Retries and Audit Trail | Webhook integrations that lose events and cannot be replayed | Node.js, TypeScript, Fastify, Postgres, React, Docker | https://hookline.5-222-1-215.sslip.io | PUBLIC_VERIFIED · PACKAGE_PARTIAL |
| **Ticketline** — Field Service Workflow: Job Tickets, Approvals and PDF Invoices | Field service work that cannot be approved or invoiced consistently | Node.js, TypeScript, Fastify, Postgres, React, PDFKit | https://ticketline.5-222-1-215.sslip.io | PUBLIC_VERIFIED · PACKAGED |
| **Riverbend** — Incremental Data Pipeline with dbt Tests and Data Quality Monitoring | Pipelines that silently load bad data | Python, DuckDB, dbt, Streamlit | https://riverbend.5-222-1-215.sslip.io | PUBLIC_VERIFIED · PACKAGE_PARTIAL |
| **Harborlift** — Application and Database Migration Lab with Verified Rollback | Migrations without a tested way back | Postgres, Python, Docker, Caddy | https://harborlift.5-222-1-215.sslip.io | PUBLIC_VERIFIED · PACKAGE_PARTIAL |
| **Vaultgate** — Multi-Tenant Client Portal with Row-Level Security and Audit Logs | Tenant data leaking across boundaries | FastAPI, Postgres RLS, React | https://vaultgate.5-222-1-215.sslip.io | PUBLIC_VERIFIED · PACKAGED |
| **WooBridge** — Custom WooCommerce API Sync Plugin with Mapping and Error Recovery | Store data drifting from the system of record | PHP, WordPress, WooCommerce, WP-CLI, Docker | local lab (no public admin) | LOCAL_VERIFIED · PACKAGED |

## Northstar Agent

- **What it proves:** a RAG assistant that answers only from a tenant's knowledge base, cites the
  document and excerpt, abstains when the evidence is missing, and performs one validated action with
  an audit trail.
- **Try it:** https://northstar.5-222-1-215.sslip.io — four scenario buttons walk through answer,
  abstention, audited ticket and tenant isolation.
- **Code:** https://github.com/joshbarros/portfolio-demos (`projects/northstar-agent/`).
- **Video:** `projects/northstar-agent/portfolio/video/northstar-demo.mp4` (37s, captioned).
- **Full package:** `projects/northstar-agent/portfolio/` (story, evidence, checklist, screenshots,
  diagram, proposal notes).
- **Limitations:** hashing embeddings rather than a semantic model; deterministic extractive answers
  when no LLM key is configured; fictional tenants are not authenticated because tenant switching is
  part of the demo. Details in
  `projects/northstar-agent/docs/limitations.md`.

## Rules

- Fictional data only. No real clients, revenue, users, SLAs or production claims.
- Each project has its own README, tests, Dockerfile/Compose where applicable, `.env.example`,
  architecture and limitations docs.
- Secrets never belong in this repository.
- Screenshots and video come from the deployed application, not from mockups.

## Layout

```
portfolio-demos/
  projects/
    northstar-agent/
      backend/            FastAPI app, retrieval, tool, audit
      frontend/           React + TypeScript SPA
      evals/              behaviour cases
      docs/               architecture, limitations, evaluation, demo script, screenshots
      portfolio/          Upwork package: texts, story, evidence, checklist, media
      scripts/            eval runner, video recording
  shared/
  infra/
```
