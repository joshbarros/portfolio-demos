# Evidence

**Project:** Northstar Agent — AI Support Agent with RAG, Citations and Auditable Actions
**Author:** Josh Barros (Josué André da Silva Barros), directing an AI coding agent
**Application commit:** `8ec7cb3` (`northstar-agent: RAG support agent with citations, abstention and
audited ticket tool`)
**Date of the evidence run:** 2026-11-23 (UTC)
**Environment:** local Linux workstation (Ubuntu 26.04, Python 3.14 venv) and Hetzner Cloud
`desafio100k-agents` (Ubuntu 24.04, CAX11, 2 vCPU / 4 GB) running Docker Compose + Caddy
**Public URL:** https://northstar.5-222-1-215.sslip.io

## What was actually run

| # | Scenario | Command / action | Observed result |
|---|---|---|---|
| 1 | Unit and API tests | `PYTHONPATH=. pytest -q` | `16 passed, 3 skipped` (Postgres suite skipped without a database URL) |
| 2 | Postgres + pgvector tests | `docker run pgvector/pgvector:pg16`, then `NORTHSTAR_TEST_DATABASE_URL=… pytest -q tests/test_postgres.py` | `3 passed` — pgvector ordering, ticket/audit round trip, tenant isolation |
| 3 | Behaviour eval set | `PYTHONPATH=. python ../scripts/run_evals.py` | `13/13 passed`, all in `deterministic` mode except the tool and abstain cases |
| 4 | Container build and start | `docker compose up -d --build` | `northstar-app-1` healthy, `northstar-db-1` healthy |
| 5 | Public health check | `GET /api/health` over HTTPS | `{"ok":true,"service":"northstar-agent","mode":"demo",…}` |
| 6 | Public scene A — answer with source | Click *Answer with source* on the public URL | Answer quoted from the KB; citation `Thermostat reset guide · support/thermostat-reset.md · updated 2026-10-02`; `mode=deterministic` |
| 7 | Public scene B — abstention | Click *Abstain honestly* | Banner "No supporting evidence", 0 citations, offer to open a ticket |
| 8 | Public scene C — audited action | Click *Auditable action* | Ticket created (id `TKT-…`); visible in Tickets; audit row `create_ticket` with args JSON and `created TKT-…` |
| 9 | Tenant isolation (wrong tenant) | Ask "How long does shipping take?" in Demo Electric Co. | Abstained, 0 citations |
| 10 | Tenant isolation (right tenant) | Same question in Northstar Demo Shop | Answered from the shipping policy with citation |
| 11 | Console and network check | Playwright console + network capture on the public URL | 0 console errors, 0 warnings; 43 requests, 0 failures |
| 12 | Visual review, desktop | Screenshots at 1600×1000 and 1400×1050 | No clipped text, no stray scrollbars, panels aligned |
| 13 | Visual review, mobile | 390×844 viewport | Found horizontal overflow from the scenario strip; fixed with `minmax(0,1fr)` and `min-width:0`; re-verified `document.scrollWidth == 390` |
| 14 | Video capture | `python scripts/record_demo.py` against the public URL | 37.3 s, 1280×720, H.264, captions burned in |
| 15 | Deployed port exposure | `curl` direct to `:8092` and `:8093` from outside; `ufw status verbose` | Both direct ports blocked; only 22/80/443 open; app and Hermes reachable through Caddy with TLS |

## Real execution vs mock vs replay

- Retrieval, ranking, abstention, tool execution, audit and tenant filtering are **real**: the browser
  calls the deployed FastAPI process, which queries the deployed Postgres/pgvector instance.
- There is **no mocked backend** and no recorded API fixture in the demonstrated path.
- The answer text in the public instance is produced by the **deterministic extractive mode**, not by
  an LLM. This is reported by the API (`mode="deterministic"`) and visible in the UI. The LLM path
  exists in code but has **not** been exercised against a live provider key — see PENDING items.
- No external service is stubbed in the demonstrated flow.

## Artifacts

| Artifact | Path |
|---|---|
| Screenshots, originals 1600×1000 | `screenshots/1600x1000/` |
| Screenshots, 1000×750 | `screenshots/1000x750/` |
| Video (37 s, captioned) | `video/northstar-demo.mp4` |
| Architecture diagram | `diagrams/architecture.png` |
| Eval run output | `../../docs/eval-results.txt` |
| Eval methodology | `../../docs/evaluation.md` |
| Known limitations | `../../docs/limitations.md` |

## Sanitization
- No token, password, connection string, private key or `.env` value appears in the repository, the
  screenshots or the video.
- The database password exists only in the server's `/opt/northstar/.env` (`chmod 600`) and is not in
  any artifact.
- The demo database was reset after the verification run, so ticket ids created during that run are
  no longer listed. The screenshots and video were captured against the deployed application and
  show real rows at capture time.
- No real person, employer, client or customer appears in any frame. All tenants, documents and
  tickets are fictional.
- Upwork data is not stored anywhere in this repository.

## Limitations that remain

- Semantic quality is limited by the hashing embeddings; paraphrases without shared tokens can be
  missed and end in abstention.
- The LLM answer path and its latency/cost are unverified (no provider key configured).
- The public demo has no tenant authentication, by design, because tenant switching is part of the
  demonstration.
- Single-node deployment without a queue or backup policy beyond the database volume.
