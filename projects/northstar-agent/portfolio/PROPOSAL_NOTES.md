# Proposal notes

Notes for turning this demo into a first message. Nothing here invents a client, a result or a
metric. Use only the part that matches the job.

## How to position it, in three angles

**1. RAG that refuses to guess (AI/LLM jobs).**
Most RAG demos show a happy path. This one is built around the failure path: no evidence means no
answer, and every answer carries the document, source path and excerpt. If a job mentions
hallucination, grounding, citations or trust, lead with that.

**2. One validated action with an audit trail (automation jobs).**
The agent can open a ticket, but the app decides when, validates the arguments, redacts secrets and
writes the result to an audit table. If a job mentions "the agent should create/update X in our
system", this is the pattern: narrow tool, application-side authority, auditable.

**3. Tenant-scoped retrieval in SQL (backend/platform jobs).**
The tenant filter is part of the query, not the prompt. The same question abstains in one tenant and
is answered in another. If a job mentions multi-tenant, data isolation, Postgres or pgvector, use
the isolation scene.

## Short opening drafts (English, truthful)

Draft A — RAG / LLM applications:

> You mentioned answers that cannot be trusted. I built a working reference for that: a support agent
> that answers only from its knowledge base, cites the document and excerpt, and says it could not
> find the answer when the evidence is missing. It is a personal demo project (fictional company),
> public demo and code are linked in my profile. I can walk through the retrieval and abstention
> logic on a call, and I would start your build by defining the eval cases first.

Draft B — automation with an auditable action:

> If the assistant is going to change something in your system, the risky part is not the text, it is
> the action. My demo shows the pattern I would use: one narrow tool, arguments validated in the
> application, secrets redacted, every call and result written to an audit log. Personal demo
> project, fictional data, live link and code available. Happy to map it to your workflow.

Draft C — short version for a quick job:

> I have a working RAG support agent with citations, explicit abstention and an audited ticket tool,
> deployed with Postgres/pgvector and Docker. It is a personal demo, not client work. If your scope is
> close, I can send a fixed-scope proposal after a 15-minute call.

## Questions to ask before quoting

- Which documents are in scope, and who owns updates when a policy changes?
- What must the assistant never answer or never do?
- Is an action required (create ticket, update record), and what is the audit requirement?
- What does a wrong answer cost you? That sets the abstention threshold and the eval set.
- Which model or provider is allowed, and is there a data-residency constraint?

## What not to claim

- No client, no revenue, no users, no production traffic.
- No "97% accuracy" or similar: the eval set checks 13 observable properties, not answer quality.
- No SLA, no certifications, no team.
- Do not present the fictional companies as customers.
