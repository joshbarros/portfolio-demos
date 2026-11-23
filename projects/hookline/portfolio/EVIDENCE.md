# Evidence

**Commit:** to be recorded after the public push
**Date:** 2026-11-23
**Public URL:** https://hookline.5-222-1-215.sslip.io

## Verified

| Scenario | Observed |
|---|---|
| Valid event | Execution succeeded, 3 steps succeeded, 1 attempt |
| Transient failure | Execution succeeded after 5 attempts; reservation created once (idempotent) |
| Permanent failure | Execution dead at the reservations step, 422 recorded |
| Timeout | Step retried and eventually dead after the attempt limit |
| Duplicate delivery | Second delivery returned the same execution id, `duplicate: true`, one reservation |
| Replay after fix | Dead execution replayed with `failure_mode=happy` and succeeded |
| Tampered signature | 401 `bad_signature` |
| Stale signed request | 401 `stale` |

Unit tests: 8 passing (`npm test`) covering signature verification, replay window, event validation
and backoff bounds.
