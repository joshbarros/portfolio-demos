# Checklist

Legend: **PASS** verified with a result, **PENDING** not yet verified, **BLOCKED** cannot be verified
in the current environment. No item is marked PASS on the basis of "it should work".

## Functional acceptance (spec §10.6)

| # | Item | Status | Evidence |
|---|---|---|---|
| 1 | Ask a question, open the source, create a ticket in a short flow | PASS | Public URL, scenes A–C, 2026-11-23 |
| 2 | Answer shows the document and an accessible excerpt | PASS | Citation card expands to excerpt, source path, update date, relevance |
| 3 | Explicit indication when there is no evidence | PASS | Amber banner, 0 citations, `abstained=true`, `mode=abstain` |
| 4 | Ticket appears in the list | PASS | Tickets tab after scene C |
| 5 | Ticket appears in the audit | PASS | Audit tab: action, sanitized args, result |
| 6 | Tenant isolation | PASS | Same question abstains in Demo Electric Co., answers in Northstar Demo Shop |
| 7 | Session history limited to the session | PASS | `test_history_is_session_scoped`; `/api/history` returns `[]` for another session or tenant |
| 8 | Human handoff flag | PASS | `escalate=true` on abstention and ticket responses |

## Controls (spec §10.4)

| # | Item | Status | Evidence |
|---|---|---|---|
| 9 | Tenant filter enforced in the query, not by the model | PASS | SQL `WHERE tenant_id = ?`; cross-tenant test |
| 10 | Tool arguments validated before execution | PASS | Rejected 1-character subject with a reason; audit row records the rejection |
| 11 | Secrets redacted from audit arguments | PASS | Keys matching token/password/secret/key/authorization → `[redacted]` |
| 12 | Document text treated as untrusted data | PASS | Injection marker filter + instruction framing; `injection-note` eval case |
| 13 | Admin ingestion protected | PASS | `403` when `ADMIN_TOKEN` is unset; token header required when set |
| 14 | No action escapes the demo | PASS | Tickets are rows in the demo database only; no email, chat or external API is called |

## Evaluation (spec §10.5)

| # | Item | Status | Evidence |
|---|---|---|---|
| 15 | Reproducible eval set of 12–20 cases | PASS | 13 cases in `evals/questions.json` |
| 16 | Cases cover direct, combined, absent, conflicting, injection, cross-tenant, tool valid/invalid | PASS | See `docs/evaluation.md` table |
| 17 | Test suite green | PASS | 16 passed on SQLite; 3 passed on Postgres + pgvector |
| 18 | No unsupported "groundedness %" published | PASS | Eval reports properties, not a score |
| 19 | Latency and tokens measured on real LLM runs | PENDING | Public instance runs deterministic mode; no provider key configured |
| 20 | LLM answer path exercised end to end | PENDING | Code path exists, untested against a live key |

## Deploy and operations

| # | Item | Status | Evidence |
|---|---|---|---|
| 21 | Docker Compose build and start | PASS | `northstar-app-1` and `northstar-db-1` healthy |
| 22 | HTTPS on the public URL | PASS | Let's Encrypt certificate via Caddy |
| 23 | Public URL verified after deploy | PASS | Scenes re-executed on the public host |
| 24 | Only 22/80/443 exposed | PASS | Direct `:8092` and `:8093` blocked; `ufw` default deny |
| 25 | No console errors or failed requests | PASS | 0 errors, 43 requests, 0 failures |
| 26 | Restart resilience | PASS | `restart: unless-stopped` on both services; container healthy after recreate |
| 27 | Backups | PENDING | No automated backup of the Postgres volume; acceptable for a resettable demo |
| 28 | Rate limiting | PENDING | Expected at the proxy; not configured for this demo |

## Media and package (spec §17)

| # | Item | Status | Evidence |
|---|---|---|---|
| 29 | Screenshots of main flow, technical detail, result/audit | PASS | 4 scenes, 1600×1000 |
| 30 | 1000×750 versions, re-framed without stretching | PASS | Captured at 1400×1050 (same 4:3 ratio) and resampled |
| 31 | Mobile-width verification | PASS | 390×844; overflow found and fixed, `scrollWidth == 390` |
| 32 | Real 30–60 s video with captions | PASS | 37.3 s, 1280×720, H.264, captions burned in |
| 33 | Video states it is a personal demo project | PASS | Opening caption |
| 34 | Diagram from the real architecture | PASS | `diagrams/architecture.png` |
| 35 | Title ≤70, role ≤100, description ≤600, ≤5 skills | PASS | `CHARACTER_COUNTS.json` |
| 36 | Three ways to explain relevance | PASS | `PROPOSAL_NOTES.md` |
| 37 | Evidence document with commit, date, environment, commands, results | PASS | `EVIDENCE.md` |

## Truth, authorship and privacy (spec §3, §18)

| # | Item | Status | Evidence |
|---|---|---|---|
| 38 | All data fictional | PASS | Seed data and UI labels; README disclaimer |
| 39 | No client, revenue, user or production claim | PASS | Text reviewed; no quantified benefit invented |
| 40 | AI assistance disclosed | PASS | `ROLE.txt`, `PROJECT_STORY.md` §3 |
| 41 | No secrets in repo, screenshots or video | PASS | `.gitignore`, manual review of frames, `.env` excluded |
| 42 | No personal or Upwork data in artifacts | PASS | Fictional names only |
| 43 | Public code repository link | PASS | https://github.com/joshbarros/portfolio-demos (commit `8ec7cb3`) |
| 44 | Upwork portfolio item published | BLOCKED | No Upwork MCP access in this environment; package ready for manual publication |

## Known defects or accepted limitations

- Paraphrases without lexical overlap can be missed → abstention. Accepted tradeoff, documented.
- The `deterministic` mode quotes sentences verbatim, so answers read like excerpts.
- The public demo allows switching between two fictional tenants without authentication, by design.
