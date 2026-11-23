# Demo script

Target length: 60–75 seconds, no voice-over, screen only. Recorded in Chromium at 1440×900.

| Time | Scene | Action | What the viewer must see |
|---|---|---|---|
| 0:00–0:04 | Intro | Land on the app | "Personal demo project" badge, two tenants, four scenarios, the guarantees list |
| 0:04–0:24 | **A. Answer with source** | Click *Answer with source* | Answer appears with one citation card; open it to reveal the excerpt, source path and update date |
| 0:24–0:40 | **B. Abstention** | Click *Abstain honestly* | Amber banner "No supporting evidence", no citations, offer to open a ticket |
| 0:40–0:58 | **C. Auditable action** | Click *Auditable action* | Ticket id returned, green tool flag, ticket appears in the Tickets tab, `create_ticket` entry in Audit with sanitized args and result |
| 0:58–1:08 | Isolation | Switch to the other tenant, click *Tenant isolation* | The same question abstains in demo-electric and answers in northstar-demo-shop |
| 1:08–1:15 | Close | Audit tab | Ticket count and audit trail as the last frame |

## Recording checklist

- Fresh database (`docker compose down -v && docker compose up -d`) so ticket ids look new.
- Browser zoom 100%, no bookmarks bar, no devtools.
- Disable the blinking cursor before recording if the terminal is not used.
- Keep the mouse movement deliberate: one click per scene, no scrolling unless the citation panel
  needs it.
- Verify after recording: three scenes visible, no console errors, no failed requests in the network
  panel.

## Screenshots to publish

1. `01-answer-with-source.png` — answer plus citation card.
2. `02-citation-excerpt.png` — the cited document and excerpt expanded.
3. `03-abstention.png` — explicit limitation.
4. `04-tickets-list.png` — ticket created, in the list.
5. `05-ticket-and-audit.png` — audit entry with sanitized args and result.
6. `06-tenant-isolation-abstain.png` — the shipping question in the wrong tenant.
7. `07-tenant-isolation-answer.png` — the same question in the right tenant.
8. `08-mobile.png` — 390px viewport of the main flow.
