# Evidence

**Date:** 2026-11-23
**Public portal:** https://vaultgate.5-222-1-215.sslip.io
**Screenshots:** `portfolio/screenshots/01-alpha-blocked.png`, `02-beta-own-files.png`
**Video:** `portfolio/video/vaultgate-demo.mp4` (34.5 s)

## Verified in the browser

| Scenario | Observed |
|---|---|
| Alpha login | Only `alpha-brief.txt` and `alpha-rates.csv` listed |
| Cross-tenant request by id | 404 `file not found`; audit entry `file.read found:false` |
| Switch to Beta | Beta sees only `beta-notes.txt` |
| Audit | login, files.list, file.read and denial recorded |

## Verified in tests (10 passing)

Cross-tenant read and write, direct SQL scoping with `app.org_id`, connection reuse across tenants,
expired session, revoked session, signed URL happy path, expiry, tampered signature, cross-tenant
signing, audit of denials.

## Notes

- Signed URLs remain valid until they expire; the demo does not claim instant revocation.
- Audit rows are append-only for the application role; infrastructure administrators with direct
  database access are out of scope. No HIPAA/BAA/regulatory claim.
