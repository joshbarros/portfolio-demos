# Hookline

**Reliable Webhook and API Automation with Retries and Audit Trail**

A personal demo project. A signed webhook triggers a three-step flow; a step fails, the system retries
with exponential backoff and jitter, and the interface shows exactly what happened — including the
dead-letter queue and a controlled replay.

- Live demo: https://hookline.5-222-1-215.sslip.io
- All data is fictional. No client, revenue or production claim.

## Scenes

| Scene | What happens |
|---|---|
| Valid event | Signature verified, event stored, three steps succeed |
| Transient failure | Destination returns 503 twice, retries recover, the reservation exists once |
| Permanent failure | 422 stops the flow and the execution goes to dead |
| Timeout | Step exceeds the timeout and is retried |
| Duplicate delivery | The same event twice returns the same execution; one business action |
| Replay | A dead execution is replayed after the cause is fixed |

## Stack

- Node.js 22 + TypeScript + Fastify.
- Postgres 16 for durable state (events, executions, steps).
- Separate worker process; fake destination services in their own container.
- React + TypeScript + Vite UI.
- Docker Compose; Caddy for TLS in front of the API.

## Run

```bash
cp .env.example .env   # set POSTGRES_PASSWORD and HOOKLINE_SECRET
docker compose up -d --build
open http://127.0.0.1:8097
```

Tests:

```bash
npm install
npm test
```

## Delivery semantics

At-least-once. The event is persisted before processing. Steps that support idempotency keys
(reservations, catalog) never create a second effect when retried. Notifications are deliberately not
idempotent: the UI shows the duplicate when a retry re-sends. See `docs/limitations.md`.

## Repository layout

```
src/server.ts     API, signature verification, webhook ingestion, SPA
src/worker.ts     claims executions, runs steps, retries with backoff + jitter
src/fakes.ts      fictional reservations, catalog and notification services
src/db.ts         schema and queries
src/signature.ts  HMAC signing, replay window, backoff
frontend/         React console
test/             unit tests for signature, validation and backoff
```
