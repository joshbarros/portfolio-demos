# Video script and captions

Recorded from the live application at 1280×720, 37 seconds, no voice-over. Captions are burned into
the video; the times below are approximate (±1s). The recording was made with Playwright against
`https://northstar.5-222-1-215.sslip.io` on 2026-11-23; the script is
`scripts/record_demo.py`.

| Time (approx.) | Caption | Action | Result on screen |
|---|---|---|---|
| 0:00–0:05 | Personal demo project — fictional company, fictional data | Page loads | Two tenants, four scenarios, guarantees list |
| 0:05–0:08 | 1. Answer with a verifiable citation | Click *Answer with source* | Answer quoted from the knowledge base, one citation card |
| 0:08–0:13 | The citation opens to the source document, excerpt and update date | Open the citation | Excerpt, `support/thermostat-reset.md`, `updated 2026-10-02`, relevance |
| 0:13–0:17 | 2. No evidence in the knowledge base → explicit abstention | Click *Abstain honestly* | Amber "No supporting evidence" banner, no citations, offer to open a ticket |
| 0:17–0:21 | 3. A tool call: the ticket is created by the app | Click *Auditable action* | Green tool flag, ticket id in the answer |
| 0:21–0:24 | The ticket appears in the tenant's list | Tickets tab | Ticket id, subject, priority, status |
| 0:24–0:28 | Audit log: sanitized arguments and the tool result | Audit tab | `create_ticket`, args JSON, `created TKT-…` |
| 0:28–0:31 | Tenant isolation: wrong tenant → no answer | Click *Tenant isolation* | Abstention in Demo Electric Co. |
| 0:31–0:37 | Same question, correct tenant → grounded answer | Switch tenant, ask again | Answer with the shipping policy citation |

## Production notes

- Real browser capture, no mocked backend: the video hits the deployed API and Postgres.
- Ticket ids in the video are real rows created by that run in the fictional demo database.
- No personal data, no real company, no real customer appears in frame.
- Captions were injected into the page before each action, so they are synchronized by construction
  rather than added in an editor.
- Format: H.264 MP4, 1280×720, 25 fps, ~185 kb/s, 845 KB. Plays in browsers, QuickTime and VLC.
- Re-recording: `DEMO_URL=https://… python scripts/record_demo.py`, then convert the WebM to MP4 with
  `ffmpeg -i page@*.webm -c:v libx264 -pix_fmt yuv420p -movflags +faststart -crf 24 out.mp4`.
