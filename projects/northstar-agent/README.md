# Northstar Agent

**AI Support Agent with RAG, Citations and Auditable Actions**

A personal demo project. The agent answers support questions for a fictional company, cites the
document and excerpt it used, abstains when the knowledge base has no evidence, and opens a fictional
ticket through an audited tool.

> All companies, documents, tickets and prices are fictional. This is a portfolio demonstration, not
> a client engagement or a production service.

## The three demo scenes

| Scene | What happens |
|---|---|
| Answer with source | "How do I reset the thermostat?" → answer quoted from the KB plus a citation with source path and update date |
| Honest abstention | "Do you accept cryptocurrency payments?" → explicit "could not find" with no fabricated answer, and an offer to escalate |
| Auditable action | "Please open a ticket about a broken thermostat" → ticket id, ticket in the list, sanitized tool arguments and result in the audit log |

Also demonstrated: **tenant isolation** (the same shipping question abstains in one tenant and answers
in the other) and **prompt-injection resistance** (a document containing instructions is treated as
data).

## Live demo

- App: https://northstar.5-222-1-215.sslip.io
- Health: https://northstar.5-222-1-215.sslip.io/api/health

The instance runs in deterministic extractive mode unless an LLM key is configured, and every
response reports which mode answered (`deterministic`, `openai`, `tool`, `abstain`).

## Screenshots

| Answer with source | Citation excerpt |
|---|---|
| ![Answer with source](docs/screenshots/01-answer-with-source.png) | ![Citation excerpt](docs/screenshots/02-citation-excerpt.png) |

| Abstention | Ticket and audit |
|---|---|
| ![Abstention](docs/screenshots/03-abstention.png) | ![Ticket and audit](docs/screenshots/05-ticket-and-audit.png) |

| Tenant isolation — abstains | Tenant isolation — answers |
|---|---|
| ![Tenant isolation abstains](docs/screenshots/06-tenant-isolation-abstain.png) | ![Tenant isolation answers](docs/screenshots/07-tenant-isolation-answer.png) |

Mobile (390px): ![Mobile](docs/screenshots/08-mobile.png)

## Stack

- Python 3.12, FastAPI, Pydantic.
- React 18, TypeScript, Vite.
- Postgres 16 + pgvector (deployment); SQLite for local development and tests.
- Docker Compose, Caddy for TLS in front of the app.
- Playwright for the end-to-end verification and the screenshots.

## Run it

### Docker (Postgres + pgvector, as deployed)

```bash
cp .env.example .env
# set POSTGRES_PASSWORD in .env
docker compose up -d --build
open http://127.0.0.1:8093
```

### Local (SQLite, no Docker)

```bash
cd backend
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt

# API with the built SPA (build the frontend first)
cd ../frontend && npm ci && npm run build && cd ../backend
PYTHONPATH=. uvicorn app.main:app --port 8093
```

Frontend dev server with hot reload: `cd frontend && npm run dev` (proxies `/api` to port 8093).

## Tests and evaluation

```bash
cd backend
PYTHONPATH=. pytest -q                      # 16 tests, 3 Postgres tests skipped by default
PYTHONPATH=. python ../scripts/run_evals.py # 13 behaviour cases
```

The Postgres suite runs when a database is provided:

```bash
docker compose up -d db
NORTHSTAR_TEST_DATABASE_URL="postgresql://northstar:$POSTGRES_PASSWORD@127.0.0.1:5432/northstar" \
  PYTHONPATH=. pytest -q tests/test_postgres.py
```

Captured output: [`docs/eval-results.txt`](docs/eval-results.txt). What the cases mean and what they
deliberately do not measure: [`docs/evaluation.md`](docs/evaluation.md).

## API

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Service and mode |
| GET | `/api/tenants` | Fictional tenants |
| POST | `/api/chat` | `{tenant_id, session_id, message}` → answer, citations, abstained, escalate, tool_calls, mode |
| GET | `/api/history?tenant_id&session_id` | Session-scoped conversation |
| GET | `/api/tickets?tenant_id` | Fictional tickets |
| GET | `/api/audit?tenant_id` | Tool calls with sanitized args and result |
| POST | `/api/admin/ingest` | Protected ingestion; disabled unless `ADMIN_TOKEN` is set |

### Reproducible ingestion

```bash
cd backend
PYTHONPATH=. python -m app.ingest --tenant demo-electric \
  --title "Refund policy" --source policies/refund.md \
  --content "Refunds are available within 30 days of the first charge."

PYTHONPATH=. python -m app.ingest --tenant demo-electric --file docs.json
```

## Design notes

- **The application decides permissions, not the model.** Tenant filtering, tool selection, argument
  validation and redaction happen in code. See [`docs/architecture.md`](docs/architecture.md).
- **Abstention is engineered.** A fixed lexical gate, a rerank blend and an unknown-term check make
  "I could not find this" the expected outcome when evidence is missing.
- **Stale documents lose.** When two policy versions exist, retrieval keeps the newest one per topic.
- **Audit is a first-class table**, written by the tool, not by the model.
- **Honest modes.** Deterministic extractive mode is labelled in the UI and API rather than disguised
  as a model answer.

## Known limitations

The demo uses hashing embeddings (no semantic model), answers extractively without an LLM key, and
exposes two fictional tenants without authentication because tenant switching is part of the demo.
The full list, including what would change in a paid engagement, is in
[`docs/limitations.md`](docs/limitations.md).

## Repository layout

```
backend/app/core.py     retrieval, ranking, abstention, tool, audit
backend/app/main.py     FastAPI app, tenant checks, static SPA
backend/app/ingest.py   admin ingestion CLI
backend/tests/          sqlite + postgres suites
evals/questions.json    13 behaviour cases
frontend/src/           React SPA
scripts/run_evals.py    eval runner
docs/                   architecture, limitations, evaluation, demo script
```
