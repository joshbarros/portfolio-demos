# Vaultgate

**Multi-Tenant Client Portal with Row-Level Security and Audit Logs**

Personal demo project. Two fictional organizations share one Postgres database, with tenant isolation
enforced by row-level security (FORCE RLS) rather than by application filters. The tenant always comes
from a validated session; a browser parameter never selects it.

## What is implemented

- Organizations, users (admin/user), sessions with expiry and revocation.
- Files with per-tenant RLS on read and write.
- Audit table the application role can insert into but not update or delete.
- Signed download URLs with expiry (valid until they expire; no instant revocation claim).
- The application role (`vault_app`) is not the table owner, and RLS is forced, so the policy cannot
  be bypassed by the app role.
- Tenant context is set per transaction with `set_config('app.org_id', …, true)`, so a pooled
  connection cannot leak the previous tenant.

## Tests (10, all passing)

Cross-tenant read and write, direct SQL scoping, connection reuse across tenants, expired and revoked
sessions, signed URL happy path, expiry, tampering and cross-tenant signing, audit of denials.

```bash
docker compose up -d
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
PYTHONPATH=. python -m pytest -q
```

## Live demo

https://vaultgate.5-222-1-215.sslip.io — sign in as Alice (Alpha Freight) or Bob (Beta Clinic) with
the demo password `demo`. Use "Attempt cross-tenant access" to see the block and the audit entry.

## Media

- Screenshots: `portfolio/screenshots/`.
- Video: `portfolio/video/vaultgate-demo.mp4` (34.5 s).

## Limitations

- Files are stored as `bytea` for the demo; production would use S3-compatible storage with
  server-side encryption and short-lived signed URLs.
- No real authentication factors; demo passwords exist only for the lab.
- Audit rows are append-only for the app role, but infrastructure administrators with direct database
  access could alter them. The trail is not described as immutable.
- No HIPAA/BAA/regulatory claim.
