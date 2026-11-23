# Limitations

This is a **personal demo project**, not a product and not a client engagement. The points below are
deliberate, and stating them is part of the demo.

## Data and claims

- Every company, document, tenant, ticket and price is fictional. There are no real customers,
  revenue, users, SLAs, certifications or production metrics behind this project.
- The knowledge base is intentionally tiny (9 documents across 2 tenants) so a visitor can read all
  of it and verify the citations by hand.

## Retrieval

- Embeddings are 256-dimensional hashing vectors, not a semantic model. Ranking is dominated by
  lexical overlap with a cosine tiebreaker. Paraphrases that share no tokens with the source can be
  missed, and the agent will abstain instead of guessing. That failure mode is visible in the eval
  set (`abstain-weather`, `abstain-crypto`).
- There is no cross-encoder reranker, no query expansion and no HyDE. A chunk is roughly 70 words
  with 15-word overlap.
- The candidate set on Postgres is the 40 nearest chunks by vector distance before the lexical gate.
  On a big corpus this would need tuning; on 20 chunks it is irrelevant.

## Answers

- Without `OPENAI_API_KEY` the agent runs in **deterministic extractive mode**: it returns the two
  most relevant sentences verbatim, with citation, and reports `mode="deterministic"`. It does not
  paraphrase, combine documents into a narrative, or resolve conflicting sources beyond preferring
  the newest document.
- With a key, answers come from `gpt-4o-mini` with a grounding instruction. Grounding is therefore
  prompt-enforced, not formally guaranteed. The citation list still comes from retrieval, not from
  the model's text, so a model that hallucinates an extra fact is not caught by a verifier.
- No answer-quality judge model is used. The eval set checks observable properties (abstention,
  citation presence, tenant isolation, tool behaviour), not a "groundedness score". No percentage is
  published because the number would not mean anything on 13 cases.

## Security

- Prompt-injection handling is a marker-based filter plus instruction framing. It is a demonstration
  of the control, not a guarantee against a determined adversarial document.
- The public demo exposes two fictional tenants without authentication, because tenant switching is
  part of the demo. A real deployment would authenticate the caller and resolve the tenant from the
  session, never from a request parameter alone.
- Rate limiting is expected at the reverse proxy. The app itself does not implement per-IP limits.
- `ADMIN_TOKEN` is off by default. If enabled on a public host, rotate it and keep it out of Git.

## Operations

- One container, one database, no queue, no horizontal scaling, no backups beyond the Docker volume.
- SQLite mode is for local development and tests only; the deployed instance uses Postgres.
- No voice, telephony, email, WhatsApp or multi-channel ingestion. The scope is a single web chat.
- French/Portuguese answer quality is out of scope: the demo content and UI are in English.

## What would change in a paid engagement

1. Real embedding model and a reranker, plus corpus-specific chunking.
2. Tenant authentication and authorization resolved server-side.
3. Answer verification against citations before responding.
4. A proper eval harness with a labelled set and human review, run in CI.
5. Observability: trace ids, retrieval debug view, latency and cost per answer.
