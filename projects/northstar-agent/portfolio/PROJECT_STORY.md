# Project story — Northstar Agent

**AI Support Agent with RAG, Citations and Auditable Actions**

Personal demo project. All companies, documents, tickets and prices are fictional. Built by Josh
Barros (Josué André da Silva Barros) directing an AI coding agent; every technical claim below was
verified by running the application.

## 1. Fictional user and problem

Demo Electric Co., a fictional maker of smart thermostats, runs support through a small knowledge
base: reset guides, warranty, billing, installation. Two failure modes are expensive for a company
like this:

- An assistant that invents a warranty period or a refund window creates legal and financial
  exposure.
- An assistant that cannot show where an answer came from cannot be reviewed, corrected or trusted.

The demo shows an assistant that answers **only** from the knowledge base, shows the document and
excerpt it used, refuses when the evidence is missing, and performs one real action — opening a
support ticket — with an audit trail.

## 2. Demonstrated flow

1. "How do I reset the thermostat?" → answer quoted from the reset guide, with a citation card
   showing title, source path, update date and excerpt.
2. "Do you accept cryptocurrency payments?" → no supporting document, so the agent abstains and
   offers to open a ticket. No invented payment method.
3. "Please open a ticket about a broken thermostat" → the app validates the arguments, creates a
   fictional ticket, writes a sanitized audit entry, and the ticket appears in the tenant's list.
4. Tenant isolation: "How long does shipping take?" abstains in Demo Electric Co. and is answered in
   Northstar Demo Shop, with that tenant's shipping policy.

## 3. Responsibility in the build

Josh defined the product slice, the trust boundaries and the acceptance criteria, reviewed each
iteration, and owns the result. The implementation was written with an AI coding agent under his
direction; the code, tests, deployment and evidence were generated and verified in this repository.
The demo does not claim a client, a team, revenue or production usage.

## 4. Stack and architecture

- Python 3.12, FastAPI, Pydantic.
- React 18, TypeScript, Vite (single-page frontend served by the API container).
- Postgres 16 with pgvector in deployment; SQLite for local development and tests behind the same
  small connection wrapper.
- Docker Compose (app + database), Caddy for TLS and reverse proxy on Hetzner.
- Playwright for end-to-end verification, screenshots and the video.

Request path: SPA → `POST /api/chat` → tenant check → tenant-filtered retrieval (pgvector ordering on
Postgres, lexical gate and rerank in Python) → answer adapter (LLM when a key exists, deterministic
extraction otherwise) → citations for the documents that actually contributed → session history,
ticket tool and audit log.

## 5. Decisions and tradeoffs

- **Lexical gate before the vector score.** The demo uses 256-dimensional hashing embeddings so it
  works with no API key. That makes cosine similarity noisy, so ranking is `0.7 * lexical overlap +
  0.3 * cosine` and chunks below 0.18 overlap are dropped. Fewer false answers, more abstentions.
- **Refuse instead of paraphrase.** Deterministic mode extracts the two best-matching sentences
  verbatim. Less fluent than an LLM answer, but the answer is checkable against the citation.
- **Permissions in code, not in the prompt.** The tenant filter is part of the SQL. Tool execution,
  argument validation and redaction happen in Python. The model never decides authority.
- **Newest document wins per topic.** "Warranty policy (2024, outdated)" and "Warranty policy
  (updated)" collapse to the newest, so a stale policy cannot answer a current question.
- **Explicit mode reporting.** Every response carries `mode`: `deterministic`, `openai`, `tool` or
  `abstain`. The UI shows the mode, so a reviewer always knows what produced the answer.
- **Two stores, one behaviour.** Postgres/pgvector for the deployment, SQLite for tests. The ranking
  logic is shared; only the candidate query differs.

## 6. Tests performed

- `pytest`: 16 tests on SQLite covering citations, updated-vs-outdated policies, abstention, tenant
  isolation, prompt-injection text, tool validation, ticket/audit round trip, idempotent seeding,
  session-scoped history and disabled admin ingestion. 3 additional Postgres tests run against a
  real pgvector database.
- Behaviour eval set: 13 cases in `evals/questions.json`, one per property, run by
  `scripts/run_evals.py`. Result: 13/13.
- Browser verification with Playwright on the public URL: the three scenes plus tenant isolation,
  with zero console errors and zero failed requests.
- Visual review at 1600×1000, 1400×1050 and 390×844 (mobile). A mobile layout bug — horizontal
  overflow caused by the scenario strip — was found and fixed during this review.

## 7. Measured technical results

- Eval set: 13/13 properties pass in deterministic mode (run recorded in `docs/eval-results.txt`).
- Public health check responds over HTTPS; the three demo scenes were re-executed on the public URL
  after deployment.
- No LLM latency or token numbers are claimed: the public instance runs in deterministic mode, which
  makes no model call. With `OPENAI_API_KEY` set the response reports `mode="openai"`, and timings
  would need to be measured on that configuration.

## 8. Limitations

- Hashing embeddings, not a semantic model: a paraphrase with no shared tokens can be missed, and
  the agent abstains rather than guesses.
- With an LLM key, grounding is prompt-enforced and not formally verified against the citations.
- Prompt-injection handling is a marker filter plus instruction framing, not a hard guarantee.
- The public demo exposes two fictional tenants without authentication, because tenant switching is
  part of the demonstration.
- Single container, no queue, no horizontal scaling, no backup policy beyond the database volume.
- English content only; no voice, email, WhatsApp or other channels.

## 9. How to run

```bash
cp .env.example .env          # set POSTGRES_PASSWORD
docker compose up -d --build  # app on 127.0.0.1:8093
```

Local development with SQLite:

```bash
cd backend && python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt
PYTHONPATH=. pytest -q
PYTHONPATH=. python ../scripts/run_evals.py
```

Public demo: https://northstar.5-222-1-215.sslip.io

## 10. Opportunity fit

This proof is relevant to:

- AI/LLM application engineering (RAG, grounding, citation, abstention, evaluation).
- Backend engineering with Python/FastAPI and PostgreSQL.
- Internal tools and support automation where an audit trail matters.
- Teams that need a working reference before committing to a vendor or a large build.
- Integrations where an agent must perform one narrow, validated action rather than open-ended tool
  use.
